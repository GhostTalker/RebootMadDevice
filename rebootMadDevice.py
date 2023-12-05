#!/usr/bin/env /bin/python3
#
# RebootMadDevices
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "5.0.2"
__status__ = "TEST"

# generic/built-in and other libs
import os
import sys
import time
import datetime
import json
import requests
import configparser
import subprocess
import logging
import logging.handlers
from threading import Thread
import prometheus_client


## read config
_config = configparser.ConfigParser()
_rootdir = os.path.dirname(os.path.abspath('rebootMadDevice.py'))
_config.read(_rootdir + '/config/config.ini')
_device_config = (_rootdir + '/config/devices.json')
_adb_path = _config.get("ENVIROMENT", "ADB_PATH", fallback='/usr/bin')
_adb_port = _config.get("ENVIROMENT", "ADB_PORT", fallback='5555')
_log_mode = _config.get("LOGGING", "LOG_MODE", fallback='console')
_log_level = _config.get("LOGGING", "LOG_LEVEL", fallback='INFO')
_log_filename = _config.get("LOGGING", "LOG_FILENAME", fallback='RMDClient.log')
_api_rotom_secret = _config.get("ROTOMAPI", "API_ROTOM_SECRET", fallback=None)
_api_endpoint_status = _config.get("ROTOMAPI", "API_ENDPOINT_STATUS")
_prometheus_enable = _config.getboolean("PROMETHEUS", "PROMETHEUS_ENABLE", fallback=False)
_prometheus_port = _config.get("PROMETHEUS", "PROMETHEUS_PORT", fallback=8000)
_prometheus_device_location = _config.get("PROMETHEUS", "PROMETHEUS_DEVICE_LOCATION", fallback="")
_try_adb_first = _config.get("REBOOTOPTIONS", "TRY_ADB_FIRST")
_try_restart_mapper_first = _config.get("REBOOTOPTIONS", "TRY_RESTART_MAPPER_FIRST", fallback='False')
_sleeptime_between_check = _config.get("REBOOTOPTIONS", "SLEEPTIME_BETWEEN_CHECK", fallback=5)
_proto_timeout = _config.get("REBOOTOPTIONS", "PROTO_TIMEOUT", fallback=300)
_force_reboot_timeout = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_TIMEOUT", fallback=1800)
_force_reboot_waittime = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_WAITTIME", fallback=3600)
_reboot_waittime = _config.get("REBOOTOPTIONS", "REBOOT_WAITTIME", fallback=300)
_off_on_sleep = _config.get("REBOOTOPTIONS", "OFF_ON_SLEEP", fallback=5)
_max_poe_reboot = _config.get("REBOOTOPTIONS", "MAX_POE_REBOOT", fallback=10)
_discord_webhook_enable = _config.getboolean("DISCORD", "WEBHOOK", fallback=False)
_discord_webhook_url = _config.get("DISCORD", "WEBHOOK_URL", fallback='')
_gpio_usage = _config.get("GPIO", "GPIO_USAGE", fallback=False)


def makeTimestamp():
    return convert_to_milliseconds(int(time.time()))


def convert_to_seconds(milliseconds_timestamp):
    return milliseconds_timestamp / 1000.0


def convert_to_milliseconds(seconds_timestamp):
    return int(seconds_timestamp * 1000)


def calc_past_sec_from_now(timestamp):
    """ calculate time between now and given timestamp in seconds """
    if not timestamp:
        return 99999
    elif int(timestamp) > makeTimestamp():
        return 0
    diffToNow = convert_to_seconds(makeTimestamp()) - convert_to_seconds(int(timestamp))
    return diffToNow	


def timestamp_to_readable_datetime(mstimestamp):
    try:
        """ make timestamp human readable """
        timestamp = datetime.datetime.fromtimestamp(convert_to_seconds(mstimestamp))
    except:
        """ prevent error while having wrong timestamp """
        timestamp = datetime.datetime.fromtimestamp(convert_to_seconds(makeTimestamp()))            
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")
		

