#!/usr/bin/env python3
"""
WitMotion WT901 Logger v4
- Fixed API calls (enums, calibration, no get_temperature)
- Software axis remapping for upside-down (-Z up) mount
- Callback-based logging (correct API pattern for this library)
- Clean CSV output with corrected pitch/roll/yaw
- Improved interactive menu with live display

Mount orientation assumed:
    Physical Z: inverted (-Z points up)
    Physical X: lateral
    Physical Y: longitudinal, ALSO inverted
    
Corrections applied in software:
    corrected_roll  = raw_pitch             (Y longitudinal -> roll axis)
    corrected_pitch = raw_roll              (X lateral -> pitch axis)  
    corrected_yaw   = raw_yaw              (yaw unaffected by Z flip)
    accel_x corrected = raw_accel_x        (lateral, OK)
    accel_y corrected = -raw_accel_y       (longitudinal, INVERTED)
    accel_z corrected = -raw_accel_z       (vertical, INVERTED - was upside down)
    gyro_y corrected  = -raw_gyro_y        (inverted with Y axis)
    
NOTE: Verify these by driving and checking that:
    - Braking shows positive accel_y (decel in forward direction)
    - Left turn shows positive roll (body rolls right)
    - Pitch near 0 on flat road
"""

import time
import csv
import threading
from datetime import datetime

try:
    from witmotion import IMU, InstallationDirection, CalibrationMode
    import witmotion
except ImportError:
    print("ERROR: witmotion package not found.")
    print("Install with: pip install witmotion")
    raise

# ── Axis remapping ──────────────────────────────────────────────────────────

def remap_axes(accel, gyro, angle):
    """
    Correct raw sensor values for upside-down (-Z up) mounting.
    X = lateral, Y = longitudinal (inverted), Z = vertical (inverted)
    
    Returns dicts with corrected values.
    """
    ax, ay, az = accel
    gx, gy, gz = gyro
    roll_raw, pitch_raw, yaw_raw = angle  # device: roll=X, pitch=Y, yaw=Z

    corrected_accel = (
         ax,    # lateral: OK
        -ay,    # longitudinal: INVERTED
        -az,    # vertical: INVERTED (upside down)
    )
    corrected_gyro = (
         gx,
        -gy,    # inverted with Y
         gz,
    )
    # With -Z up mount, device 'roll' is actually vehicle pitch and vice versa
    # The ~-144 roll offset confirms full inversion: 180 - 144 = ~36deg mount angle
    # Subtract 180 from roll to correct for flip, then swap
    corrected_angle = (
        -(roll_raw + 180.0),  # vehicle pitch: correct for 180deg flip
         pitch_raw,           # vehicle roll: largely unaffected
         yaw_raw,             # yaw: heading unaffected by Z flip
    )
    return corrected_accel, corrected_gyro, corrected_angle


# ── Logger class ─────────────────────────────────────────────────────────────

