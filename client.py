import socket
import struct
import time
import random
import os
from protocol import (
    create_header, parse_header,
    MSG_TYPE_JOIN_REQ, MSG_TYPE_JOIN_RESP,
    MSG_TYPE_CLAIM_REQ, MSG_TYPE_BOARD_SNAPSHOT, MSG_TYPE_LEAVE
)

# -------------------------------
# Config
# -------------------------------
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005
OUTDIR = "results"
os.makedirs(OUTDIR, exist_ok=True)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(0.5)

seq_num = 0
player_id = None

# -------------------------------
# Join Phase
# -------------------------------
join_req = create_header(MSG_TYPE_JOIN_REQ, seq_num, 0)
client_socket.sendto(join_req, (SERVER_IP, SERVER_PORT))
print("[JOIN] Sent JOIN_REQUEST")
seq_num += 1

while True:
    try:
        data, addr = client_socket.recvfrom(1024)
        header = parse_header(data)
        if header["msg_type"] == MSG_TYPE_JOIN_RESP:
            player_id = struct.unpack("!B", data[22:])[0]
            print(f"[JOIN] Assigned PlayerID={player_id}")
            break
    except socket.timeout:
        continue

# Create numeric log file
numeric_log_path = f"{OUTDIR}/client_{player_id}.txt"
numeric_log = open(numeric_log_path, "w")

# -------------------------------
# Main Loop
# -------------------------------
start = time.time()
claimed = set()

while time.time() - start < 30:
    row, col = random.randint(0, 19), random.randint(0, 19)
    if (row, col) in claimed:
        continue
    claimed.add((row, col))

    payload = struct.pack("!BB", row, col)
    claim_req = create_header(MSG_TYPE_CLAIM_REQ, seq_num, len(payload)) + payload
    client_socket.sendto(claim_req, (SERVER_IP, SERVER_PORT))
    print(f"[CLAIM] Sent CLAIM_REQUEST for ({row},{col})")
    seq_num += 1

    try:
        while True:
            data, addr = client_socket.recvfrom(2048)
            recv_time_ms = int(time.time() * 1000)
            header = parse_header(data)

            if header["msg_type"] == MSG_TYPE_BOARD_SNAPSHOT:
                snapshot_id = header.get("seq_num", 0)
                server_ts_ms = recv_time_ms  # fallback

                # Write to numeric log (not print)
                numeric_log.write(f"{player_id} {snapshot_id} {seq_num} {server_ts_ms} {recv_time_ms} 0.0 0.0 0.0\n")
                numeric_log.flush()

                print(f"[SNAPSHOT] Player {player_id} received SnapshotID={snapshot_id}")
                break

    except socket.timeout:
        continue

# -------------------------------
# Leave Phase
# -------------------------------
leave_msg = create_header(MSG_TYPE_LEAVE, seq_num, 0)
client_socket.sendto(leave_msg, (SERVER_IP, SERVER_PORT))
print("[INFO] Sent LEAVE message.")
client_socket.close()
numeric_log.close()
print(f"[INFO] Client closed. Numeric log saved to {numeric_log_path}")