def printTable(myDict, colList=None):
   """ Pretty print a list of dictionaries (myDict) as a dynamically sized table.
   If column names (colList) aren't specified, they will show in random order.
   Author: Thierry Husson - Use it as you want but don't blame me.
   """
   if not colList: colList = list(myDict[0].keys() if myDict else [])
   myList = [colList] # 1st row = header
   for item in myDict: myList.append([str(item[col] if item[col] is not None else '') for col in colList])
   colSize = [max(map(len,col)) for col in zip(*myList)]
   formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
   myList.insert(1, ['-' * i for i in colSize]) # Seperating line
   for item in myList: logging.info(formatStr.format(*item))


def initRMDdata():
    # init device dict 
    rmd_data = {}
    
    # read device json file
    logging.debug(f'Read data from devices.json file.')
    with open(_device_config) as json_file:
       _jsondata = json.load(json_file) 
    
    # init rmd data in dict
    logging.debug(f'Init device data dictionary.')
    for device in _jsondata:
        rmd_data[device]= {'ip_address': _jsondata[device]["IP_ADDRESS"],
                           'mapper_mode': _jsondata[device]["MAPPER_MODE"],
                           'switch_mode': _jsondata[device]["SWITCH_MODE"],
                           'switch_option': _jsondata[device]["SWITCH_OPTION"],
                           'switch_value': _jsondata[device]["SWITCH_VALUE"],
                           'led_position': _jsondata[device]["LED_POSITION"],
                           'device_location': _prometheus_device_location,
						   'status': 0,
                           'last_seen': None,
                           'last_reboot_time': 1672531200000,
                           'reboot_count': 0,
                           'reboot_force': False,
                           'reboot_type': None,
                           'reboot_forced': False,
                           'last_reboot_forced_time': 1672531200000,
                           'webhook_id': 0								
    					}

    return rmd_data


def getDeviceStatusData():
    logging.info(f'Update device status data from API...')
    method = "get"
    url = _api_endpoint_status
    auth = None
    headers = {
       'Accept': 'application/json',
       'X-Rotom-Secret': _api_rotom_secret
    }

    while True:
        # Get device data from rotom api
        try:
            logging.debug("Get device data from rotom api")
            response = requests.request(method, url, headers=headers, auth=auth)
            deviceStatusData = response.json()
            return deviceStatusData  # return inside the try block
    
        except:
            logging.error(f'Get device data from rotom api failed.')
            logging.error(f'sleep 30s and retry')
            time.sleep(30)  # if request fails, sleep and then retry


def check_device(device_origin, deviceStatusData):
    # Update data from deviceStatusData in _rmd_data set
    if any(device['origin'] == device_origin for device in deviceStatusData['devices']):
        device_data = next(device for device in deviceStatusData['devices'] if device['origin'] == device_origin)
        _rmd_data[device_origin]['last_seen'] = device_data['dateLastMessageReceived']

    # Analyze DATA of device
    logging.debug("Checking device {} for nessessary reboot.".format(device_origin))
    if calc_past_sec_from_now(_rmd_data[device_origin]['last_seen']) > int(_proto_timeout):
        if _rmd_data[device_origin]['last_reboot_time'] is not None and calc_past_sec_from_now(_rmd_data[device_origin]['last_reboot_time']) < (int(_reboot_waittime)):
            _rmd_data[device_origin]['status'] = 1
        else:						
            _rmd_data[device_origin]['status'] = 2
            if calc_past_sec_from_now(_rmd_data[device_origin]['last_seen']) > int(_force_reboot_timeout): 
                _rmd_data[device_origin]['reboot_force'] = True
    
    else:
        _rmd_data[device_origin].update({
            'reboot_force': False,
            'reboot_count': 0,
            'reboot_type': None,
            'status': 0
        })
    
        # clear webhook_id after fixed message
        if _rmd_data[device_origin]['webhook_id'] != 0:
            discord_message(device_origin, fixed=True)
            _rmd_data[device_origin]['webhook_id'] = 0		


