#!/usr/bin/env python3
"""
witmotion_log_parser.py  v2
Converts witmotion_raw.log (from imu_logger2.2+) into a clean merged CSV.

Log line formats understood:
    New (imu_logger2.2+):  [HH:MM:SS.mmm] INFO:witmotion.cmd.debug:<message>
    Legacy (no timestamp): INFO:witmotion.cmd.debug:<message>
    Session marker:        SESSION_START 2026-03-05T18:05:58.123456

Output CSV columns:
    timestamp_iso, time_hms,
    raw_ax_g .. raw_yaw_deg,
    accel_lat_g .. yaw_deg   (mount-corrected),
    mag_x/y/z, temp_c

Mount corrections for -Z up (upside-down flat):
    accel_lat  =  raw_ax          X lateral, OK
    accel_lon  = -raw_ay          Y longitudinal, INVERTED
    accel_vert = -raw_az          Z vertical, INVERTED
    pitch      = -(raw_roll+180)  correct 180° flip
    roll       =  raw_pitch
    yaw        =  raw_yaw

Usage:
    python3 witmotion_log_parser.py [input.log] [output.csv]
    python3 witmotion_log_parser.py              # uses witmotion_raw.log
"""

import re
import sys
import csv
import os
from datetime import datetime, date, timedelta


# ── Regex patterns ────────────────────────────────────────────────────────────

RE_TS_PREFIX   = re.compile(r'^\[(\d{2}:\d{2}:\d{2}\.\d{3})\] (.*)')
RE_SESSION     = re.compile(r'^SESSION_START (.+)')
RE_INFO        = re.compile(r'^INFO:witmotion\.cmd\.debug:(.*)')

RE_ACCEL = re.compile(
    r'acceleration message - vec:\(([^,]+),\s*([^,]+),\s*([^)]+)\)\s+temp_celsius:([\d.]+)'
)
RE_GYRO = re.compile(
    r'angular velocity message - w:\(([^,]+),\s*([^,]+),\s*([^)]+)\)\s+temp_celsius:([\d.]+)'
)
RE_ANGLE = re.compile(
    r'angle message - roll:([-\d.]+)\s+pitch:([-\d.]+)\s+yaw:([-\d.]+)'
)
RE_MAG = re.compile(
    r'magnetic message - vec:\(([^,]+),\s*([^,]+),\s*([^)]+)\)\s+temp_celsius:([\d.]+)'
)


# ── Axis corrections ──────────────────────────────────────────────────────────

def apply_corrections(accel, gyro, angle):
    """Correct for -Z up (upside-down flat) mount."""
    ax, ay, az = accel
    gx, gy, gz = gyro
    roll_raw, pitch_raw, yaw_raw = angle
    return (
        ( ax, -ay, -az),
        ( gx, -gy,  gz),
        (-(roll_raw + 180.0), pitch_raw, yaw_raw),
    )


# ── Timestamp helpers ─────────────────────────────────────────────────────────

