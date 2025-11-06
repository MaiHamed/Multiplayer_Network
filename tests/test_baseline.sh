#!/usr/bin/env bash
set -euo pipefail

# Baseline test runner (no impairment)
# - Starts server and N clients
# - Runs for DURATION seconds
# - Collects numeric log lines (lines starting with a digit)
# - Produces detailed metrics CSV and summary CSV with mean/median/p95

NUM_CLIENTS=4
DURATION=30         # seconds
RESULTS_DIR="./results"
SERVER_CMD="python3 server.py"
CLIENT_CMD="python3 client.py"

mkdir -p "$RESULTS_DIR"
# kill leftovers
pkill -f server.py 2>/dev/null || true
pkill -f client.py 2>/dev/null || true

echo "[INFO] Starting baseline test: $NUM_CLIENTS clients for $DURATIONs"
# start server
$SERVER_CMD > "$RESULTS_DIR/server_raw.log" 2>&1 &
SERVER_PID=$!
sleep 1

# start clients
CLIENT_PIDS=()
for i in $(seq 1 $NUM_CLIENTS); do
  OUT="$RESULTS_DIR/client_${i}_raw.log"
  # start each client in background; stdout/stderr to file
  $CLIENT_CMD > "$OUT" 2>&1 &
  CLIENT_PIDS+=($!)
  sleep 0.2
done

echo "[INFO] Running for $DURATION seconds..."
sleep "$DURATION"

echo "[INFO] Stopping clients and server..."
# terminate clients and server
for pid in "${CLIENT_PIDS[@]}"; do
  kill "$pid" 2>/dev/null || true
done
kill "$SERVER_PID" 2>/dev/null || true
sleep 1

# Extract numeric lines (lines that start with a digit) to cleaned files
echo "[INFO] Extracting numeric lines..."
CLEAN_LIST=()
for i in $(seq 1 $NUM_CLIENTS); do
  RAW="$RESULTS_DIR/client_${i}_raw.log"
  CLEAN="$RESULTS_DIR/client_${i}.txt"
  grep -E '^[0-9]+' "$RAW" > "$CLEAN" || true
  CLEAN_LIST+=("$CLEAN")
done
# server numeric lines
grep -E '^[0-9]+' "$RESULTS_DIR/server_raw.log" > "$RESULTS_DIR/server.txt" || true

# Combine all client numeric files into one baseline.txt (optional)
cat "${CLEAN_LIST[@]}" > "$RESULTS_DIR/baseline.txt" || true

echo "[INFO] Generating CSVs..."
# run embedded python to parse numeric lines and compute metrics
python3 - <<'PY'
import csv, glob, os, statistics, math

RESULTS_DIR = "results"
client_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "client_*.txt")))
server_file = os.path.join(RESULTS_DIR, "server.txt")
detailed_csv = os.path.join(RESULTS_DIR, "baseline_metrics.csv")
summary_csv = os.path.join(RESULTS_DIR, "summary.csv")

# helper percentile without numpy
def percentile(vals, p):
    if not vals:
        return 0.0
    vals_sorted = sorted(vals)
    k = (len(vals_sorted)-1) * (p/100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals_sorted[int(k)]
    d0 = vals_sorted[int(f)] * (c-k)
    d1 = vals_sorted[int(c)] * (k-f)
    return d0 + d1

# Parse numeric lines: expected format per line:
# client_id snapshot_id seq_num server_timestamp_ms recv_time_ms cpu_percent perceived_position_error bandwidth_per_client_kbps
rows = []
per_client_recv_times = {}  # for jitter per-client: inter-arrival differences of recv_time
for cf in client_files:
    with open(cf, "r") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) < 8:
                continue
            try:
                client_id = int(parts[0])
                snapshot_id = int(parts[1])
                seq_num = int(parts[2])
                server_ts = float(parts[3])
                recv_ts = float(parts[4])
                cpu_percent = float(parts[5])
                perceived_err = float(parts[6])
                bw = float(parts[7])
            except:
                continue
            latency = recv_ts - server_ts
            # save for jitter calculation
            per_client_recv_times.setdefault(client_id, []).append(recv_ts)
            rows.append({
                "client_id": client_id,
                "snapshot_id": snapshot_id,
                "seq_num": seq_num,
                "server_timestamp_ms": server_ts,
                "recv_time_ms": recv_ts,
                "latency_ms": latency,
                "jitter_ms": 0.0,  # fill later
                "perceived_position_error": perceived_err,
                "cpu_percent": cpu_percent,
                "bandwidth_per_client_kbps": bw
            })

# compute per-client jitter (variation in inter-arrival times)
# jitter per-sample defined as abs(delta_latency) or abs(delta_recv_time difference)
# We'll compute jitter as absolute difference between successive inter-arrival times (ms)
client_intervals = {}
for cid, times in per_client_recv_times.items():
    if len(times) < 2:
        client_intervals[cid] = [0.0]*len(times)
        continue
    intervals = [times[i] - times[i-1] for i in range(1,len(times))]
    # jitter list aligned to snapshots after the first; pad with 0 for first
    jitter_list = [0.0]
    for i in range(1,len(times)):
        if i == 1:
            jitter_list.append(0.0)
        else:
            # variation between intervals
            jitter_list.append(abs(intervals[i-1] - intervals[i-2]))
    client_intervals[cid] = jitter_list