def check_devices():
        # API-call for device status
        deviceStatusData = getDeviceStatusData()

        try:    
            threads = []
            for device in _rmd_data:
                thread = Thread(target=check_device, args=(device, deviceStatusData))
                thread.start()
                threads.append(thread)
        
            for thread in threads:
                thread.join()
        except:
            logging.error(f'Error checking clients. Threads failed.')


def check_rebooted_devices():
    rebootedDevicedList = []
    logging.debug("Find rebooted devices for information and update discord message.")	
    logging.info("")
    logging.info("---------------------------------------------")
    logging.info("Devices are rebooted. Waiting to come online:")	
    logging.info("---------------------------------------------")
    logging.info("")

    for device in list(_rmd_data):
        if _rmd_data[device]['status'] == 1: 
            rebootedDevicedList.append({'device': device, 'last_seen': timestamp_to_readable_datetime(_rmd_data[device]['last_seen']), 'offline_minutes': round(calc_past_sec_from_now(_rmd_data[device]['last_seen'])/60), 'count': _rmd_data[device]['reboot_count'], 'last_reboot_time': timestamp_to_readable_datetime(_rmd_data[device]['last_reboot_time']), 'reboot_ago_min': round(calc_past_sec_from_now(_rmd_data[device]['last_reboot_time'])/60), 'type': _rmd_data[device]['reboot_type']})

            # Update no_data time and existing Discord messages
            if _rmd_data[device]['webhook_id'] != 0:
                logging.info('Update Discord message')
                discord_message(device)

    if not rebootedDevicedList:
        printTable([{'device': '-','last_seen': '-','offline_minutes': '-','count': '-','last_reboot_time': '-','reboot_ago_min': '-','type': '-'}], ['device','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
        logging.info("")
    else:
        printTable(rebootedDevicedList, ['device','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
        logging.info("")
			

def reboot_bad_devices():

    ##checking for bad devices
    badDevicedList = []
    logging.debug(f'Find bad devices and reboot them.')	
    logging.info(f'')
    logging.info(f'---------------------------------------------')
    logging.info(f'Devices for reboot:')	
    logging.info(f'---------------------------------------------')
    logging.info(f'')

    for device in list(_rmd_data):
        if _rmd_data[device]['status'] == 2:
            badDevicedList.append({'device': device, 'last_seen': timestamp_to_readable_datetime(_rmd_data[device]['last_seen']), 'offline_minutes': round(calc_past_sec_from_now(_rmd_data[device]['last_seen'])/60), 'count': _rmd_data[device]['reboot_count'], 'force': _rmd_data[device]['reboot_force']})

    if not badDevicedList:
        printTable([{'device': '-','last_seen': '-','offline_minutes': '-','count': '-','reboot_nessessary': '-', 'force': '-'}], ['device','last_seen','offline_minutes','count','force'])
        logging.info("")
    else:
        printTable(badDevicedList, ['device','last_seen','offline_minutes','count','force'])
        logging.info("")

    ## reboot in threads
    reboot_threads = []

    for badDevice in badDevicedList:
        reboot_thread = Thread(target=doRebootDevice, args=(badDevice["device"],))
        reboot_thread.start()
        reboot_threads.append(reboot_thread)

    for reboot_thread in reboot_threads:
        reboot_thread.join()


def doRebootDevice(DEVICE_ORIGIN_TO_REBOOT):
    # Create discord message
    if _discord_webhook_enable:
        discord_message(DEVICE_ORIGIN_TO_REBOOT)

    logging.info("Origin to reboot is: {}".format(DEVICE_ORIGIN_TO_REBOOT))
    logging.info("Force option is: {}".format(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force']))
    logging.debug("Rebootcount is: {}".format(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count']))

    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] += 1
    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_time'] = makeTimestamp()

    if _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force'] and calc_past_sec_from_now(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_forced_time']) > int(_force_reboot_waittime):
        _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_forced_time'] = makeTimestamp()
        reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        return

    try_counter = 2

    for _ in range(try_counter):
        if _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'] in list_adb_connected_devices():
            logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))

            if eval(_try_restart_mapper_first):
                logging.info("Try to restart {} on Device {}".format(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'], DEVICE_ORIGIN_TO_REBOOT))
                return_code = restart_mapper_sw(DEVICE_ORIGIN_TO_REBOOT)
                if return_code == 0:
                    logging.info("Restart Mapper on Device {} was successful.".format(DEVICE_ORIGIN_TO_REBOOT))
                    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "MAPPER"
                    return
                else:
                    logging.info("Execute of restart Mapper on Device {} was not successful. Try rebooting the device now.".format(DEVICE_ORIGIN_TO_REBOOT))

            if eval(_try_adb_first):
                logging.info("Try to reboot Device {} via ADB. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
                return_code = adb_reboot(DEVICE_ORIGIN_TO_REBOOT)

                if return_code == 0:
                    logging.info("Reboot via ADB of Device {} was successful.".format(DEVICE_ORIGIN_TO_REBOOT))
                    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "ADB"
                    return
                else:
                    logging.warning("Rebooting Device {} via ADB was not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
                    reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
                    break
        else:
            logging.debug("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
            connect_device(DEVICE_ORIGIN_TO_REBOOT)

    else:
        reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        return


def list_adb_connected_devices():
    cmd = "{}/adb devices | /bin/grep {}".format(_adb_path, _adb_port)
    try:
        connectedDevices = subprocess.check_output([cmd], shell=True)
        connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
            "\\n", ",").replace("\\tdevice", "").split(",")
    except subprocess.CalledProcessError:
        connectedDevices = ()
    return connectedDevices


def connect_device(DEVICE_ORIGIN_TO_REBOOT):
    cmd = "{}/adb connect {}".format(_adb_path, _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'])
    try:
        subprocess.check_output([cmd], shell=True)
    except subprocess.CalledProcessError:
        logging.info("Connection via adb failed")
    # Wait for 2 seconds
    time.sleep(2)


def restart_mapper_sw(DEVICE_ORIGIN_TO_REBOOT):
    _adbloc = "{}/adb".format(_adb_path)
    _deviceloc = "{}:{}".format(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], _adb_port)
    _mapperscript = "{}/mapperscripts/restart{}.sh".format(_rootdir, _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'])
    try:
        subprocess.Popen([_mapperscript, _adbloc, _deviceloc])
        return 0
    except:
        return 1
	 

def adb_reboot(DEVICE_ORIGIN_TO_REBOOT):
    _adbloc = "{}/adb".format(_adb_path)
    _deviceloc = "{}:{}".format(_rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], _adb_port)
    try:
        subprocess.Popen([_adbloc, '-s', _deviceloc, 'reboot'])
        return 0
    except:
        return 1
	

def reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT):
    ## read powerSwitch config
    powerSwitchMode = _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_mode']
    powerSwitchOption = _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_option']
    powerSwitchValue = _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_value']

    ## setting data for webhook
    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
    _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = powerSwitchMode

    ## HTML 
    if powerSwitchMode == 'HTML':
        logging.debug("PowerSwitch with HTML starting.")
        poweron = powerSwitchValue.split(";")[0]
        poweroff = powerSwitchValue.split(";")[1]
        logging.info("turn HTTP PowerSwitch off")
        requests.get(poweroff)
        time.sleep(int(_off_on_sleep))
        logging.info("turn HTTP PowerSwitch on")
        requests.get(poweron)
        logging.debug("PowerSwitch with HTML done.")
        return        

    ## GPIO 
    elif powerSwitchMode == 'GPIO':
        logging.debug("PowerSwitch with GPIO starting.")
        relay_mode = powerSwitchOption.split(";")[0]
        cleanup_mode = powerSwitchOption.split(";")[1]
        gpionr = int(powerSwitchValue)
        logging.info("turn GPIO PowerSwitch off")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        try:
           eval(cleanup_mode)
        except:
           cleanup_mode = "False"
        
        if eval(cleanup_mode):
            GPIO.cleanup()
            logging.info("GPIO cleanup done!")

        if relay_mode == 'NO':
            logging.debug("Relay_mode: " + relay_mode)
            # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.HIGH)
            logging.debug("setting GPIO setup to: GPIO.OUT")
            GPIO.setup(gpionr, GPIO.OUT)
            logging.debug("setting GPIO output to: GPIO.HIGH")
            GPIO.output(gpionr, GPIO.HIGH)
        elif relay_mode == 'NC':
            logging.debug("Relay_mode: " + relay_mode)
            # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.LOW)
            logging.debug("setting GPIO setup to: GPIO.OUT")
            GPIO.setup(gpionr, GPIO.OUT)
            logging.debug("setting GPIO output to: GPIO.LOW")
            GPIO.output(gpionr, GPIO.LOW)
        else:
            logging.error("wrong relay_mode in config")
        logging.debug("sleeping 10s")
        time.sleep(int(_off_on_sleep))
        logging.info("turn GPIO PowerSwitch on")
        if relay_mode == 'NO':
            logging.debug("Relay_mode: " + relay_mode)
            # GPIO.output(gpionr, GPIO.LOW)
            logging.debug("setting GPIO setup to: GPIO.OUT")
            GPIO.setup(gpionr, GPIO.OUT)
            logging.debug("setting GPIO output to: GPIO.LOW")
            GPIO.output(gpionr, GPIO.LOW)
        elif relay_mode == 'NC':
            logging.debug("Relay_mode: " + relay_mode)
            # GPIO.output(gpionr, GPIO.HIGH)
            logging.debug("setting GPIO setup to: GPIO.OUT")
            GPIO.setup(gpionr, GPIO.OUT)
            logging.debug("setting GPIO output to: GPIO.HIGH")
            GPIO.output(gpionr, GPIO.HIGH)
        else:
            logging.error("wrong relay_mode in config")

        if eval(cleanup_mode):
            GPIO.cleanup()
            logging.info("GPIO cleanup done!")
        logging.debug("PowerSwitch with GPIO done.")
        return

    ## CMD 
    elif powerSwitchMode == 'CMD':
        logging.debug("PowerSwitch with CMD starting.")
        try:
            subprocess.check_output(powerSwitchValue, shell=True)
        except subprocess.CalledProcessError:
            logging.error("failed to fire command")
        logging.debug("PowerSwitch with CMD done.")
        _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
        _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "CMD"
        return

    ## SCRIPT 
    elif powerSwitchMode == 'SCRIPT':
        logging.debug("PowerSwitch with SCRIPT starting.")
        poweron = powerSwitchValue.split(";")[0]
        poweroff = powerSwitchValue.split(";")[1]
        logging.info("execute script for PowerSwitch off")
        try:
            subprocess.check_output(poweroff, shell=True)
        except subprocess.CalledProcessError:
            logging.error("failed to start script")
        time.sleep(int(_off_on_sleep))
        logging.info("execute script for PowerSwitch on")
        try:
            subprocess.check_output(poweron, shell=True)
        except subprocess.CalledProcessError:
            logging.error("failed to start script")
        logging.debug("PowerSwitch with SCRIPT done.")
        return

    ## POE 
    elif powerSwitchMode == 'POE':
        logging.debug("PowerSwitch with POE starting.")
        if powerSwitchOption == 'SWITCHOFF':
            if _rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] > _max_poe_reboot:
                logging.info("Too many reboots via POE. Deactivate POE port on switch.")
                try:
                    switchportoff = powerSwitchValue.split(";")[0]
                    subprocess.check_output(switchportoff, shell=True)
                    return;
                except subprocess.CalledProcessError:
                    logging.error("failed to deaktivate poe port")
        try:
            subprocess.check_output(powerSwitchValue, shell=True)
        except subprocess.CalledProcessError:
            logging.error("failed to fire poe port reset")
        logging.debug("PowerSwitch with POE done.")
        return

    else:
        logging.warning("no PowerSwitch configured. Do it manually!!!")
			
			
def init_rmd_info():
    # Prometheus metric for build and running info
    rmd_version_info = prometheus_client.Info('rmd_build_version', 'Description of info')
    rmd_version_info.info({'version': __version__, 'status': __status__, 'started': timestamp_to_readable_datetime(makeTimestamp())})
    rmd_script_running_info = prometheus_client.Gauge('rmd_script_cycle_info', 'Actual cycle of the running script')
    rmd_script_running_info.set(0)
	
    # Prometheus metric for device config
    rmd_metric_device_info = prometheus_client.Gauge('rmd_metric_device_info', 'Device infos from config', ['device', 'device_location', 'mapper_mode', 'ip_address', 'switch_mode', 'led_position']) 
    for device, data in _rmd_data.items():
        rmd_metric_device_info.labels(device, data['device_location'], data['mapper_mode'], data['ip_address'], data['switch_mode'], data['led_position']).set(1)

    #Prometheus metric for device
    rmd_metric_device_last_seen = prometheus_client.Gauge('rmd_metric_device_last_seen', 'Device last seen', ['device'])
    rmd_metric_device_status = prometheus_client.Gauge('rmd_metric_device_status', 'Device status', ['device'])
    rmd_metric_device_last_reboot_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_time', 'Device last reboot time', ['device'])
    rmd_metric_device_reboot_count = prometheus_client.Gauge('rmd_metric_device_reboot_count', 'Device reboot count', ['device'])
    rmd_metric_device_reboot_force = prometheus_client.Gauge('rmd_metric_device_reboot_force', 'Device need reboot force', ['device'])
    rmd_metric_device_last_reboot_forced_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_forced_time', 'Device last reboot force time', ['device'])
    rmd_metric_device_webhook_id = prometheus_client.Gauge('rmd_metric_device_webhook_id', 'Actual status discord webhook id', ['device'])

     # Return a dictionary containing the metrics
    return {
        'rmd_version_info': rmd_version_info,
        'rmd_script_running_info': rmd_script_running_info,
        'rmd_metric_device_info': rmd_metric_device_info,
        'rmd_metric_device_last_seen': rmd_metric_device_last_seen,
        'rmd_metric_device_status': rmd_metric_device_status,
        'rmd_metric_device_last_reboot_time': rmd_metric_device_last_reboot_time,
        'rmd_metric_device_reboot_count': rmd_metric_device_reboot_count,
        'rmd_metric_device_reboot_force': rmd_metric_device_reboot_force,
        'rmd_metric_device_last_reboot_forced_time': rmd_metric_device_last_reboot_forced_time,
        'rmd_metric_device_webhook_id': rmd_metric_device_webhook_id,
    } 


def set_metric_values(device, metric, value):
    try:
        # Convert None, False, and True to numbers
        if value is None:
            value=0
        elif value is True:
            value=1
        elif value is False:
            value=0

        metric.labels(device).set(value)

    except Exception as e:
        logging.error(f"Error setting Prometheus metric for device {device}: {e}")


def set_device_metrics(device, data, metrics):
    metrics_mapping = {
        'rmd_metric_device_last_seen': 'last_seen',
        'rmd_metric_device_status': 'status',
        'rmd_metric_device_last_reboot_time': 'last_reboot_time',
        'rmd_metric_device_reboot_count': 'reboot_count',
        'rmd_metric_device_reboot_force': 'reboot_force',
        'rmd_metric_device_last_reboot_forced_time': 'last_reboot_forced_time',
        'rmd_metric_device_webhook_id': 'webhook_id',
    }

    for metric_name, data_key in metrics_mapping.items():
        metric = metrics[metric_name]
        value = data[data_key]
        set_metric_values(device, metric, value)


def create_prometheus_metrics(metrics):
    logging.info('Creating metrics for Prometheus...')
    metrics['rmd_script_running_info'].inc()
    for device, data in _rmd_data.items():
        set_device_metrics(device, data, metrics)
			

def discord_message(device_origin, fixed=False):
    if not _discord_webhook_enable:
        return

    # create data for webhook
    logging.info('Start Webhook for device ' + device_origin )

    data = {
      "content": "",
      "username": "Alert!",
      "avatar_url": "https://github.com/GhostTalker/icons/blob/main/rmd/messagebox_critical_256.png?raw=true",
      "embeds": [
        {
          "title": "Device restarted!", 
          "color": 16711680,
          "author": {
            "name": "RebootMadDevice",
            "url": "https://github.com/GhostTalker/RebootMadDevice",
            "icon_url": "https://github.com/GhostTalker/icons/blob/main/Ghost/GhostTalker.jpg?raw=true"
          },
           "thumbnail": {
               "url": "https://github.com/GhostTalker/icons/blob/main/rmd/reboot.jpg?raw=true"
           },
           "fields": [
            {
              "name": "Device",
              "value": device_origin,
              "inline": "true"
            },
            {
              "name": "Reboot",
              "value": _rmd_data[device_origin]['reboot_type'],
              "inline": "true"
            },
            {
              "name": "Force",
              "value": _rmd_data[device_origin]['reboot_forced'],
              "inline": "true"
            }
          ]
        }
      ]
    }
    # add timestamp
    data["embeds"][0]["timestamp"] = str(datetime.datetime.utcnow())

    # send webhook
    logging.debug(f'data to send with webhook:')
    logging.debug(data)
    logging.debug(_rmd_data[device_origin]['webhook_id'])

    if _rmd_data[device_origin]['webhook_id'] == 0:
        data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{calc_past_sec_from_now(_rmd_data[device_origin]['last_seen'])*60}` minutes!\nReboot count: `{_rmd_data[device_origin]['reboot_count']}`"
        try:
            result = requests.post(_discord_webhook_url, json = data, params={"wait": True})
            result.raise_for_status()
            answer = result.json()
            logging.debug(answer)
            _rmd_data[device_origin]["webhook_id"] = answer["id"]
            logging.debug(_rmd_data[device_origin]["webhook_id"])
        except requests.exceptions.RequestException as err:
            logging.error(err)
    else:
        logging.debug('parameter fixed is: ' + str(fixed))
        if not fixed:
            data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{calc_past_sec_from_now(_rmd_data[device_origin]['last_seen'])*60}` minutes!\nReboot count: `{_rmd_data[device_origin]['reboot_count']}`\nFixed :x:"
        else:
            data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{calc_past_sec_from_now(_rmd_data[device_origin]['last_seen'])*60}` minutes!\nReboot count: `{_rmd_data[device_origin]['reboot_count']}`\nFixed :white_check_mark:"

        try:
            result = requests.patch(_discord_webhook_url + "/messages/" + str(_rmd_data[device_origin]["webhook_id"]), json = data)
            result.raise_for_status()
        except requests.exceptions.RequestException as err:
            logging.error(err)

    return result.status_code


## Logging handler
if _log_mode == "console":
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',level=logging.getLevelName(_log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)
elif _log_mode == "file":
    logging.basicConfig(filename=_log_filename, filemode='a', format='%(asctime)s %(levelname)-8s %(message)s',level=logging.getLevelName(_log_level))
    logger = logging.getLogger(__name__)
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=3)
    logger.addHandler(file_handler)


try:
    # init RMD data
    _rmd_data = initRMDdata()

    # GPIO import libs
    if eval(_gpio_usage):
        logging.debug("import GPIO libs")
        import RPi.GPIO as GPIO
	
    # Start up the server to expose the metrics.
    if _prometheus_enable:
        prometheus_client.start_http_server(int(_prometheus_port))
        # init prometheus metrics
        metrics = init_rmd_info()

    # Loop for checking every configured interval
    while True:
        # Start checking devices
        check_devices()
		
        # Create prometheus metrics
        if _prometheus_enable:
            create_prometheus_metrics(metrics)   

        # checking for rebooted devices
        check_rebooted_devices()
			
        # Reboot devices if nessessary
        reboot_bad_devices()

        # Waiting for next check			
        logging.info("Waiting for {} seconds...".format(_sleeptime_between_check))
        time.sleep(int(_sleeptime_between_check))

except KeyboardInterrupt:
    logging.info("RMD will be stopped")
    exit(0)	

