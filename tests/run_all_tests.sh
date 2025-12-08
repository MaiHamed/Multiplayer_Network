#!/bin/bash

# =============================
# Run server and clients for test
# =============================

# Function to start Python script and return PID
start_python() {
    local script_path=$1
    echo "Starting $script_path..."
    cmd.exe /C "start /B python \"$script_path\"" 
}

# Paths (adjust if your scripts move)
SERVER_PATH="../server.py"
CLIENT_PATH="../client.py"

# Start server
echo "Starting server..."
start_python "$SERVER_PATH"
SERVER_PID=$!
echo "Server started."

# Give server some time to initialize
sleep 2

# Start clients
NUM_CLIENTS=4
for i in $(seq 1 $NUM_CLIENTS); do
    echo "Starting client $i..."
    start_python "$CLIENT_PATH"
    sleep 1
done

# Run test for 20 seconds
TEST_DURATION=20
echo "Running test for $TEST_DURATION seconds..."
sleep $TEST_DURATION

# Kill server and clients
echo "Stopping server and clients..."
# On Windows, we can use taskkill
taskkill //F //IM python.exe //T > /dev/null 2>&1

echo "Test finished."
