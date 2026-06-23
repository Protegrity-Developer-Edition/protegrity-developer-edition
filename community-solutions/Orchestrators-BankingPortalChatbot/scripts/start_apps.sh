#!/bin/bash
cd "$(dirname "$0")"

echo "=== Stopping existing app ==="
fuser -k 5002/tcp 2>/dev/null
sleep 1

echo "=== Starting TechnicalApp on port 5002 ==="
python TechnicalApp/run.py &
TECH_PID=$!
echo "TechnicalApp PID: $TECH_PID"
sleep 3

echo ""
echo "=== Status ==="
curl -s -o /dev/null -w "TechnicalApp :5002 → HTTP %{http_code}\n" http://localhost:5002/tech/login || echo "  ⚠️  TechnicalApp not responding"
echo ""
echo "To stop: fuser -k 5002/tcp"