# assign jitter values back to rows in chronological per-client order
# build per-client row lists
per_client_rows = {}
for r in rows:
    per_client_rows.setdefault(r["client_id"], []).append(r)

for cid, rlist in per_client_rows.items():
    jitter_vals = client_intervals.get(cid, [0.0]*len(rlist))
    # ensure same length
    for idx, r in enumerate(rlist):
        if idx < len(jitter_vals):
            r["jitter_ms"] = jitter_vals[idx]
        else:
            r["jitter_ms"] = 0.0

# Write detailed CSV
fieldnames = [
    "client_id","snapshot_id","seq_num",
    "server_timestamp_ms","recv_time_ms","latency_ms","jitter_ms",
    "perceived_position_error","cpu_percent","bandwidth_per_client_kbps"
]
with open(detailed_csv,"w",newline='') as out:
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    # sort rows by client_id then snapshot_id
    for r in sorted(rows, key=lambda x: (x["client_id"], x["snapshot_id"])):
        writer.writerow({k: r.get(k,0) for k in fieldnames})

# Compute summary stats (per scenario, aggregate across clients)
latencies = [r["latency_ms"] for r in rows]
jitters = [r["jitter_ms"] for r in rows]
errors  = [r["perceived_position_error"] for r in rows]
cpu = [r["cpu_percent"] for r in rows]
bw = [r["bandwidth_per_client_kbps"] for r in rows]

def safe_stats(arr):
    if not arr:
        return (0.0,0.0,0.0)
    return (statistics.mean(arr), statistics.median(arr), percentile(arr,95))

summary_fields = [
    "metric","mean","median","p95"
]
summary_rows = [
    {"metric":"latency_ms","mean":safe_stats(latencies)[0],"median":safe_stats(latencies)[1],"p95":safe_stats(latencies)[2]},
    {"metric":"jitter_ms","mean":safe_stats(jitters)[0],"median":safe_stats(jitters)[1],"p95":safe_stats(jitters)[2]},
    {"metric":"perceived_position_error","mean":safe_stats(errors)[0],"median":safe_stats(errors)[1],"p95":safe_stats(errors)[2]},
    {"metric":"cpu_percent","mean":safe_stats(cpu)[0],"median":safe_stats(cpu)[1],"p95":safe_stats(cpu)[2]},
    {"metric":"bandwidth_per_client_kbps","mean":safe_stats(bw)[0],"median":safe_stats(bw)[1],"p95":safe_stats(bw)[2]},
]

with open(summary_csv,"w",newline='') as out:
    writer = csv.DictWriter(out, fieldnames=summary_fields)
    writer.writeheader()
    for r in summary_rows:
        writer.writerow(r)

# Print acceptance checks to stdout
avg_updates_per_client = 0
# approximate updates/sec: count snapshots per client divided by duration (if known)
# Here we compute average snapshot rate across clients if possible:
duration = max((r["recv_time_ms"] for r in rows), default=0) - min((r["recv_time_ms"] for r in rows), default=0)
if duration > 0:
    duration_s = duration / 1000.0
    per_client_counts = {cid: len(lst) for cid,lst in per_client_rows.items()}
    updates_per_client = [c/duration_s for c in per_client_counts.values()] if duration_s>0 else []
    avg_updates_per_client = statistics.mean(updates_per_client) if updates_per_client else 0.0
else:
    avg_updates_per_client = 0.0

avg_latency = statistics.mean(latencies) if latencies else 0.0
avg_cpu = statistics.mean(cpu) if cpu else 0.0

print("=== Baseline Test Summary ===")
print(f"avg_updates_per_client: {avg_updates_per_client:.2f} updates/sec")
print(f"avg_latency_ms: {avg_latency:.3f} ms")
print(f"avg_cpu_percent: {avg_cpu:.3f} %")
print(f"Detailed CSV: {detailed_csv}")
print(f"Summary CSV: {summary_csv}")

# Acceptance criteria check: 20 updates/sec per client, avg_latency <=50ms, avg_cpu <60%
pass_updates = avg_updates_per_client >= 20.0
pass_latency = avg_latency <= 50.0
pass_cpu = avg_cpu < 60.0

print("Acceptance criteria:")
print(f" - 20 updates/sec per client: {'PASS' if pass_updates else 'FAIL'}")
print(f" - avg latency <= 50 ms: {'PASS' if pass_latency else 'FAIL'}")
print(f" - avg CPU < 60%: {'PASS' if pass_cpu else 'FAIL'}")
PY

echo "[DONE] baseline test complete. Check $RESULTS_DIR for baseline_metrics.csv and summary.csv"