def resolve_timestamp(hms_str, session_date, prev_dt):
    """
    Convert HH:MM:SS.mmm string to a full datetime.
    Handles midnight rollover.
    session_date: date object for the session (from SESSION_START or today)
    prev_dt:      previous datetime (to detect rollover)
    """
    h, m, s_ms = hms_str.split(':')
    s, ms = s_ms.split('.')
    dt = datetime(session_date.year, session_date.month, session_date.day,
                  int(h), int(m), int(s), int(ms) * 1000)
    # Handle midnight rollover
    if prev_dt and dt < prev_dt:
        dt += timedelta(days=1)
    return dt


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_log(filepath):
    """
    Parse log into list of complete frame dicts.
    Each frame: {ts: datetime, accel, gyro, angle, mag, temp_c}
    """
    frames = []
    current = {}
    session_date = date.today()
    session_start_dt = None
    prev_dt = None
    frame_ts = None          # timestamp of the current accel line (frame anchor)
    legacy_frame_counter = 0

    with open(filepath, 'r') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # Session start marker
            m = RE_SESSION.match(line)
            if m:
                try:
                    session_start_dt = datetime.fromisoformat(m.group(1))
                    session_date = session_start_dt.date()
                    prev_dt = session_start_dt
                except ValueError:
                    pass
                continue

            # Try to strip timestamp prefix
            ts_dt = None
            m_ts = RE_TS_PREFIX.match(line)
            if m_ts:
                try:
                    ts_dt = resolve_timestamp(m_ts.group(1), session_date, prev_dt)
                    prev_dt = ts_dt
                except Exception:
                    pass
                content_line = m_ts.group(2)
            else:
                content_line = line
                legacy_frame_counter += 1

            # Only parse INFO lines to avoid duplicate DEBUG lines
            m_info = RE_INFO.match(content_line)
            if not m_info:
                continue
            content = m_info.group(1)

            # Match message types
            if m_a := RE_ACCEL.search(content):
                if 'accel' in current:
                    frames.append(current)
                current = {
                    'ts': ts_dt,
                    'accel': (float(m_a.group(1)), float(m_a.group(2)), float(m_a.group(3))),
                    'temp_c': float(m_a.group(4)),
                }

            elif m_g := RE_GYRO.search(content):
                current['gyro'] = (float(m_g.group(1)), float(m_g.group(2)), float(m_g.group(3)))
                if ts_dt and 'ts' not in current:
                    current['ts'] = ts_dt

            elif m_an := RE_ANGLE.search(content):
                current['angle'] = (float(m_an.group(1)), float(m_an.group(2)), float(m_an.group(3)))

            elif m_m := RE_MAG.search(content):
                current['mag'] = (int(m_m.group(1)), int(m_m.group(2)), int(m_m.group(3)))

    if 'accel' in current:
        frames.append(current)

    return frames, legacy_frame_counter > 0


# ── CSV writer ────────────────────────────────────────────────────────────────

HEADERS = [
    'frame', 'timestamp_iso', 'time_hms',
    'raw_ax_g', 'raw_ay_g', 'raw_az_g',
    'raw_gx_dps', 'raw_gy_dps', 'raw_gz_dps',
    'raw_roll_deg', 'raw_pitch_deg', 'raw_yaw_deg',
    'accel_lat_g', 'accel_lon_g', 'accel_vert_g',
    'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps',
    'pitch_deg', 'roll_deg', 'yaw_deg',
    'mag_x', 'mag_y', 'mag_z',
    'temp_c',
]

