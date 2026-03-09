# OPENDAQ
Racing is expensive enough. Knowing your car's dynamics should NOT be.
Raspberry Pi-based data logger that captures real vehicle dynamics for under $70. Freely available to EVERYONE! 🏁

What It Does
Records high-resolution IMU data from your vehicle:

Acceleration: X, Y, Z in m/s² or G-force
Angular velocity: Pitch, roll, yaw in deg/s
Orientation tracking: Real-time vehicle attitude

Originally built to correlate lateral G-force with rotational yaw to analyze steering balance on our SAE Baja car. Turns out it's pretty handy for any vehicle dynamics work.

Why This Exists
Professional motorsports data loggers cost thousands of dollars. This does the core job for under $70 using a Raspberry Pi and an IMU sensor. No subscription. No cloud dependency. Just raw data you own.

Hardware Requirements

Raspberry Pi (any model with GPIO)
WitMotion IMU sensor (WT901C or similar)
MicroSD card (16GB+)
Power supply
Basic wiring supplies

Total cost: ~$50-70 (depending on Pi availability)


Quick Start

Hardware setup: See TECHNICAL_REFERENCE.md for complete build instructions


Open Source*
This project is 99% open source. The only proprietary component is the WitMotion Python library for sensor communication. Everything else—hardware design, wiring, configuration, analysis—is fully documented and modifiable.
Want to swap the IMU? Use a different sensor? Build your own parser? Go for it. That's the point.
Documentation

TECHNICAL_REFERENCE.md: Complete build guide, troubleshooting, everything you need to replicate this
src/: All the code
examples/: Sample data and analysis scripts

Contributing
Built something cool with this? Fixed a bug? Want to add support for different sensors? PRs welcome! This is for the community.
License
MIT - Build cool stuff, share what you learn.
