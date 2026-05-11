#!/bin/bash
# Arxiv Nova Knowledge Engine — Auto-start Script
# Arranca el servidor Flask + Scheduler RAPH en background
# Se integra con el Enjambre Homonexus (puerto 9100)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGDIR"

echo "📚 Arxiv Nova Knowledge Engine v1.0"
echo "   Starting server on port 9100..."

# Kill any existing arxiv server on port 9100
fuser -k 9100/tcp 2>/dev/null
sleep 1

# Start server
cd "$SCRIPT_DIR"
nohup python3 -B server.py > "$LOGDIR/server.log" 2>&1 &

PID=$!
echo "   PID: $PID"
echo "   Log: $LOGDIR/server.log"
echo "   Dashboard: http://localhost:9100"
echo "   Genesis: http://localhost:9088/arxiv-nova"

# Save PID for stopping
echo $PID > "$LOGDIR/server.pid"

# Quick health check
sleep 3
if curl -s --max-time 3 http://localhost:9100/api/status > /dev/null 2>&1; then
    echo "   ✅ Server healthy"
else
    echo "   ⚠️  Server may need more time to start (check log)"
fi

echo ""
echo "To stop: kill \$(cat $LOGDIR/server.pid)"
