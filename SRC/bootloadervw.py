#!/usr/bin/env python3
import RPi.GPIO as GPIO
import subprocess
import time

# ---------- GPIO CONFIG ----------
BOOT_LED = 26
ARMED_LED = 19
START_BTN = 13

# ---------- LOGGER CONFIG ----------
PYTHON_BIN = "/home/m1000/wt901/bin/python"
LOGGER_PATH = "/home/m1000/wt901/imu_logger2.1.py"

# ---------- INITIAL SETUP ----------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BOOT_LED, GPIO.OUT)
GPIO.setup(ARMED_LED, GPIO.OUT)
GPIO.setup(START_BTN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.output(BOOT_LED, GPIO.HIGH)
GPIO.output(ARMED_LED, GPIO.LOW)

print("Bootloader started. System alive.")
running = True

# ---------- MAIN LOOP ----------
try:
    while running:
        # Wait for START button
        armed_led_state = False
        last_blink = time.time()
        
        while GPIO.input(START_BTN) == GPIO.HIGH:
            # Blink ARMED_LED ~1Hz
            if time.time() - last_blink > 0.5:
                armed_led_state = not armed_led_state
                GPIO.output(ARMED_LED, armed_led_state)
                last_blink = time.time()
            time.sleep(0.01)
        
        print("START pressed. Launching logger.")
        GPIO.output(ARMED_LED, GPIO.LOW)
        
        # Release GPIO for logger
        GPIO.cleanup()
        
        # Spawn logger and WAIT for it to finish
        logger_process = subprocess.Popen([PYTHON_BIN, LOGGER_PATH])
        logger_process.wait()  # BLOCK until logger exits
        
        print(f"Logger exited with code {logger_process.returncode}. Returning to wait state.")
        
        # Re-initialize LEDs for next wait cycle
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BOOT_LED, GPIO.OUT)
        GPIO.setup(ARMED_LED, GPIO.OUT)
        GPIO.setup(START_BTN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        GPIO.output(BOOT_LED, GPIO.HIGH)
        GPIO.output(ARMED_LED, GPIO.LOW)

except KeyboardInterrupt:
    print("Bootloader interrupted by user.")
finally:
    GPIO.cleanup()
    print("Bootloader exiting.")
