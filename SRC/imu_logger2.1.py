#!/usr/bin/env python3
import subprocess
import csv
import datetime
import os
import signal
import sys
import time
import RPi.GPIO as GPIO
import select

# ----- BUTTON CONFIG -----
START_PIN = 13
STOP_PIN = 17
LOG_LED = 21

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(START_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(STOP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LOG_LED, GPIO.OUT)

# ----- CONFIG -----
SERIAL_PORT = "/dev/ttyS0"
RAW_LOGFILE = "/home/m1000/wt901/witmotion_raw.log"
PARSED_LOGFILE = "/home/m1000/wt901/witmotion_parsed.csv"

CMD = ["/home/m1000/wt901/bin/witmotion-debug", "--path", SERIAL_PORT, "--verbose"]

IDLE_MARKERS = ["state: idle -> idle"]
PAYLOAD_CODES = {
    "0x52": "angular_velocity",
    "0x53": "angle",
    "0x51": "Acceleration"
}

# ----- GLOBALS -----
running = True

# Graceful exit
def signal_handler(sig, frame):
    global running
    print("\nKeyboard interrupt detected. Stopping logger...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# Ensure files exist
raw_file = open(RAW_LOGFILE, "a")
csv_exists = os.path.exists(PARSED_LOGFILE)
csv_file = open(PARSED_LOGFILE, "a", newline="")
csv_writer = csv.writer(csv_file)

if not csv_exists:
    csv_writer.writerow(["timestamp", "type", "data", "checksum_status"])

# Write session-start marker so parser can anchor wall-clock time per frame
raw_file.write(f"SESSION_START {datetime.datetime.now().isoformat()}\n")
raw_file.flush()

print(f"Logger ready. Raw log: {RAW_LOGFILE}, Parsed CSV: {PARSED_LOGFILE}")

# ----- WAIT FOR START BUTTON -----
print("Waiting for START button...")
while running:
    if GPIO.input(START_PIN) == GPIO.LOW:
        print("START pressed. Launching IMU logger...")
        break
    time.sleep(0.05)

# ----- START IMU PROCESS -----
process = subprocess.Popen(
    CMD,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# LED state tracking
log_led_state = False
last_led_toggle = time.time()

try:
    while running:
        # --- TOGGLE LOG_LED (4Hz) ---
        if time.time() - last_led_toggle >= 0.125:
            log_led_state = not log_led_state
            GPIO.output(LOG_LED, log_led_state)
            last_led_toggle = time.time()
        
        # --- STOP BUTTON CHECK ---
        if GPIO.input(STOP_PIN) == GPIO.LOW:
            print("STOP pressed. Stopping logger...")
            running = False
            break

        # --- NON-BLOCKING READ ---
        ready, _, _ = select.select([process.stdout], [], [], 0.1)
        if ready:
            line = process.stdout.readline()
        else:
            continue

        # Log raw line with wall-clock timestamp prefix
        raw_file.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {line}")
        raw_file.flush()

        # Skip obvious idle lines
        if any(marker in line for marker in IDLE_MARKERS):
            continue

        # Parse payload
        if "payload" in line:
            timestamp = datetime.datetime.now().isoformat()
            checksum_status = "OK"

            # Check next line for checksum warning
            ready_next, _, _ = select.select([process.stdout], [], [], 0.05)
            if ready_next:
                next_line = process.stdout.readline()
                if "invalid checksum" in next_line:
                    checksum_status = "INVALID"
                    raw_file.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {next_line}")
                    raw_file.flush()

            # Determine type
            packet_type = "unknown"
            for code in PAYLOAD_CODES:
                if f"code {code}" in line:
                    packet_type = PAYLOAD_CODES[code]
                    break

            # Extract data
            data = line.split(":", 1)[-1].strip()
            csv_writer.writerow([timestamp, packet_type, data, checksum_status])
            csv_file.flush()

except Exception as e:
    print(f"Error: {e}")
finally:
    running = False
    GPIO.output(LOG_LED, GPIO.LOW)  # Turn off LED when stopping
    process.terminate()
    process.wait()
    raw_file.close()
    csv_file.close()
    GPIO.cleanup()
    print("Logger stopped, files closed.")
