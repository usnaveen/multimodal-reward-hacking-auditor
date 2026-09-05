#!/bin/bash
# Persistent audit launcher — survives Wibey session timeouts.
# Re-run this script any time to resume from where it left off.
#
# Usage:  bash run_audit_bg.sh
#
# Progress:  tail -f /tmp/mrha_audit.log
# Results:   results/audit_records.jsonl  (written when complete)
#            results/audit_raw_claude-haiku-4-5.jsonl  (streaming, grows as it runs)

set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$REPO/.venv/bin/python3.12"
LOG="/tmp/mrha_audit.log"

export SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem

# Check if already running
if pgrep -f "02_run_audit.py.*anthropic" > /dev/null 2>&1; then
  echo "Audit already running. Check progress:"
  echo "  tail -f $LOG"
  echo "  wc -l $REPO/results/audit_raw_claude-haiku-4-5.jsonl"
  exit 0
fi

echo "[$(date)] Starting MRHA audit (claude-haiku-4-5, resume=true)" | tee -a "$LOG"
echo "Progress log: tail -f $LOG"
echo "Raw stream:   wc -l $REPO/results/audit_raw_claude-haiku-4-5.jsonl"

nohup "$PYTHON" "$REPO/scripts/02_run_audit.py" \
  --backend anthropic \
  --model-id claude-haiku-4-5 \
  >> "$LOG" 2>&1 &

PID=$!
echo "[$(date)] Launched PID $PID" | tee -a "$LOG"
echo "PID: $PID"
