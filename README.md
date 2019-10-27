# RebootMadDevice
Reboot MAD devices via ADB when device is not responding

Install:
pip install -r requirements.txt
copy config.ini.example to config.ini and ajust the values
adjust CheckMadDevicesDaemon.sh with install path

Whats new:
- timeout can now be configured in config.ini
- path for reboot script automaticly set

ToDo:
- Improve reboot checks with additional data from madmin status endpoint
- next reboot of a device only after defined timeframe

