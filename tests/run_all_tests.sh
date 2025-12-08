#!/bin/bash
# test_game_advanced.sh
# Advanced test scenario for SR ARQ game

# ------------------------------
# CONFIGURATION
SERVER_SCRIPT="server.py"
CLIENT_SCRIPT="client.py"
NUM_CLIENTS=4
TEST_DURATION=20  # seconds
PACKET_DROP_RATE=0.1  # 10% simulated packet loss
PACKET_DELAY_MAX=0.05 # max delay in seconds

# ------------------------------
# Start server
echo "Starting server..."
python $SERVER_SCRIPT &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 1  # give server time to start

# ------------------------------
# Start clients
CLIENT_PIDS=()
for i in $(seq 1 $NUM_CLIENTS); do
    echo "Starting client $i..."
    # pass drop/delay as args to client.py (modify client.py to accept them)
    python $CLIENT_SCRIPT --no-gui --drop-rate $PACKET_DROP_RATE --max-delay $PACKET_DELAY_MAX &
    CLIENT_PIDS+=($!)
    sleep 0.5
done

# ------------------------------
# Run the test
echo "Test running for $TEST_DURATION seconds..."
sleep $TEST_DURATION

# ------------------------------
# Stop clients
echo "Stopping clients..."
for pid in "${CLIENT_PIDS[@]}"; do
    kill $pid
done

# ------------------------------
# Stop server
echo "Stopping server..."
kill $SERVER_PID

echo "Test complete!"
echo "Check client and server logs for sent/received/dropped statistics."
