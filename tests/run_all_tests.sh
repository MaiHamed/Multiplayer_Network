#!/bin/bash

# ===============================
# run_all_tests.sh
# Git Bash friendly test runner
# ===============================

# Paths (relative to the tests folder)
SERVER_PATH="../server.py"
CLIENT_PATH="../client.py"

# Test configuration
NUM_CLIENTS=4
TEST_DURATION=20  # seconds

# Arrays to store PIDs
SERVER_PID=0
CLIENT_PIDS=()

# Function to start a Python script in the background and log output
start_python() {
    local script_path=$1
    local log_file=$(basename "$script_path" .py).log
    echo "Starting $script_path..."
    python "$script_path" > "../tests/$log_file" 2>&1 &
    echo $!  # Return PID
}

# ===============================
# Start server
# ===============================
SERVER_PID=$(start_python "$SERVER_PATH")
echo "Server PID: $SERVER_PID"

# Give the server a moment to start
sleep 2

# ===============================
# Start clients
# ===============================
for ((i=1; i<=NUM_CLIENTS; i++)); do
    CLIENT_PID=$(start_python "$CLIENT_PATH")
    CLIENT_PIDS+=($CLIENT_PID)
    echo "Started client $i with PID $CLIENT_PID"
    sleep 1
done

# ===============================
# Let the test run
# ===============================
echo "Test running for $TEST_DURATION seconds..."
sleep $TEST_DURATION

# ===============================
# Cleanup
# ===============================
echo "Stopping clients..."
for pid in "${CLIENT_PIDS[@]}"; do
    kill $pid 2>/dev/null
done

echo "Stopping server..."
kill $SERVER_PID 2>/dev/null

echo "Test completed. Check logs in the tests/ folder:"
echo " - server.log"
for ((i=1; i<=NUM_CLIENTS; i++)); do
    echo " - client${i}.log"
done
