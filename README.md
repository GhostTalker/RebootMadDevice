# RebootMadDevice
Reboot MAD devices via ADB or PowerSwitch when device is not responding

only works with Python 3.6 and above

Install:
- pip3 install -r requirements.txt
- pip3 install -r requirements_rpi.txt (only for raspberry - add support for GPIO and LED)
- copy config.ini.example to config.ini and adjust the values
- adjust CheckMadDevicesDaemon.sh with install path

Whats new:
- devided requirements in two parts (general and raspi)
- add status LED support for WS2812 led stripe
- added Discord Webhook support
- timeout can now be configured in config.ini
- path for reboot script automaticly set
- next reboot of a device only after defined timeframe
- usable with external commands
- usable with web api like sonoff
- usable with gpio
- it is configurable if you use the relay in NC or NO mode
- fixed null values

