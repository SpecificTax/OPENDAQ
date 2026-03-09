# OPENDAQ
Racing is expensive enough. Knowing your car's dynamics should NOT be.
Raspberry Pi-based data logger that captures real vehicle dynamics for under $70. 
Freely available to EVERYONE! 🏁

What It Does:
Records high-resolution IMU data from your vehicle:

Acceleration: X, Y, Z in m/s² or G-force
Angular velocity: Pitch, roll, yaw in deg/s
Orientation tracking: Real-time vehicle attitude

Originally built to correlate lateral G-force with rotational yaw to analyze steering balance on our SAE Baja car. Turns out it's pretty handy for any vehicle dynamics work.

Why This Exists:
Professional motorsports data loggers cost thousands of dollars. This does the core job for under $70 using a Raspberry Pi and an IMU sensor. No subscription. No cloud dependency. Just raw data you own.

Hardware Requirements:

Raspberry Pi (any model with GPIO)
WitMotion IMU sensor (WT901C or similar)
MicroSD card (16GB+)
Power supply
Basic wiring supplies

Total cost: ~$50-70 (depending on Pi availability)


Hardware setup: See TECHNICAL_REFERENCE for complete build instructions


Open Source (DISCLAIMER**)
This project is 99% open source. The only proprietary component is the WitMotion Python library for sensor communication. Everything else—hardware design, wiring, configuration, analysis—is fully documented and modifiable.
Want to swap the IMU? Use a different sensor? Build your own parser? Go for it. That's the point.

Documentation:

TECHNICAL_REFERENCE.md: Complete build guide, troubleshooting, everything you need to replicate this

src/: All the code

examples/: Sample data and analysis scripts

Contributing:

Built something cool with this? Fixed a bug? Want to add support for different sensors? PRs welcome! This is for the community.

I would LOVE to see people carrying this on further.

Quick wins would be automating the flow of .log -> PARSER -> Timestamped CSV ready for analysis.

License:

MIT - Build cool stuff, Share what you learned!

SAMPLE OUTPUTS: THIS IS YOUR CHOICE ON DASHBOARDING!

<img width="1320" height="499" alt="Screenshot 2026-03-03 at 8 17 28 PM" src="https://github.com/user-attachments/assets/218c744d-afea-47a2-b65d-5d9906e7e8dc" />

<img width="2820" height="1536" alt="image" src="https://github.com/user-attachments/assets/50429bbc-ef78-4ffc-bf9e-528890bc1770" />

<img width="1374" height="692" alt="image" src="https://github.com/user-attachments/assets/86d74879-bcce-4c01-b712-7813c65bc915" />

