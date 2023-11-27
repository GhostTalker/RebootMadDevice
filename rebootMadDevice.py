#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "4.2.1"
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

class rmdData(object):
    
    ## read config
    _config = configparser.ConfigParser()
    _rootdir = os.path.dirname(os.path.abspath('config.ini'))
    _config.read(_rootdir + "/config/config.ini")
    _api_rotom_secret = _config.get("ROTOMAPI", "API_ROTOM_SECRET", fallback=None)
    _api_endpoint_status = _config.get("ROTOMAPI", "API_ENDPOINT_STATUS")
    _prometheus_enable = _config.getboolean("PROMETHEUS", "PROMETHEUS_ENABLE", fallback=False)
    _prometheus_port = _config.get("PROMETHEUS", "PROMETHEUS_PORT", fallback=8000)
    _prometheus_device_location = _config.get("PROMETHEUS", "PROMETHEUS_DEVICE_LOCATION", fallback="")
    _sleeptime_between_check = _config.get("REBOOTOPTIONS", "SLEEPTIME_BETWEEN_CHECK", fallback=5)
    _ip_ban_check_enable = _config.getboolean("IP_BAN_CHECK", "BANCHECK_ENABLE", fallback=False)
    _ip_ban_check_wh = _config.get("IP_BAN_CHECK", "BANCHECK_WEBHOOK", fallback='')
    _ip_ban_check_ping = _config.get("IP_BAN_CHECK", "BANPING", fallback=0)
    _discord_webhook_enable = _config.getboolean("DISCORD", "WEBHOOK", fallback=False)
    _discord_webhook_url = _config.get("DISCORD", "WEBHOOK_URL", fallback='')
    _try_adb_first = _config.get("REBOOTOPTIONS", "TRY_ADB_FIRST")
    _try_restart_mapper_first = _config.get("REBOOTOPTIONS", "TRY_RESTART_MAPPER_FIRST", fallback='False')
    _sleeptime_between_check = _config.get("REBOOTOPTIONS", "SLEEPTIME_BETWEEN_CHECK", fallback=5)
    _proto_timeout = _config.get("REBOOTOPTIONS", "PROTO_TIMEOUT", fallback=300)
    _force_reboot_timeout = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_TIMEOUT", fallback=1800)
    _force_reboot_waittime = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_WAITTIME", fallback=3600)
    _off_on_sleep = _config.get("REBOOTOPTIONS", "OFF_ON_SLEEP", fallback=5)
    _reboot_waittime = _config.get("REBOOTOPTIONS", "REBOOT_WAITTIME", fallback=300)
    _adb_path = _config.get("ENVIROMENT", "ADB_PATH", fallback='/usr/bin')
    _adb_port = _config.get("ENVIROMENT", "ADB_PORT", fallback='5555')
    _led_enable = _config.get("STATUS_LED", "LED_ENABLE")
    _led_type = _config.get("STATUS_LED", "LED_TYPE", fallback='internal')
    _led_count = _config.get("STATUS_COUNT", "LED_ENABLE", fallback=60)
    _led_pin = _config.get("STATUS_LED", "LED_PIN", fallback=18)
    _led_freq_hz = _config.get("STATUS_LED", "LED_FREQ_HZ", fallback=800000)
    _led_dma = _config.get("STATUS_LED", "LED_DMA", fallback=10)
    _led_brightness = _config.get("STATUS_LED", "LED_BRIGHTNESS", fallback=255)
    _led_invert = _config.get("STATUS_LED", "LED_INVERT")
    _led_ws_external = _config.get("STATUS_LED", "LED_WS_EXTERNAL", fallback='')
    _gpio_usage = _config.get("GPIO", "GPIO_USAGE")
    _reboot_cycle = _config.get("REBOOT_CYCLE", "REBOOT_CYCLE", fallback='False')
    _reboot_cycle_last_timestamp = int(datetime.datetime.timestamp(datetime.datetime.now()))
    _reboot_cycle_wait_time = _config.get("REBOOT_CYCLE", "REBOOT_CYCLE_WAIT_TIME", fallback=20)


    def __init__(self):
        self.initRMDdata()		
  
  
    def initRMDdata(self):
        # init dict 
        self._rmd_data = {}
        self._area_data = {}
    
        # read json file
        logging.debug("Read data from devices.json file.")
        with open('config/devices.json') as json_file:
           _jsondata = json.load(json_file) 
    
        # init rmd data in dict
        logging.debug("Init rmd data dictonary.")
        for device in _jsondata:
            self._rmd_data[device]= {'ip_address': _jsondata[device]["IP_ADDRESS"],
                                'mapper_mode': _jsondata[device]["MAPPER_MODE"],
                                'switch_mode': _jsondata[device]["SWITCH_MODE"],
                                'switch_option': _jsondata[device]["SWITCH_OPTION"],
                                'switch_value': _jsondata[device]["SWITCH_VALUE"],
                                'led_position': _jsondata[device]["LED_POSITION"],
                                'device_location': self._prometheus_device_location,
                                'last_seen': 0,
                                'last_reboot_time': self.makeTimestamp(),
                                'reboot_count': 0,
                                'reboot_nessessary': False,
                                'reboot_force': False,
                                'reboot_type': None,
                                'reboot_forced': False,
                                'last_reboot_forced_time': 0,
                                'webhook_id': 0,
                                'workercount': 0								
								}

        # Prometheus metric for build and running info
        self.rmd_version_info = prometheus_client.Info('rmd_build_version', 'Description of info')
        self.rmd_version_info.info({'version': __version__, 'status': __status__, 'started': self.timestamp_to_readable_datetime(self.makeTimestamp())})
        self.rmd_script_running_info = prometheus_client.Gauge('rmd_script_cycle_info', 'Actual cycle of the running script')
        self.rmd_script_running_info.set(0)
        # Prometheus metric for device config
        self.rmd_metric_device_info = prometheus_client.Gauge('rmd_metric_device_info', 'Device infos from config', ['device', 'device_location', 'mapper_mode', 'ip_address', 'switch_mode', 'led_position']) 
        for device in self._rmd_data:
            self.rmd_metric_device_info.labels(device, self._rmd_data[device]['device_location'],self._rmd_data[device]['mapper_mode'], self._rmd_data[device]['ip_address'], self._rmd_data[device]['switch_mode'], self._rmd_data[device]['led_position']).set(1)
        #Prometheus metric for device
        self.rmd_metric_device_last_seen = prometheus_client.Gauge('rmd_metric_device_last_seen', 'Device last seen', ['device'])
        self.rmd_metric_device_status = prometheus_client.Gauge('rmd_metric_device_status', 'Device status', ['device'])
        self.rmd_metric_device_last_reboot_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_time', 'Device last reboot time', ['device'])
        self.rmd_metric_device_reboot_count = prometheus_client.Gauge('rmd_metric_device_reboot_count', 'Device reboot count', ['device'])
        self.rmd_metric_device_reboot_nessessary = prometheus_client.Gauge('rmd_metric_device_reboot_nessessary', 'Device reboot nessessary', ['device'])
        self.rmd_metric_device_reboot_force = prometheus_client.Gauge('rmd_metric_device_reboot_force', 'Device need reboot force', ['device'])
        self.rmd_metric_device_last_reboot_forced_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_forced_time', 'Device last reboot force time', ['device'])
        self.rmd_metric_device_webhook_id = prometheus_client.Gauge('rmd_metric_device_webhook_id', 'Actual status discord webhook id', ['device'])


    def getDeviceStatusData(self):
        method = "get"
        url = self._api_endpoint_status
        auth = None
        headers = {
           'Accept': 'application/json',
           'X-Rotom-Secret': self._api_rotom_secret
        }

        while True:
            # Get device data from rotom api
            try:
                logging.debug("Get device data from rotom api")
                response = requests.request(method, url, headers=headers, auth=auth)
                deviceStatusData = response.json()
                return deviceStatusData  # return inside the try block
    
            except:
                logging.error("Get device data from rotom api failed.")
                logging.error("sleep 30s and retry")
                time.sleep(30)  # if request fails, sleep and then retry


    def check_client(self, device_origin, deviceStatusData):
        self._device_origin = device_origin

        # Update data from deviceStatusData in _rmd_data set
        if any(device['origin'] == self._device_origin for device in deviceStatusData['devices']):
            device_data = next(device for device in deviceStatusData['devices'] if device['origin'] == self._device_origin)
            self._rmd_data[self._device_origin]['last_seen'] = device_data['dateLastMessageReceived']


            # Analyze DATA of device
            logging.debug("Checking device {} for nessessary reboot.".format(self._device_origin))
    
            if self.calc_past_min_from_now(self._rmd_data[self._device_origin]['last_seen']) > int(self._proto_timeout):
                if self.calc_past_min_from_now(self._rmd_data[self._device_origin]['last_reboot_time'])*60 < (int(self._reboot_waittime)):
                    self._rmd_data[self._device_origin]['reboot_nessessary'] = 'rebooting'
                    ## set led status warn if enabled
                    try:
                        if eval(self._led_enable):
                            logging.debug("Set status LED to warning for device {}".format(self._device_origin))
                            self.setStatusLED(self._device_origin, 'warn')
                    except:
                        logging.error("Error setting status LED for device {} ".format(self._device_origin))
    
                else:						
                    self._rmd_data[self._device_origin]['reboot_nessessary'] = True
                    if self.calc_past_min_from_now(self._rmd_data[self._device_origin]['last_seen']) > int(self._force_reboot_timeout) or eval(self._try_adb_first) is False: 
                        self._rmd_data[self._device_origin]['reboot_force'] = True
    
                    ## set led status critical if enabled
                    try:
                        if eval(self._led_enable):
                            logging.debug("Set status LED to critical for device {}".format(self._device_origin))
                            self.setStatusLED(device, 'crit')
                    except:
                        logging.error("Error setting status LED for device: {} ".format(self._device_origin))
    
            else:
                self._rmd_data[self._device_origin]['reboot_nessessary'] = False
                self._rmd_data[self._device_origin]['reboot_force'] = False
                self._rmd_data[self._device_origin]['reboot_count'] = 0
                self._rmd_data[self._device_origin]['reboot_type'] = None
    
                # clear webhook_id after fixed message
                if self._rmd_data[device]['webhook_id'] != 0:
                    self.discord_message(device, fixed=True)
                    self._rmd_data[self._device_origin]['webhook_id'] = 0  
    
                ## set led status ok if enabled
                try:
                    if eval(self._led_enable):
                        logging.debug("Set status LED to ok for device {}".format(self._device_origin))
                        self.setStatusLED(self._device_origin, 'ok')
                except:
                    logging.error("Error setting status LED for device {} ".format(self._device_origin))
    
                ## Check for daily PowerCycle
                if eval(self._reboot_cycle):
                    logging.debug("Checking if devices {} was rebooted within 24h.".format(self._device_origin))
                    if int(self._rmd_data[self._device_origin]['last_reboot_time']) < int(datetime.datetime.timestamp(datetime.datetime.now() - datetime.timedelta(hours = 24))):
                        logging.info("Last reboot older than 24h. Rebooting!")
                        self._rmd_data[self._device_origin]['reboot_nessessary'] = True                    


    def check_clients(self):
        logging.info(f'Checking all clients...')
    
        # API-call for device status
        deviceStatusData = self.getDeviceStatusData()

        try:    
            threads = []
            for device in self._rmd_data:
                thread = Thread(target=self.check_client, args=(device, deviceStatusData))
                thread.start()
                threads.append(thread)
        
            for thread in threads:
                thread.join()
        except:
            logging.error("Error checking clients. Threads failed.")


    def check_rebooted_devices(self):
        rebootedDevicedList = []
        logging.debug("Find rebooted devices for information and update discord message.")	
        logging.info("")
        logging.info("---------------------------------------------")
        logging.info("Devices are rebooted. Waiting to come online:")	
        logging.info("---------------------------------------------")
        logging.info("")

        for device in list(self._rmd_data):
            if str(self._rmd_data[device]['reboot_nessessary']) == 'rebooting': 
                rebootedDevicedList.append({'device': device, 'area': self._rmd_data[device]['area_name'], 'last_seen': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_seen']), 'offline_minutes': self.calc_past_min_from_now(self._rmd_data[device]['last_seen']), 'count': self._rmd_data[device]['reboot_count'], 'last_reboot_time': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_reboot_time']), 'reboot_ago_min': self.calc_past_min_from_now(self._rmd_data[device]['last_reboot_time']), 'type': self._rmd_data[device]['reboot_type']})

                # Update no_data time and existing Discord messages
                if self._rmd_data[device]['webhook_id'] != 0:
                        logging.info('Update Discord message')
                        self.discord_message(device)

        if not rebootedDevicedList:
            self.printTable([{'device': '-','area': '-','last_seen': '-','offline_minutes': '-','count': '-','last_reboot_time': '-','reboot_ago_min': '-','type': '-'}], ['device','area','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
            logging.info("")
        else:
            self.printTable(rebootedDevicedList, ['device','area','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
            logging.info("")


    def reboot_bad_devices(self):
	
        ##checking for bad devices
        badDevicedList = []
        logging.debug("Find bad devices and reboot them.")	
        logging.info("")
        logging.info("---------------------------------------------")
        logging.info("Devices for reboot:")	
        logging.info("---------------------------------------------")
        logging.info("")

        for device in list(self._rmd_data):
            if str(self._rmd_data[device]['reboot_nessessary']) == 'True':
                badDevicedList.append({'device': device, 'area': self._rmd_data[device]['area_name'], 'last_seen': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_seen']), 'offline_minutes': self.calc_past_min_from_now(self._rmd_data[device]['last_seen']), 'count': self._rmd_data[device]['reboot_count'], 'reboot_nessessary': self._rmd_data[device]['reboot_nessessary'], 'force': self._rmd_data[device]['reboot_force']})

        if not badDevicedList:
            self.printTable([{'device': '-','area': '-','last_seen': '-','offline_minutes': '-','count': '-','reboot_nessessary': '-', 'force': '-'}], ['device','area','last_seen','offline_minutes','count','reboot_nessessary','force'])
            logging.info("")
        else:
            self.printTable(badDevicedList, ['device','area','last_seen','offline_minutes','count','reboot_nessessary','force'])
            logging.info("")

        ## reboot in threads
        reboot_threads = []

        for badDevice in badDevicedList:
            reboot_thread = Thread(target=self.doRebootDevice, args=(badDevice["device"],))
            reboot_thread.start()
            reboot_threads.append(reboot_thread)
    
        for reboot_thread in reboot_threads:
            reboot_thread.join()


    def doRebootDevice(self, DEVICE_ORIGIN_TO_REBOOT):

        try_counter = 2
        counter = 0
        # Create discord message
        if self._discord_webhook_enable:
            self.discord_message(DEVICE_ORIGIN_TO_REBOOT)

        logging.info("Origin to reboot is: {}".format(DEVICE_ORIGIN_TO_REBOOT))
        logging.info("Force option is: {}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force']))
        logging.debug("Rebootcount is: {}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count']))

        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] + 1
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_time'] = self.makeTimestamp()

        if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force'] and self.calc_past_min_from_now(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_forced_time']) > int(self._force_reboot_waittime):
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_forced_time'] = self.makeTimestamp()
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
            return
        while counter < try_counter:
            if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'] in self.list_adb_connected_devices():
                logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
                if eval(self._try_restart_mapper_first):
                    logging.info("Try to restart {} on Device {}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'],DEVICE_ORIGIN_TO_REBOOT))
                    return_code = self.restart_mapper_sw(DEVICE_ORIGIN_TO_REBOOT)
                    if return_code == 0:
                        logging.info("Restart Mapper on Device {} was successfull.".format(DEVICE_ORIGIN_TO_REBOOT))
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "MAPPER"
                        return
                    else:
                        logging.info("Execute of restart Mapper on Device {} was not successfull. Try reboot device now.".format(DEVICE_ORIGIN_TO_REBOOT))

                    logging.info("rebooting Device {}. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
                    return_code = self.adb_reboot(DEVICE_ORIGIN_TO_REBOOT)
                    if return_code == 0:
                        logging.info("Restart via adb of Device {} was successfull.".format(DEVICE_ORIGIN_TO_REBOOT))
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "ADB"
                    else:
                        logging.warning("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
                        self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)                    
                return
                break;
            else:
                logging.debug("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
                self.connect_device(DEVICE_ORIGIN_TO_REBOOT)
                counter = counter + 1
        else:
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
            return


    def list_adb_connected_devices(self):
        cmd = "{}/adb devices | /bin/grep {}".format(self._adb_path, self._adb_port)
        try:
            connectedDevices = subprocess.check_output([cmd], shell=True)
            connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
                "\\n", ",").replace("\\tdevice", "").split(",")
        except subprocess.CalledProcessError:
            connectedDevices = ()
        return connectedDevices


    def connect_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = "{}/adb connect {}".format(self._adb_path, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'])
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            logging.info("Connection via adb failed")
        # Wait for 2 seconds
        time.sleep(2)

    
    def restart_mapper_sw(self, DEVICE_ORIGIN_TO_REBOOT):
        _adbloc = "{}/adb".format(self._adb_path)
        _deviceloc = "{}:{}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], self._adb_port)
        _mapperscript = "{}/mapperscripts/restart{}.sh".format(self._rootdir, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'])
        try:
            subprocess.Popen([_mapperscript, _adbloc, _deviceloc])
            return 0
        except:
            return 1
    	 
    
    def adb_reboot(self, DEVICE_ORIGIN_TO_REBOOT):
        _adbloc = "{}/adb".format(self._adb_path)
        _deviceloc = "{}:{}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], self._adb_port)
        try:
            subprocess.Popen([adbloc, '-s', DEVICELOC, 'reboot'])
            return 0
        except:
            return 1
		

    def reboot_device_via_power(self, DEVICE_ORIGIN_TO_REBOOT):
        ## read powerSwitch config
        powerSwitchMode = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_mode']
        powerSwitchOption = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_option']
        powerSwitchValue = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_value']

        ## setting data for webhook
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = powerSwitchMode

        ## HTML 
        if powerSwitchMode == 'HTML':
            logging.debug("PowerSwitch with HTML starting.")
            poweron = powerSwitchValue.split(";")[0]
            poweroff = powerSwitchValue.split(";")[1]
            logging.info("turn HTTP PowerSwitch off")
            requests.get(poweroff)
            time.sleep(int(self._off_on_sleep))
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
            time.sleep(int(self._off_on_sleep))
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
            time.sleep(int(self._off_on_sleep))
            logging.debug("PowerSwitch with CMD done.")
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "CMD"
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
            time.sleep(int(self._off_on_sleep))
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
            try:
                subprocess.check_output(powerSwitchValue, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire poe port reset")
            time.sleep(int(self._off_on_sleep))
            logging.debug("PowerSwitch with POE done.")
            return

        ## PB
        elif powerSwitchMode == 'PB':
            logging.debug("PowerSwitch with PB starting.")
            pbport = powerSwitchValue
            pb_interface = powerSwitchOption
            pbporton = '/bin/echo -e "on {}" > {}'.format(pbport, pb_interface)
            pbportoff = '/bin/echo -e "off {}" > {}'.format(pbport, pb_interface)
            logging.info("send command to PowerBoard for PowerSwitch off")
            try:
                subprocess.check_output(pbportoff, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            time.sleep(int(self._off_on_sleep))
            logging.info("send command to Powerboard for PowerSwitch on")
            try:
                subprocess.check_output(pbporton, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            logging.debug("PowerSwitch with PB done.")
            return
			
        ## SNMP
        elif powerSwitchMode == 'SNMP':
            logging.debug("PowerSwitch with SNMP starting.")
            switchport = powerSwitchValue
            snmp_switch_ip_adress = powerSwitchOption.split(";")[0]
            snmp_community_string = powerSwitchOption.split(";")[1]
            snmpporton = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 1'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            snmpportoff = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 2'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            try:
                subprocess.check_output(snmpportoff, shell=True)
                logging.info("send SNMP command port OFF to SWITCH")
            except subprocess.CalledProcessError:
                logging.error("failed to fire SNMP command")
            time.sleep(int(self._off_on_sleep))
            try:
                subprocess.check_output(snmpporton, shell=True)
                logging.info("send SNMP command port ON to SWITCH")
            except subprocess.CalledProcessError:
                logging.error("failed to fire SNMP command")
            logging.debug("PowerSwitch with SNMP done.")
            return
        else:
            logging.warning("no PowerSwitch configured. Do it manually!!!")


    def create_prometheus_metrics(self):
        logging.info(f'create metrics for prometheus...')

        self.rmd_script_running_info.inc()
       
        for device in self._rmd_data:
            try:
                self.rmd_metric_device_last_seen.labels(device).set(self._rmd_data[device]['last_seen'])
                self.rmd_metric_device_last_reboot_time.labels(device).set(self._rmd_data[device]['last_reboot_time'])
                self.rmd_metric_device_reboot_count.labels(device).set(self._rmd_data[device]['reboot_count'])
                if self._rmd_data[device]['reboot_nessessary']:
                    self.rmd_metric_device_reboot_nessessary.labels(device).set(1)
                else:
                    self.rmd_metric_device_reboot_nessessary.labels(device).set(0)
                if self._rmd_data[device]['reboot_force']:
                    self.rmd_metric_device_reboot_force.labels(device).set(1)
                else:
                    self.rmd_metric_device_reboot_force.labels(device).set(0)
                self.rmd_metric_device_last_reboot_forced_time.labels(device).set(self._rmd_data[device]['last_reboot_forced_time'])
                self.rmd_metric_device_webhook_id.labels(device).set(self._rmd_data[device]['webhook_id'])
                if ( self.makeTimestamp() - self._rmd_data[device]['last_seen'] ) < int(self._proto_timeout):
                    self.rmd_metric_device_status.labels(device).set(0)
                elif str(self._rmd_data[device]['reboot_nessessary']) == 'rebooting' and (( self.makeTimestamp() - self._rmd_data[device]['last_seen'] ) < int(self._force_reboot_timeout)):
                    self.rmd_metric_device_status.labels(device).set(1)
                elif ( self.makeTimestamp() - self._rmd_data[device]['last_seen'] ) > int(self._force_reboot_timeout):
                    self.rmd_metric_device_status.labels(device).set(2)    				

            except:
                logging.error("Error creating prometheus metrics for device {} ".format(device))            


    def discord_message(self, device_origin, fixed=False):
        if not self._discord_webhook_enable:
            return

        # create data for webhook
        logging.info('Start Webhook for device ' + device_origin )

        now = datetime.datetime.utcnow()
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
                  "value": self._rmd_data[device_origin]['reboot_type'],
                  "inline": "true"
                },
                {
                  "name": "Force",
                  "value": self._rmd_data[device_origin]['reboot_forced'],
                  "inline": "true"
                }
              ]
            }
          ]
        }
        # add timestamp
        data["embeds"][0]["timestamp"] = str(now)

        # send webhook
        logging.debug('data to send with webhook:')
        logging.debug(data)
        logging.debug(self._rmd_data[device_origin]['webhook_id'])

        if self._rmd_data[device_origin]['webhook_id'] == 0:
            data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_seen'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`"
            try:
                result = requests.post(self._discord_webhook_url, json = data, params={"wait": True})
                result.raise_for_status()
                answer = result.json()
                logging.debug(answer)
                self._rmd_data[device_origin]["webhook_id"] = answer["id"]
                logging.debug(self._rmd_data[device_origin]["webhook_id"])
            except requests.exceptions.RequestException as err:
                logging.error(err)
        else:
            logging.debug('parameter fixed is: ' + str(fixed))
            if not fixed:
                data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_seen'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`\nFixed :x:"
            else:
                data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_seen'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`\nFixed :white_check_mark:"

            try:
                result = requests.patch(self._discord_webhook_url + "/messages/" + str(self._rmd_data[device_origin]["webhook_id"]), json = data)
                result.raise_for_status()
            except requests.exceptions.RequestException as err:
                logging.error(err)

        return result.status_code


    def check_ipban(self):
        banned = True
        wh_send = False
        while banned: 
            logging.info("Checking PTC Login Servers...")
            try:
                result = requests.head('https://sso.pokemon.com/sso/login')
                result.raise_for_status()
            except requests.exceptions.RequestException as err:
                logging.info(f"PTC Servers are not reachable! Error: {err}")
                logging.info("Waiting 5 minutes and trying again")
                time.sleep(300)
                continue
            if result.status_code != 200:
                logging.info("IP is banned by PTC, waiting 5 minutes and trying again")
                # Only send a message once per ban and only when a webhook is set
                if not wh_send and self._ip_ban_check_wh:
                    unbantime = datetime.datetime.now() + datetime.timedelta(hours=3)
                    data = {
                        "username": "Alert!",
                        "avatar_url": "https://github.com/GhostTalker/icons/blob/main/rmd/messagebox_critical_256.png?raw=true",
                        "content": f"<@{self._ip_ban_check_ping}> IP address is currently banned by PTC! \nApproximate remaining time until unban: <t:{int(unbantime.timestamp())}:R> ({unbantime.strftime('%H:%M')})",
                    }
                    try:
                        result = requests.post(self._ip_ban_check_wh, json=data)
                        result.raise_for_status()
                    except requests.exceptions.RequestException as err:
                        logging.info(err)
                wh_send = True
                time.sleep(300)
                continue
            else:
                logging.info("IP is not banned by PTC, continuing...")
                banned = False
                wh_send = False
        

    def initiate_led(self):
        global strip
        # Create NeoPixel object with appropriate configuration.
        strip = Adafruit_NeoPixel(int(self._led_count), int(self.led_pin), int(self._led_freq_hz), int(self._led_dma), eval(self._led_invert), int(self._led_brightness))
        # Intialize the library (must be called once before other functions).
        strip.begin()
        for j in range(256 * 1):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, self.wheel_led((i + j) & 255))
            strip.show()
            time.sleep(20 / 1000.0)
        """Wipe color across display a pixel at a time."""
        for i in range(strip.numPixels()):
            strip.setPixelColorRGB(i, 0, 0, 0)
            strip.show()
            time.sleep(50 / 1000.0)


    def wheel_led(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)


    def setStatusLED(self, device_origin, alertColor):
        # get led position number
        dev_nr = self._rmd_data[device_origin]["led_position"]
       
        # define color values
        if alertColor == "crit":
            rLED = 255
            gLED = 0
            bLED = 0
        elif alertColor == "warn":
            rLED = 255
            gLED = 255
            bLED = 0
        elif alertColor == "ok":
            rLED = 0
            gLED = 255
            bLED = 0

        if rmdItem._led_type == "internal":
            # execute to led strip
            logging.debug("LED alertlvl: " + str(alertColor))
            logging.debug("LED Colors: " + str(rLED) + ", " + str(gLED) + ", " + str(bLED))
            strip.setPixelColorRGB(int(dev_nr) - 1, int(rLED), int(gLED), int(bLED))
            strip.show()
        elif rmdItem._led_type == "external":
            websocket.enableTrace(False)
            ws = create_connection(rmdItem._led_ws_external)  # open socket
            hexcolor = webcolors.rgb_to_hex((rLED, gLED, bLED)).replace("#", "")
            led_number = '%0.4d' % (int(dev_nr) - 1)
            payload = "!{} {}".format(led_number, hexcolor)
            ws.send(payload)  # send to websocket
            ws.close()  # close websocket


    ## time calculations and transformation
    def calc_past_min_from_now(self, timestamp):
        """ calculate time between now and given timestamp """
        now = int(time.time())
        if timestamp == None or timestamp == "":
            return 99999
        elif int(timestamp) > int(now):
            return 0
        diffToNow = int(now) - int(timestamp)
        past_min_from_now = int(diffToNow / 60)
        return int(past_min_from_now)


    def makeTimestamp(self):
        ts = int(time.time())
        return ts


    def timestamp_to_readable_datetime(self, vartimestamp):
        try:
            """ make timestamp human readable """
            timestamp = datetime.datetime.fromtimestamp(vartimestamp)
        except:
            """ prevent error while having wrong timestamp """
            timestamp = datetime.datetime.fromtimestamp(self.makeTimestamp())            
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")


    def printTable(self, myDict, colList=None):
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


## Logging handler
def create_timed_rotating_log(log_file):
    logging.basicConfig(filename=log_file, filemode='a', format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(log_level))
    logger = logging.getLogger(__name__)
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=3)
    logger.addHandler(file_handler)


def create_stdout_log():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)


if __name__ == '__main__':

    # Logging Options
    logconfig = configparser.ConfigParser()
    logrootdir = os.path.dirname(os.path.abspath('config/config.ini'))
    logconfig.read(logrootdir + "/config.ini")
    log_mode = logconfig.get("LOGGING", "LOG_MODE", fallback='console')
    log_filename = logconfig.get("LOGGING", "LOG_FILENAME", fallback='RMDClient.log')
    log_level = logconfig.get("LOGGING", "LOG_LEVEL", fallback='INFO')

    if log_mode == "console":
        create_stdout_log()
    elif log_mode == "file":
        create_timed_rotating_log(log_filename)
    else:
        create_timed_rotating_log('/dev/null')

    ## init rmdData
    rmdData = rmdData()

    # LED initalize / import libs
    if eval(rmdData._led_enable):
        logging.debug("LED feature activated")        
        if rmdData._led_type == "internal":
            logging.debug("import rpi_ws281x libs")
            from rpi_ws281x import *
            logging.debug("initiate led stripe")
            rmdData.initiate_led()
        elif rmdData._led_type == "external":
            logging.debug("import webcolors and websocket libs")
            import webcolors
            import websocket
            from websocket import create_connection

    try:
        # Start up the server to expose the metrics.
        if rmdData._prometheus_enable:
            prometheus_client.start_http_server(int(rmdData._prometheus_port))
        # Loop for checking every configured interval
        while True:
            # IP ban check if enabled
            if rmdData._ip_ban_check_enable:
                rmdData.check_ipban()
                logging.info("IP ban check done successfully")			     

            # Start checking devices
            logging.info("Update device status data.")	
            rmdData.check_clients()
			
            # Create prometheus metrics
            if rmdData._prometheus_enable:
                rmdData.create_prometheus_metrics()   

            # checking for rebooted devices
            rmdData.check_rebooted_devices()

            # Reboot devices if nessessary
            rmdData.reboot_bad_devices()

            # Waiting for next check			
            logging.info("Waiting for {} seconds...".format(rmdData._sleeptime_between_check))
            time.sleep(int(rmdData._sleeptime_between_check))
	
    except KeyboardInterrupt:
        logging.info("RMD will be stopped")
        exit(0)	