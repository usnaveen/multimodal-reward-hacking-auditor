#!/bin/bash
# Watchdog: keeps restarting the audit until all 1600 items are done.
# Run this in a terminal and leave it open.
# Press Ctrl+C to stop.

REPO="$(cd "$(dirname "$0")" && pwd)"
RAW="$REPO/results/audit_raw_claude-haiku-4-5.jsonl"
TOTAL=1600

echo "=== MRHA Audit Watchdog ==="
echo "Target: $TOTAL items"
echo "Stream: $RAW"
echo "Press Ctrl+C to stop."
echo ""

export SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem
PYTHON="$REPO/.venv/bin/python3.12"

while true; do
  # Count how many are done
  DONE=0
  if [ -f "$RAW" ]; then
    DONE=$(wc -l < "$RAW" | tr -d ' ')
  fi

  echo "[$(date +%H:%M:%S)] $DONE/$TOTAL scored"

  if [ "$DONE" -ge "$TOTAL" ]; then
    echo "✅ All $TOTAL items scored! Audit complete."
    echo "Results: $REPO/results/audit_records.jsonl"
    break
  fi

  # Check if already running
  if pgrep -f "02_run_audit.py.*anthropic" > /dev/null 2>&1; then
    sleep 15
    continue
  fi

  echo "[$(date +%H:%M:%S)] Process not running — restarting (resume from $DONE)..."
  "$PYTHON" "$REPO/scripts/02_run_audit.py" \
    --backend anthropic \
    --model-id claude-haiku-4-5 \
    2>&1 | grep -E "resume|audit|Error|Traceback" &

  sleep 20
done
