#!/bin/bash
# Start Bloodbank subscribers for Node-RED Fireflies flow

set -e

SCRIPTS_DIR="/home/delorenj/code/33GOD/services/node-red-flow-orchestrator/scripts"
LOG_DIR="$HOME/.node-red/logs"
export RABBIT_URL="amqp://guest:guest@localhost:5672/"

mkdir -p "$LOG_DIR"
pkill -f "bloodbank_subscribe.py" || true
sleep 1

# Start subscribers
nohup "$SCRIPTS_DIR/.venv/bin/python" -u \
  "$SCRIPTS_DIR/bloodbank_subscribe.py" \
  --routing-key fireflies.transcript.upload \
  --queue node-red.fireflies.upload \
  > "$LOG_DIR/subscriber-upload.log" 2>&1 &
UPLOAD_PID=$!

nohup "$SCRIPTS_DIR/.venv/bin/python" -u \
  "$SCRIPTS_DIR/bloodbank_subscribe.py" \
  --routing-key fireflies.transcript.ready \
  --queue node-red.fireflies.ready \
  > "$LOG_DIR/subscriber-ready.log" 2>&1 &
READY_PID=$!

sleep 2

if ps -p $UPLOAD_PID > /dev/null; then
  echo "✓ Upload subscriber started (PID: $UPLOAD_PID)"
else
  echo "✗ Upload subscriber failed"
  exit 1
fi

if ps -p $READY_PID > /dev/null; then
  echo "✓ Ready subscriber started (PID: $READY_PID)"
else
  echo "✗ Ready subscriber failed"
  exit 1
fi

echo ""
echo "Logs: $LOG_DIR/subscriber-{upload,ready}.log"
