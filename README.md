# RebootMadDevice V4 - Flygon API version ( under developing)
Reboot ATV devices via ADB or PowerSwitch when device is not responding to MAD or RDM.

Only works with Python 3.6 and above.

Run the installation and this scripts not with sudo. Use root user!

Running the daemon is only possible with root user!

After restarting Flygon it will take up to 5 minutes before data is usable. 

#### Install:
```
Raspberry or Server:
- pip3 install -r requirements.txt
- pip3 install -r requirements_rpi.txt (only for raspberry - add support for GPIO and LED)
- copy config.ini.example to config.ini and adjust the values
- adjust RMDdaemon.sh with install path
```

#### Using the daemon:
 
The deamon has to be started with:
```
RMDdaemon.sh start
```
if you want to check that is running:
```
RMDdaemon.sh status
```

and if you want to stop:
```
RMDdaemon.sh stop
```

#### Doing a manual reboot (e.g. for testing):
 
A manual reboot can be done with the ManualReboot.py script:
```
   ManualReboot.py -o <DEVICE_ORIGIN_TO_REBOOT>
or
   ManualReboot.py --origin <DEVICE_ORIGIN_TO_REBOOT>
```

#### ADD MAPPER RESTART SCRIPT:
 
To use the mapper restart option the config parameter TRY_RESTART_MAPPER_FIRST has to be true.
```
TRY_RESTART_MAPPER_FIRST = True
```
Next step is to add the "MAPPER_MODE" to the device.json like:
```
"MAPPER_MODE": "ATLAS"
```
Then a bash script with the commands has to be created in the folder. The name has to be:
```
restart<MAPPER_MODE_VALUE>.sh
```
It is possible to use different MAPPER_MODE on each device.


#### Features and supported hardware:
```
- Reboot every device one times within 24 hours (optional)
- Flygon support
- support for status LED with WS2812 led stripe
- support for external status LED via websocket (https://github.com/FabLab-Luenen/McLighting)
- usable with PowerBoard (Link will follow)
- usable with external commands
- usable with web api like sonoff
- usable with snmp
- usable with gpio
- relay mode NC or NO
```
#### Whats new:
```
- Restart Script for mapper software
- Add waittime for force reboots
- Add support to restart mapper software instead of reboot
- Flygon support
- based on Flygon database 
- client architecture
- timeout can be configured in config.ini
- next reboot of a device only after defined timeframe
- Discord Webhook support (without discord_webhook dependency)
- devided requirements in two parts (general and raspi)
- ADB reboot optional
- manual reboot script for testing
- IP ban check for PTC
```
## License
See the [LICENSE](https://github.com/GhostTalker/RebootMadDevice/blob/master/LICENSE.md) file for license rights and limitations (MIT).