class WT901Logger:
    def __init__(self, port='/dev/ttyS0', baudrate=9600):
        print(f"Connecting to {port} at {baudrate} baud...")
        self.device = IMU(path=port, baudrate=baudrate)
        self._lock = threading.Lock()
        self._latest = {}          # latest readings from callbacks
        self._csv_file = None
        self._csv_writer = None
        self._logging = False
        self._sample_count = 0
        self._log_start_time = None
        self._subscribe_all()
        time.sleep(0.3)            # let first messages arrive
        print("✓ Connected!\n")

    # ── Subscriptions (correct API pattern) ──

    def _subscribe_all(self):
        """Subscribe to all message types via callbacks."""
        try:
            from witmotion import (AccelerationMessage, AngularVelocityMessage,
                                   AngleMessage, MagneticMessage)
            self.device.subscribe(self._on_accel,   AccelerationMessage)
            self.device.subscribe(self._on_gyro,    AngularVelocityMessage)
            self.device.subscribe(self._on_angle,   AngleMessage)
            self.device.subscribe(self._on_mag,     MagneticMessage)
        except Exception as e:
            print(f"  Warning: Could not subscribe to all message types: {e}")
            # Fallback: subscribe without type filter (gets everything)
            self.device.subscribe(self._on_any)

    def _on_accel(self, msg):
        with self._lock:
            self._latest['accel'] = (msg.x, msg.y, msg.z)
            self._latest['temp_c'] = getattr(msg, 'temp_celsius', None)
        self._try_log_row()

    def _on_gyro(self, msg):
        with self._lock:
            self._latest['gyro'] = (msg.x, msg.y, msg.z)

    def _on_angle(self, msg):
        with self._lock:
            self._latest['angle'] = (msg.roll, msg.pitch, msg.yaw)

    def _on_mag(self, msg):
        with self._lock:
            self._latest['mag'] = (msg.x, msg.y, msg.z)

    def _on_any(self, msg):
        """Fallback handler if typed subscriptions fail."""
        with self._lock:
            msg_type = type(msg).__name__
            if 'Accel' in msg_type:
                self._latest['accel'] = (msg.x, msg.y, msg.z)
            elif 'Angular' in msg_type or 'Gyro' in msg_type:
                self._latest['gyro'] = (msg.x, msg.y, msg.z)
            elif 'Angle' in msg_type:
                self._latest['angle'] = (msg.roll, msg.pitch, msg.yaw)

    def _try_log_row(self):
        """Write a CSV row when we have fresh accel data (sync point)."""
        if not self._logging:
            return
        with self._lock:
            if 'accel' not in self._latest or 'gyro' not in self._latest or 'angle' not in self._latest:
                return
            accel = self._latest['accel']
            gyro  = self._latest['gyro']
            angle = self._latest['angle']
            mag   = self._latest.get('mag', (None, None, None))
            temp  = self._latest.get('temp_c', None)

        c_accel, c_gyro, c_angle = remap_axes(accel, gyro, angle)
        ts_ms = int(time.time() * 1000)

        row = [
            ts_ms,
            datetime.fromtimestamp(ts_ms / 1000).strftime('%H:%M:%S.%f')[:-3],
            # Raw values
            round(accel[0], 5), round(accel[1], 5), round(accel[2], 5),
            round(gyro[0],  4), round(gyro[1],  4), round(gyro[2],  4),
            round(angle[0], 2), round(angle[1], 2), round(angle[2], 2),
            # Corrected values
            round(c_accel[0], 5), round(c_accel[1], 5), round(c_accel[2], 5),
            round(c_gyro[0],  4), round(c_gyro[1],  4), round(c_gyro[2],  4),
            round(c_angle[0], 2), round(c_angle[1], 2), round(c_angle[2], 2),
            # Extras
            mag[0], mag[1], mag[2],
            round(temp, 2) if temp is not None else '',
        ]

        self._csv_writer.writerow(row)
        self._csv_file.flush()
        self._sample_count += 1

    # ── Configuration ─────────────────────────────────────────────────────

    def configure_high_speed(self):
        """200 Hz, 16g, 256 Hz bandwidth."""
        print("Configuring for high-speed logging...")
        self.device.set_update_rate(200);    time.sleep(0.15)
        self.device.set_accelerometer_range(16); time.sleep(0.15)
        self.device.set_bandwidth(256);      time.sleep(0.15)
        print("✓ Done: 200 Hz | ±16g | 256 Hz BW")

    def set_installation_direction(self, horizontal=True):
        """
        Set device installation direction.
        horizontal=True  -> flat/horizontal mount (default)
        horizontal=False -> vertical mount
        NOTE: This API only supports horizontal/vertical.
              For -Z up (upside down flat) use horizontal=True
              then apply software axis corrections (done automatically in logging).
        """
        direction = InstallationDirection.horizontal if horizontal else InstallationDirection.vertical
        self.device.set_installation_direction(direction)
        time.sleep(0.1)
        label = "horizontal" if horizontal else "vertical"
        print(f"✓ Installation direction set to: {label}")
        print("  (Axis inversion for -Z up mount is handled in software)")

    def calibrate_accel_gyro(self):
        """Accelerometer + gyroscope calibration."""
        print("\n⚠️  CALIBRATION — keep device COMPLETELY STILL!")
        print("Starting in 3 seconds...")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)
        print("Calibrating...")
        self.device.set_calibration_mode(CalibrationMode.AccelerometerGyroscopeCalibration)
        time.sleep(5)
        self.device.set_calibration_mode(CalibrationMode.None_)
        print("✓ Calibration complete!\n")

    def set_update_rate(self, rate):
        self.device.set_update_rate(rate)
        time.sleep(0.1)
        print(f"✓ Update rate: {rate} Hz")

    def set_accel_range(self, range_g):
        self.device.set_accelerometer_range(range_g)
        time.sleep(0.1)
        print(f"✓ Accel range: ±{range_g}g")

    def set_bandwidth(self, bw):
        self.device.set_bandwidth(bw)
        time.sleep(0.1)
        print(f"✓ Bandwidth: {bw} Hz")

    # ── Logging ───────────────────────────────────────────────────────────

    def start_logging(self, filename=None):
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imu_log_{ts}.csv"

        self._csv_file = open(filename, 'w', newline='')
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow([
            'timestamp_ms', 'time_hms',
            # Raw
            'raw_ax_g', 'raw_ay_g', 'raw_az_g',
            'raw_gx_dps', 'raw_gy_dps', 'raw_gz_dps',
            'raw_roll_deg', 'raw_pitch_deg', 'raw_yaw_deg',
            # Corrected (mount-adjusted)
            'accel_lat_g', 'accel_lon_g', 'accel_vert_g',
            'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps',
            'pitch_deg', 'roll_deg', 'yaw_deg',
            # Extras
            'mag_x', 'mag_y', 'mag_z',
            'temp_c',
        ])
        self._sample_count = 0
        self._log_start_time = time.time()
        self._logging = True
        print(f"✓ Logging to: {filename}")
        return filename

    def stop_logging(self):
        self._logging = False
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
        elapsed = time.time() - self._log_start_time if self._log_start_time else 0
        rate = self._sample_count / elapsed if elapsed > 0 else 0
        print(f"\n✓ Logging stopped — {self._sample_count} samples in {elapsed:.1f}s ({rate:.1f} Hz avg)")

    # ── Display ───────────────────────────────────────────────────────────

    def print_readings(self, corrected=True):
        with self._lock:
            accel = self._latest.get('accel')
            gyro  = self._latest.get('gyro')
            angle = self._latest.get('angle')
            temp  = self._latest.get('temp_c')

        if not all([accel, gyro, angle]):
            print("  Waiting for data... (if stuck, check port/baud)")
            return

        if corrected:
            c_accel, c_gyro, c_angle = remap_axes(accel, gyro, angle)
            print(f"\n{'─'*45}")
            print(f"  CORRECTED (mount-adjusted)")
            print(f"  Accel (g):  lat={c_accel[0]:+.3f}  lon={c_accel[1]:+.3f}  vert={c_accel[2]:+.3f}")
            print(f"  Gyro (°/s): X={c_gyro[0]:+.2f}  Y={c_gyro[1]:+.2f}  Z={c_gyro[2]:+.2f}")
            print(f"  Pitch={c_angle[0]:+.1f}°  Roll={c_angle[1]:+.1f}°  Yaw={c_angle[2]:+.1f}°")
            print(f"{'─'*45}")
            print(f"  RAW (from sensor)")
        print(f"  Accel (g):  X={accel[0]:+.3f}  Y={accel[1]:+.3f}  Z={accel[2]:+.3f}")
        print(f"  Gyro (°/s): X={gyro[0]:+.2f}  Y={gyro[1]:+.2f}  Z={gyro[2]:+.2f}")
        print(f"  Angle:  Roll={angle[0]:+.1f}°  Pitch={angle[1]:+.1f}°  Yaw={angle[2]:+.1f}°")
        if temp is not None:
            print(f"  Temp: {temp:.1f}°C")
        print()

    def close(self):
        if self._logging:
            self.stop_logging()
        self.device.close()


