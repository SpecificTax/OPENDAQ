#!/bin/bash
# run_bootloader.sh
# Safe wrapper to launch bootloader under systemd using venv Python

# Absolute paths
VENV_PYTHON="/home/m1000/wt901/bin/python"
BOOTLOADER_PY="/home/m1000/wt901/bootloadervw.py"
LOG_DIR="/home/m1000/wt901"
RAW_LOG="$LOG_DIR/witmotion_raw.log"
PARSED_LOG="$LOG_DIR/witmotion_parsed.csv"

# Optional: export paths so subprocesses see venv first
export PATH="/home/m1000/wt901/bin:$PATH"

# Optional: log systemd wrapper startup
echo "$(date) - Starting bootloader via run_bootloader.sh" >> "$RAW_LOG"

# Launch bootloader
exec "$VENV_PYTHON" "$BOOTLOADER_PY" >> "$RAW_LOG" 2>&1
