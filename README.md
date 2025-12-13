# Multiplayer Network Game – Phase 2

**Grid State Synchronization Protocol (GSSP)**

## Overview

This project is a **UDP-based multiplayer grid game** developed as part of the **Networking Course Project – Phase 2**.
It extends the Phase 1 prototype by implementing a **reliable, event-driven synchronization protocol (GSSP)** with **Selective Repeat ARQ**, a **waiting room system**, **leaderboard**, and **automated network testing**.

The server acts as an **authoritative node**, maintaining the global grid state and synchronizing all connected clients using **delta-based board snapshots**. Communication is optimized for **low latency** and **bandwidth efficiency**, even under packet loss and delay.

---

## Key Features (Phase 2 Enhancements)

* Custom UDP protocol (**GSSP**) with:

  * Sequence numbers
  * Acknowledgments
  * Selective Repeat ARQ
  * Per-packet timers
* Waiting Room System:

  * Minimum **2 players** required to start
  * **1-minute countdown** once minimum players join
  * **Start Now** option to skip waiting
* Real-time Grid Gameplay:

  * Players can **claim cells**
  * Players can **reclaim cells from other players**
* Fixed game duration (**100 seconds**)
* End-game **Leaderboard popup**
* “Play Again” support (returns players to waiting room)
* Automated testing under **packet loss and delay** using `netem`
* CSV logging and performance metrics collection

---

## Project Structure
```
.
├── launcher.py # Starts server and launches clients
├── server.py # Authoritative game server
├── client.py # Game client
├── protocol.py # GSSP message formats & helpers
├── waiting_room.py # Waiting room logic
├── leaderboard.py # End-game leaderboard popup
├── gui.py # Game GUI components
├── tests
│ ├── run_all_tests.sh # Automated netem test runner
│ ├── analyze_results.py # Post-test CSV analysis
│ ├── generate_plots.py # Generate graphs from test results
│ ├── postprocess.py # Data postprocessing utilities
│ ├── test_client.py # Unit tests for client
│ └── test_server.py # Unit tests for server
│ └── results
|  ├── logs # CSV logs (latency, jitter, error)
└── README.md
```


---

## Requirements

* Python **3.8+**
* Linux environment (for `tc netem` testing)
* Standard Python libraries:

  * `socket`
  * `struct`
  * `time`
  * `threading`
  * `select`

No external Python dependencies are required.

---

## How the System Works

### 1. Launcher & Startup

* `launcher.py` starts the **server**
* Clients are launched from the launcher interface

### 2. Waiting Room

* Players enter a waiting room upon joining
* Game starts when:

  * At least **2 players** are present, **and**
  * Either:

    * The **1-minute timer expires**, or
    * A player clicks **Start Now**

### 3. Gameplay

* Duration: **100 seconds**
* Players send **CLAIM_REQUEST** messages to claim or steal grid cells
* Server validates actions and broadcasts **BOARD_SNAPSHOT** updates
* Clients update their local view using received snapshots

### 4. End of Game

* Server sends **GAME_OVER**
* Leaderboard popup shows final rankings
* Players may choose **Play Again**, returning to the waiting room

---

## Protocol Summary (GSSP)

* Transport: **UDP**
* Model: **Client–Server**
* Reliability: **Selective Repeat ARQ**
* Update Strategy: **Event-driven (no periodic streaming)**

### Supported Message Types

| MsgType | Description    |
| ------- | -------------- |
| 0       | JOIN_REQUEST   |
| 1       | JOIN_RESPONSE  |
| 2       | CLAIM_REQUEST  |
| 3       | BOARD_SNAPSHOT |
| 4       | GAME_OVER      |
| 5       | LEAVE          |
| 6       | GAME START     |
| 7       | WAITING_ROOM   |
| 8       | ACK            |
| 9       | LEADERBOARD    |


Each message includes:

* Sequence number
* Acknowledgment number
* Snapshot ID
* Timestamp
* Variable payload

---

## Running the Project Locally

### Step 1 — Start the Launcher

```bash
 for mac : python3 launcher.py
 for windows: python launcher.py
```

### Step 2 — Launch Server

* Click **Start Server** from the launcher

### Step 3 — Launch Clients

* Click **New Client**
* Each client joins the waiting room automatically

### Step 4 — Start the Game

* Wait for the minimum players or click **Start Now**

---

## Testing & Network Simulation (Phase 2)

All tests are automated using **Linux netem**.

### Example Commands

**2% Packet Loss**
sudo tc qdisc add dev <IF> root netem loss 2%


**5% Packet Loss**
sudo tc qdisc add dev <IF> root netem loss 5%

**100 ms Delay**
sudo tc qdisc add dev <IF> root netem delay 100ms


**Remove netem:**
sudo tc qdisc del dev <IF> root

**Automated Test Execution**
cd tests
./run_all_tests.sh


---

## Metrics Collected

Each test produces CSV logs with:

* `client_id`
* `snapshot_id`
* `seq_num`
* `server_timestamp_ms`
* `recv_time_ms`
* `latency_ms`
* `jitter_ms`
* `perceived_position_error`
* `cpu_percent`
* `bandwidth_per_client_kbps`

Reported statistics:

* Mean
* Median
* 95th percentile

---

## Acceptance Criteria Coverage

| Scenario     | Result                            |
| ------------ | --------------------------------- |
| Baseline     | ≤ 50 ms latency, stable CPU       |
| 2% Loss      | Graceful interpolation, low error |
| 5% Loss      | ≥ 99% critical event delivery     |
| 100 ms Delay | Stable gameplay, no desync        |

---

## Notes

* Server **must be started before clients**
* Communication uses **UDP over localhost**
* Snapshots are sent **only on state changes**
* Logs are generated for testing and evaluation

---