# ── Main menu ────────────────────────────────────────────────────────────────

def main():
    print("WitMotion WT901 Logger v4\n")

    port     = input("Serial port [/dev/ttyS0]: ").strip() or '/dev/ttyS0'
    baudrate = input("Baud rate   [9600]:       ").strip() or '9600'

    try:
        logger = WT901Logger(port=port, baudrate=int(baudrate))
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    while True:
        print("\n═══ WT901 Menu ═══")
        print("1. Show current readings (raw + corrected)")
        print("2. Live display (refresh every 0.5s, Ctrl+C to stop)")
        print("3. Configure high-speed (200Hz, 16g, 256Hz BW)")
        print("4. Calibrate accel/gyro (keep still!)")
        print("5. Set installation direction")
        print("6. Start CSV logging")
        print("7. Change update rate")
        print("8. Change accel range")
        print("9. Change bandwidth")
        print("0. Exit")

        choice = input("\nChoice: ").strip()

        if choice == '1':
            logger.print_readings(corrected=True)
            input("Enter to continue...")

        elif choice == '2':
            print("Live display — Ctrl+C to stop")
            try:
                while True:
                    print("\033[2J\033[H", end='')  # clear screen
                    logger.print_readings(corrected=True)
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass

        elif choice == '3':
            logger.configure_high_speed()
            input("Enter to continue...")

        elif choice == '4':
            logger.calibrate_accel_gyro()
            input("Enter to continue...")

        elif choice == '5':
            print("\nInstallation direction:")
            print("  1: Horizontal (flat mount, including upside-down flat)")
            print("  2: Vertical (standing on edge)")
            print("  Note: -Z up (upside-down) is corrected in software automatically")
            d = input("Choice [1]: ").strip() or '1'
            logger.set_installation_direction(horizontal=(d != '2'))
            input("Enter to continue...")

        elif choice == '6':
            fname = input("Filename (Enter=auto): ").strip() or None
            logger.start_logging(fname)
            print("Logging... Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
                    elapsed = time.time() - logger._log_start_time
                    print(f"  {logger._sample_count} samples | {elapsed:.0f}s | "
                          f"{logger._sample_count/elapsed:.1f} Hz", end='\r')
            except KeyboardInterrupt:
                logger.stop_logging()

        elif choice == '7':
            print("Options: 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 125, 200")
            rate = float(input("Rate (Hz): "))
            logger.set_update_rate(rate)
            input("Enter to continue...")

        elif choice == '8':
            print("Options: 2, 4, 8, 16")
            rng = int(input("Range (g): "))
            logger.set_accel_range(rng)
            input("Enter to continue...")

        elif choice == '9':
            print("Options: 5, 10, 20, 42, 98, 188, 256")
            bw = int(input("Bandwidth (Hz): "))
            logger.set_bandwidth(bw)
            input("Enter to continue...")

        elif choice == '0':
            logger.close()
            print("Bye!")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
