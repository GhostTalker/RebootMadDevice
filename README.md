# RebootMadDevice
Reboot MAD devices via ADB when device is not responding

Install:
pip install -r requirements.txt
copy config.ini.example to config.ini and adjust the values
adjust CheckMadDevicesDaemon.sh with install path

Whats new:
- timeout can now be configured in config.ini
- path for reboot script automaticly set
- next reboot of a device only after defined timeframe
- it is configurable if you use the relay in NC or NO mode

ToDo:
- Improve reboot checks with additional data from madmin status endpoint


