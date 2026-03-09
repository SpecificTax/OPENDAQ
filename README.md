# OPENDAQ
Raspberry pi based open source vehicle telemetry. Racing is expensive enough, knowing dynamics should NOT be. Freely Available to EVERYONE! :)


Core project was an attempt to read lateral g force and correlate it to processional yaw, over time / frames. This can indicate the steering balance of the vehicle.

This project records x,y,z acceleration in m/s or G, angular velocity in deg / s, can determine orientation of pitch, roll, yaw of vehicles.

TOTAL COST should be under seventy USD. PI's are becoming more expensive due to the RAM shortages and companies pivoting away from consumer products, but this unit still is greatly cheaper than any motorsports-oriented data logging..

This project is 99% open source. the ONLY non-open source feature is the log command itself. WitMotion provides a python library with API calls and a CLI debug tool that outputs the proper data. This behavior is entirely user-configurable, and I hope to see people improve my project further.
