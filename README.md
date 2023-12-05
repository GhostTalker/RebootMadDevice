# RebootMadDevice V5 - Rotom API version 
Reboot ATV devices via ADB or PowerSwitch when device is not responding to Rotom.

Only works with Python 3.6 and above.

After restarting Rotom it will take up to 2 minutes before data is usable. 

This is a complete rework of RMD. I removed several things and features which are not nessessary anymore.

### Install:
```
Raspberry or Server:
- pip3 install -r requirements.txt
- pip3 install -r requirements_rpi.txt (only for raspberry - add support for GPIO and LED)
- copy config/config.ini.example to config/config.ini and adjust the values
- adjust RMDdaemon.sh with install path
```

### Doing a manual reboot (e.g. for testing):
 
A manual reboot can be done with the ManualReboot.py script:
```
   ManualReboot.py -o <DEVICE_ORIGIN_TO_REBOOT>
or
   ManualReboot.py --origin <DEVICE_ORIGIN_TO_REBOOT>
```

### ADD MAPPER RESTART SCRIPT:
 
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


### PROMETHEUS CONFIG:
Use IP address of the device where RMD is running and PORT is configured in the config.ini
```
  - job_name: 'rmd'
    scrape_interval: 10s
    static_configs:
      - targets: ['<IP>:<Port>']
```


### Features and supported hardware:
```
- Grafana template added
- Rotom support only
- Prometheus metrics
- usable with external commands
- usable with web api like sonoff
- usable with gpio
- relay mode NC or NO
- ADB reboot optional
- timeout can be configured in config.ini
- next reboot of a device only after defined timeframe
- Discord Webhook support (without discord_webhook dependency)
- devided requirements in two parts (general and raspi)
- Add waittime for force reboots
- Add support to restart mapper software instead of reboot
- manual reboot script for testing
```
### Whats new:
```
- Rotom API support
- added Rotom API secret (will come in future release)
- Prometheus metrics
- parallize device request
```
## License
See the [LICENSE](https://github.com/GhostTalker/RebootMadDevice/blob/master/LICENSE.md) file for license rights and limitations (MIT).
