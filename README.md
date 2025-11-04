# Multiplayer_Network
Overview

This project implements a UDP-based client-server prototype as part of the Networking Course Project (Phase 1).
It demonstrates the exchange of INIT (JOIN) and DATA (CLAIM) messages over UDP using a custom protocol described in the accompanying Mini-RFC.

⸻

## Requirements

To run the project locally, ensure the following are installed:
	•	Python 3.8 or higher
	•	Standard Python libraries (socket, struct)

No external dependencies are required.

⸻

## How It Works
	1.	The server listens on a predefined UDP port for incoming messages.
	2.	A client initiates communication by sending a JOIN_REQ message.
	3.	The server assigns a unique player ID and replies with a JOIN_RESP.
	4.	The client can send CLAIM_REQ messages to mark specific cells on the grid.
	5.	The server maintains the shared grid state and logs all actions.
	6.	When a client sends a LEAVE message, the server removes it from the active client list.

⸻

## Running the Project Locally
  - Step 1 — Start the Server
    - run in terminal: python3 server.py
  - Step 2 — Start the Clients
    - In separate terminals, run: python3 client.py
    - Each client will receive a unique player ID and can send claim requests or disconnect messages.
  - Step 3 — Observe Logs
    - The server will print real-time communication logs

  ⸻
  
  ## Notes
	•	The server must be started before any clients connect.
	•	All messages are exchanged over UDP on the localhost interface (127.0.0.1).
	•	Logs are printed to the console for debugging and verification.