def write_csv(frames, out_path):
    complete = 0
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)

        for i, fr in enumerate(frames):
            accel = fr.get('accel', (None, None, None))
            gyro  = fr.get('gyro',  (None, None, None))
            angle = fr.get('angle', (None, None, None))
            mag   = fr.get('mag',   ('', '', ''))
            temp  = fr.get('temp_c', '')
            ts    = fr.get('ts')

            ts_iso = ts.isoformat() if ts else ''
            ts_hms = ts.strftime('%H:%M:%S.%f')[:-3] if ts else ''

            if None in accel or None in gyro or None in angle:
                writer.writerow([i, ts_iso, ts_hms,
                    *[round(v,5) if v else '' for v in accel],
                    *[round(v,4) if v else '' for v in gyro],
                    *[round(v,2) if v else '' for v in angle],
                    *[''] * 9,
                    *mag,
                    round(temp,2) if temp else ''])
                continue

            ca, cg, can = apply_corrections(accel, gyro, angle)
            writer.writerow([
                i, ts_iso, ts_hms,
                round(accel[0],5), round(accel[1],5), round(accel[2],5),
                round(gyro[0], 4), round(gyro[1], 4), round(gyro[2], 4),
                round(angle[0],2), round(angle[1],2), round(angle[2],2),
                round(ca[0],5),  round(ca[1],5),  round(ca[2],5),
                round(cg[0],4),  round(cg[1],4),  round(cg[2],4),
                round(can[0],2), round(can[1],2), round(can[2],2),
                *mag,
                round(temp,2) if temp else '',
            ])
            complete += 1

    return complete


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(frames, source_file, has_legacy):
    total    = len(frames)
    complete = sum(1 for f in frames if all(k in f for k in ('accel','gyro','angle')))
    timestamped = sum(1 for f in frames if f.get('ts'))

    accels = [f['accel'] for f in frames if 'accel' in f]
    gyros  = [f['gyro']  for f in frames if 'gyro'  in f]
    angles = [f['angle'] for f in frames if 'angle' in f]
    temps  = [f['temp_c'] for f in frames if 'temp_c' in f]

    # Duration
    timed = [f['ts'] for f in frames if f.get('ts')]
    duration_str = ''
    rate_str     = ''
    if len(timed) >= 2:
        dur = (timed[-1] - timed[0]).total_seconds()
        duration_str = f"{dur:.1f}s"
        rate_str     = f"{len(timed)/dur:.2f} Hz" if dur > 0 else '?'

    def stats(vals, idx):
        col = [v[idx] for v in vals]
        return min(col), max(col), sum(col)/len(col)

    W = 55
    print(f"\n{'═'*W}")
    print(f"  LOG SUMMARY: {os.path.basename(source_file)}")
    print(f"{'═'*W}")
    print(f"  Frames total   : {total}")
    print(f"  Complete frames: {complete}  ({100*complete/total:.1f}%)")
    print(f"  Timestamped    : {timestamped}" +
          (" (legacy log — no per-frame timestamps)" if has_legacy else ""))
    if duration_str:
        print(f"  Duration       : {duration_str}  @ {rate_str}")
    print()

    if accels:
        print("  ACCELEROMETER (g)  [raw]")
        for i, lbl in enumerate(['X lateral', 'Y longitudinal', 'Z vertical']):
            mn, mx, avg = stats(accels, i)
            print(f"    {lbl:16s}  min={mn:+.3f}  max={mx:+.3f}  avg={avg:+.3f}")
    print()

    if gyros:
        print("  GYROSCOPE (°/s)  [raw]")
        for i, lbl in enumerate(['X', 'Y', 'Z']):
            mn, mx, avg = stats(gyros, i)
            print(f"    {lbl:16s}  min={mn:+.2f}  max={mx:+.2f}  avg={avg:+.2f}")
    print()

    if angles:
        print("  ANGLES (°)  [corrected for -Z up mount]")
        c_angles = [apply_corrections((0,0,0),(0,0,0), f['angle'])[2]
                    for f in frames if 'angle' in f]
        for i, lbl in enumerate(['Pitch (vehicle)', 'Roll (vehicle)', 'Yaw (heading)']):
            col = [a[i] for a in c_angles]
            print(f"    {lbl:16s}  min={min(col):+.1f}  max={max(col):+.1f}  avg={sum(col)/len(col):+.1f}")
    print()

    if temps:
        print(f"  TEMPERATURE (°C)   min={min(temps):.1f}  max={max(temps):.1f}  avg={sum(temps)/len(temps):.1f}")

    print(f"{'═'*W}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    in_file  = sys.argv[1] if len(sys.argv) > 1 else 'witmotion_raw.log'
    ts_tag   = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = sys.argv[2] if len(sys.argv) > 2 else \
               os.path.splitext(in_file)[0] + f'_parsed_{ts_tag}.csv'

    if not os.path.exists(in_file):
        print(f"ERROR: File not found: {in_file}")
        sys.exit(1)

    print(f"Parsing: {in_file}")
    frames, has_legacy = parse_log(in_file)

    if not frames:
        print("ERROR: No frames found. Check log format.")
        sys.exit(1)

    if has_legacy:
        print("  ⚠  Legacy log detected (no per-frame timestamps).")
        print("     Upgrade to imu_logger2.2 for timestamped logs.")

    print_summary(frames, in_file, has_legacy)
    complete = write_csv(frames, out_file)
    print(f"✓ CSV written : {out_file}")
    print(f"  {complete}/{len(frames)} complete frames\n")


if __name__ == "__main__":
    main()
