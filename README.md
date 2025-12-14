# Multiplayer Network Game – Phase 2

**Grid State Synchronization Protocol (GSSP)**
- [Multiplayer Network Game – Phase 2](#multiplayer-network-game--phase-2)
  - [Overview](#overview)
  - [Design Rationale \& Mechanisms](#design-rationale--mechanisms)
    - [1. Transport Layer: UDP with Custom Reliability](#1-transport-layer-udp-with-custom-reliability)
    - [2. Error Control: Selective Repeat ARQ](#2-error-control-selective-repeat-arq)
    - [3. State Management: Authoritative Server](#3-state-management-authoritative-server)
    - [4. Bandwidth Optimization: Event-Driven Delta Snapshots](#4-bandwidth-optimization-event-driven-delta-snapshots)
  - [Key Features (Phase 2 Enhancements)](#key-features-phase-2-enhancements)
  - [Project Structure](#project-structure)
  - [Requirements](#requirements)
  - [How the System Works](#how-the-system-works)
    - [1. Launcher \& Startup](#1-launcher--startup)
    - [2. Waiting Room](#2-waiting-room)
    - [3. Gameplay](#3-gameplay)
    - [4. End of Game](#4-end-of-game)
  - [Protocol Summary (GSSP)](#protocol-summary-gssp)
    - [Supported Message Types](#supported-message-types)
  - [Running the Project Locally](#running-the-project-locally)
    - [Step 1 — Start the Launcher](#step-1--start-the-launcher)
    - [Step 2 — Launch Server](#step-2--launch-server)
    - [Step 3 — Launch Clients](#step-3--launch-clients)
    - [Step 4 — Start the Game](#step-4--start-the-game)
  - [Testing \& Network Simulation (Phase 2)](#testing--network-simulation-phase-2)
    - [Example Commands](#example-commands)
  - [Metrics Collected](#metrics-collected)
  - [Acceptance Criteria Coverage](#acceptance-criteria-coverage)
  - [Notes](#notes)


## Overview

This project is a **UDP-based multiplayer grid game** developed as part of the **Networking Course Project – Phase 2**.
It extends the Phase 1 prototype by implementing a **reliable, event-driven synchronization protocol (GSSP)** with **Selective Repeat ARQ**, a **waiting room system**, **leaderboard**, and **automated network testing**.

The server acts as an **authoritative node**, maintaining the global grid state and synchronizing all connected clients using **delta-based board snapshots**. Communication is optimized for **low latency** and **bandwidth efficiency**, even under packet loss and delay.

---

## Design Rationale & Mechanisms

To achieve real-time performance while ensuring game state consistency, the system employs several specific architectural patterns and protocol designs.

### 1. Transport Layer: UDP with Custom Reliability
* **Decision:** Use UDP instead of TCP.
* **Reasoning:** TCP enforces strict ordering and retransmission, leading to **Head-of-Line (HOL) blocking**. In a real-time game, waiting for a lost packet to arrive before processing newer packets causes perceptible lag.

### 2. Error Control: Selective Repeat ARQ
* **Decision:** Implement Selective Repeat Automatic Repeat Request (ARQ).
* **Reasoning:** Simple "Stop-and-Wait" is too slow, and "Go-Back-N" wastes bandwidth by resending already-received packets.
* **Mechanism:**
    * The sender maintains a window of unacknowledged packets.
    * The receiver acknowledges packets individually.
    * Only specific lost packets are retransmitted after a per-packet timer expires, optimizing bandwidth usage under simulated packet loss (e.g., `netem` 5% loss).

### 3. State Management: Authoritative Server


* **Decision:** Server is the single source of truth.
* **Reasoning:** Peer-to-peer architectures are prone to race conditions (two players claiming a cell simultaneously) and cheating.
* **Mechanism:** Clients send `CLAIM_REQUEST` intents. The server processes these sequentially. If valid, the server updates the state and broadcasts a `BOARD_SNAPSHOT`. If invalid (e.g., cell already taken), the request is ignored or rejected, ensuring all clients eventually converge on the server's state.

### 4. Bandwidth Optimization: Event-Driven Delta Snapshots
* **Decision:** Send updates on state change only (Event-Driven), rather than a fixed tick rate (e.g., 60Hz streaming).
* **Reasoning:** Streaming the full board continuously consumes unnecessary bandwidth, especially when the grid is static.
* **Mechanism:** The server broadcasts `BOARD_SNAPSHOT` messages only when a player successfully claims a cell or the game phase changes. This "Delta" approach significantly reduces network load.

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

| Scenario     | Result                        |
| ------------ | ----------------------------- |
| Baseline     | ≤ 50 ms latency, stable CPU   |
| 2% Loss      | low error                     |
| 5% Loss      | ≥ 99% critical event delivery |
| 100 ms Delay | Stable gameplay, no desync    |

---

## Notes

* Server **must be started before clients**
* Communication uses **UDP over localhost**
* Snapshots are sent **only on state changes**
* Logs are generated for testing and evaluation

---

