# RebootMadDevice V2 - MAD Plugin
Reboot MAD devices via ADB or PowerSwitch when device is not responding

only works with Python 3.6 and above
Run the installation and this scripts not with sudo. Use root user!
Running the daemon is only possible with root user!

#### Install:
```
MAD Server:
- Copy plugin from folder /MAD_plugin to <MAD plugin folder>/RebootMadDevice/ 
- adjust plugin.ini to your requirements

Raspberry or Server:
- pip3 install -r requirements.txt
- pip3 install -r requirements_rpi.txt (only for raspberry - add support for GPIO and LED)
- copy config.ini.example to config.ini and adjust the values
- adjust RMDclientDaemon.sh with install path
- run chmod +x *.py
- run chmod +x *.sh
```

#### Using the daemon:
 
The deamon has to be started with:
```
RMDclientDaemon.sh start
```
if you want to check that is running:
```
RMDclientDaemon.sh status
```

and if you want to stop:
```
RMDclientDaemon.sh stop
```

#### Features and supported hardware:
```
- support for status LED with WS2812 led stripe
- support for external status LED via websocket (https://github.com/FabLab-Luenen/McLighting)
- usable with PowerBoard (Link will follow)
- usable with external commands
- usable with web api like sonoff
- usable with gpio
- relay mode NC or NO
```
#### Whats new:
```
- MAD plugin 
- server client architecture
- timeout can now be configured in plugin.ini
- next reboot of a device only after defined timeframe
- Discord Webhook support
- devided requirements in two parts (general and raspi)
```
## License
See the [LICENSE](https://github.com/GhostTalker/RebootMadDevice/blob/master/LICENSE.md) file for license rights and limitations (MIT).