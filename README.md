# RebootMadDevice
Reboot MAD devices via ADB or PowerSwitch when device is not responding

only works with Python 3.6 and above
Run the installation and this scripts not with sudo. Use root user!
Running the daemon is only possible with root user!

#### Install:
```
- pip3 install -r requirements.txt
- pip3 install -r requirements_rpi.txt (only for raspberry - add support for GPIO and LED)
- copy config.ini.example to config.ini and adjust the values
- adjust CheckMadDevicesDaemon.sh with install path
- run chmod +x *.py
- run chmod +x *.sh
```

#### Using the daemon:
 

The deamon has to be started with:
```
CheckMadDevicesDaemon.sh start
```
if you want to check that is running:
```
CheckMadDevicesDaemon.sh status
```

and if you want to stop
```
CheckMadDevicesDaemon.sh stop
```



#### Whats new:
```
- add support for external status LED via websocket (https://github.com/FabLab-Luenen/McLighting)
- add support for PowerBoard (Link will follow)
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
- fixed MITM auth
```
## License
See the [LICENSE](https://github.com/GhostTalker/RebootMadDevice/blob/master/LICENSE.md) file for license rights and limitations (MIT).