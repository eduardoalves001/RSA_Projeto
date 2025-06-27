#!/bin/bash

echo "Starting generate_crashed.py..."
python3 generate_crashed.py &
PID1=$!

echo "Starting generate_car.py..."
python3 generate_car.py &
PID2=$!

echo "Starting generate_ambulance.py..."
python3 generate_ambulance.py &
PID3=$!

# Wait for both to finish
wait $PID1
wait $PID2
wait $PID3

echo "All scripts finished running."