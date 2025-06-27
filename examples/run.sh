#!/bin/bash

# Função para matar os processos ao receber Ctrl+C
cleanup() {
    echo "Caught Ctrl+C, terminating child processes..."
    kill $PID1 $PID2 $PID3 2>/dev/null
    exit 1
}

# Liga o handler ao sinal SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "Starting generate_crashed.py..."
python3 generate_crashed.py &
PID1=$!

echo "Starting generate_car.py..."
python3 generate_car.py &
PID2=$!

echo "Starting generate_ambulance.py..."
python3 generate_ambulance.py &
PID3=$!

# Espera os processos terminarem (ou Ctrl+C ser capturado)
wait $PID1
wait $PID2
wait $PID3

echo "All scripts finished running."
