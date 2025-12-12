from datetime import datetime
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================
# Utility Functions
# ==========================

def parse_log_line(line):
    """
    Parse a log line that may be in Python list format:
    [0, 0, 1, 0, ...] or space-separated numbers.
    Expects at least 8 numeric fields:
    client_id snapshot_id seq_num server_timestamp_ms recv_time_ms cpu_percent perceived_position_error bandwidth_per_client_kbps
    """
    line = line.strip()
    if not line or line.startswith("[SNAPSHOT]") or line.startswith("client_id"):
        return None

    # Remove brackets and split by comma or space
    line = line.replace('[', '').replace(']', '').replace(',', ' ')
    parts = line.split()
    if len(parts) < 8:
        print(f"[DEBUG] Skipping line (not enough fields): {line}")
        return None
    try:
        return {
            "client_id": int(parts[0]),
            "snapshot_id": int(parts[1]),
            "seq_num": int(parts[2]),
            "server_timestamp_ms": float(parts[3]),
            "recv_time_ms": float(parts[4]),
            "cpu_percent": float(parts[5]),
            "perceived_position_error": float(parts[6]),
            "bandwidth_per_client_kbps": float(parts[7])
        }
    except ValueError as e:
        print(f"[DEBUG] Skipping line (parse error): {line} -> {e}")
        return None


def load_log_file(file_path):
    rows = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = parse_log_line(line)
                    if entry:
                        rows.append(entry)
    except Exception as e:
        print(f"[WARN] Could not read {file_path}: {e}")
    df = pd.DataFrame(rows)
    if not df.empty:
        df["latency_ms"] = df["recv_time_ms"] - df["server_timestamp_ms"]
        df["jitter_ms"] = df["latency_ms"].diff().abs().fillna(0)
    return df


def compute_statistics(df):
    """Compute mean, median, and 95th percentile for key metrics."""
    stats = {
        "mean_latency_ms": df["latency_ms"].mean(),
        "median_latency_ms": df["latency_ms"].median(),
        "p95_latency_ms": np.percentile(df["latency_ms"], 95),
        "mean_jitter_ms": df["jitter_ms"].mean(),
        "median_jitter_ms": df["jitter_ms"].median(),
        "p95_jitter_ms": np.percentile(df["jitter_ms"], 95),
        "mean_error": df["perceived_position_error"].mean(),
        "median_error": df["perceived_position_error"].median(),
        "p95_error": np.percentile(df["perceived_position_error"], 95),
        "mean_cpu_percent": df["cpu_percent"].mean(),
        "mean_bandwidth_kbps": df["bandwidth_per_client_kbps"].mean()
    }
    return stats


# ==========================
# Main Processing Logic
# ==========================

def main():
    results_dir = Path("./results")
    summary_csv = results_dir / f"summary{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

    all_rows = []

    # Recursively find all .log files
    log_files = list(results_dir.rglob("*/server_metrics.csv"))
    if not log_files:
        print(f"[ERROR] No log files found under {results_dir}")
        return

    for file_path in sorted(log_files):
        test_name = file_path.parent.name
        print(f"[INFO] Processing log file: {file_path}")

        df = load_log_file(file_path)
        if df.empty:
            print(f"[WARN] No valid rows in {file_path}, skipping.")
            continue

        # Save detailed metrics
        detailed_csv = results_dir / f"{test_name}_metrics{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        df.to_csv(detailed_csv, index=False)
        print(f"[INFO] Saved detailed metrics to {detailed_csv}")

        # Compute stats for summary
        stats = compute_statistics(df)
        stats["file"] = test_name
        all_rows.append(stats)

    if not all_rows:
        print("[ERROR] No valid results found to generate summary!")
        return

    # Generate summary CSV
    summary_df = pd.DataFrame(all_rows)
    summary_df = summary_df[
        [
            "file",
            "mean_latency_ms", "median_latency_ms", "p95_latency_ms",
            "mean_jitter_ms", "median_jitter_ms", "p95_jitter_ms",
            "mean_error", "median_error", "p95_error",
            "mean_cpu_percent", "mean_bandwidth_kbps"
        ]
    ]
    summary_df.to_csv(summary_csv, index=False)
    print(f"\n Summary written to {summary_csv}")
    summary_df.to_csv(summary_csv, index=False)
    print(f"\n Summary written to {summary_csv}")
    print(summary_df)

    # Generate Comparison Plots
    plot_comparisons(summary_csv, results_dir)


def plot_comparisons(summary_csv, results_dir):
    try:
        df = pd.read_csv(summary_csv)
    except Exception as e:
        print(f"Could not read summary.csv: {e}")
        return

    # Extract clean labels and sort
    def get_label(fname):
        if "baseline" in fname: return "Baseline"
        if "loss_2" in fname: return "Loss 2%"
        if "loss_5" in fname: return "Loss 5%"
        if "delay_100ms" in fname: return "Delay 100ms"
        return fname
    
    df['Label'] = df['file'].apply(get_label)
    
    # Sort order: Baseline, Loss 2, Loss 5, Delay, Others
    order_map = {"Baseline": 0, "Loss 2%": 1, "Loss 5%": 2, "Delay 100ms": 3}
    df['sort_val'] = df['Label'].map(order_map).fillna(99)
    df = df.sort_values('sort_val')

    metrics = [
        ("mean_latency_ms", "Mean Latency (ms)", "latency_comparison.png"),
        ("mean_jitter_ms", "Mean Jitter (ms)", "jitter_comparison.png"),
        ("mean_error", "Mean Perceived Error", "error_comparison.png"),
        ("mean_bandwidth_kbps", "Mean Bandwidth (kbps)", "bandwidth_comparison.png")
    ]

    for col, title, fname in metrics:
        if col not in df.columns: continue
        plt.figure(figsize=(8, 5))
        bars = plt.bar(df['Label'], df[col], color='skyblue', edgecolor='black')
        plt.xlabel("Scenario")
        plt.ylabel(title)
        plt.title(f"Comparison: {title}")
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        
        # Add values on top
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), va='bottom', ha='center')
            
        plt.tight_layout()
        plt.savefig(results_dir / fname)
        plt.close()

    # --- Plot vs Loss Rate (Line Chart) ---
    loss_df = df[df['Label'].isin(["Baseline", "Loss 2%", "Loss 5%"])].copy()
    if not loss_df.empty:
        loss_map = {"Baseline": 0, "Loss 2%": 2, "Loss 5%": 5}
        loss_df['LossRate'] = loss_df['Label'].map(loss_map)
        loss_df = loss_df.sort_values('LossRate')

        loss_metrics = [
            ("mean_latency_ms", "Latency vs Loss Rate", "latency_vs_loss.png"),
            ("mean_jitter_ms", "Jitter vs Loss Rate", "jitter_vs_loss.png"),
            ("mean_error", "Error vs Loss Rate", "error_vs_loss.png")
        ]

        for col, title, fname in loss_metrics:
            plt.figure(figsize=(6, 4))
            plt.plot(loss_df['LossRate'], loss_df[col], marker='o', linestyle='-', color='teal')
            plt.xlabel("Packet Loss Rate (%)")
            plt.ylabel(col.replace('_', ' ').title())
            plt.title(title)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.xticks([0, 2, 5])
            plt.tight_layout()
            plt.savefig(results_dir / fname)
            plt.close()
            
    print("[PLOTS] Comparison plots generated.")


if __name__ == "__main__":
    main()
