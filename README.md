# RebootMadDevice
Reboot MAD devices via ADB when device is not responding

only works with Python 3.6 and above

Install:
- pip3 install -r requirements.txt
- copy config.ini.example to config.ini and adjust the values
- adjust CheckMadDevicesDaemon.sh with install path

Whats new:
- timeout can now be configured in config.ini
- path for reboot script automaticly set
- next reboot of a device only after defined timeframe
- usable with external commands
- usable with web api like sonoff
- usable with gpio
- it is configurable if you use the relay in NC or NO mode
- fixed null values

