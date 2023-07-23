#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "4.0.5"
__status__ = "DEV"


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
    _api_endpoint_workers = _config.get("FLYGONAPI", "API_ENDPOINT_WORKERS")
    _api_endpoint_areas = _config.get("FLYGONAPI", "API_ENDPOINT_AREAS")
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
    _proto_timeout = _config.get("REBOOTOPTIONS", "PROTO_TIMEOUT", fallback=15)
    _force_reboot_timeout = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_TIMEOUT", fallback=20)
    _force_reboot_waittime = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_WAITTIME", fallback=0)
    _off_on_sleep = _config.get("REBOOTOPTIONS", "OFF_ON_SLEEP", fallback=5)
    _reboot_waittime = _config.get("REBOOTOPTIONS", "REBOOT_WAITTIME", fallback=15)
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
                                'acc_username': "",
                                'start_step': 0,
                                'end_step': 0,
                                'step': 0,								
                                'host': "",
                                'area_name': "",
                                'area_id': 0,
                                'pokemon_mode_worker': 0,
                                'quest_mode_worker': 0,
                                'fort_mode_worker': 0								
								}

        # Prometheus metric for build
        self.rmd_version_info = prometheus_client.Info('rmd_build_version', 'Description of info')
        self.rmd_version_info.info({'version': __version__, 'status': __status__})
        # Prometheus metric for device config
        self.rmd_metric_device_info = prometheus_client.Gauge('rmd_metric_device_info', 'Device infos from config', ['device', 'device_location', 'mapper_mode', 'ip_address', 'switch_mode', 'led_position']) 
        for device in self._rmd_data:
            self.rmd_metric_device_info.labels(device, self._rmd_data[device]['device_location'],self._rmd_data[device]['mapper_mode'], self._rmd_data[device]['ip_address'], self._rmd_data[device]['switch_mode'], self._rmd_data[device]['led_position']).set(1)
        #Prometheus metric for device
        self.rmd_metric_device_last_seen = prometheus_client.Gauge('rmd_metric_device_last_seen', 'Device last seen', ['device'])
        self.rmd_metric_device_last_reboot_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_time', 'Device last reboot time', ['device'])
        self.rmd_metric_device_reboot_count = prometheus_client.Gauge('rmd_metric_device_reboot_count', 'Device reboot count', ['device'])
        self.rmd_metric_device_reboot_nessessary = prometheus_client.Gauge('rmd_metric_device_reboot_nessessary', 'Device reboot nessessary', ['device'])
        self.rmd_metric_device_reboot_force = prometheus_client.Gauge('rmd_metric_device_reboot_force', 'Device need reboot force', ['device'])
        self.rmd_metric_device_last_reboot_forced_time = prometheus_client.Gauge('rmd_metric_device_last_reboot_forced_time', 'Device last reboot force time', ['device'])
        self.rmd_metric_device_webhook_id = prometheus_client.Gauge('rmd_metric_device_webhook_id', 'Actual status discord webhook id', ['device'])
        self.rmd_metric_device_workerarea_id = prometheus_client.Gauge('rmd_metric_device_workerarea_id', 'Actual area id', ['device'])
        self.rmd_metric_device_acc_username = prometheus_client.Gauge('rmd_metric_device_acc_username', 'Actual acc username', ['device','acc_username'])
        self.rmd_metric_device_workstep = prometheus_client.Gauge('rmd_metric_device_workstep', 'Device working step information', ['device', 'start_step', 'end_step', 'area_id', 'area_name'])
        #Prometheus metric for area
        self.rmd_metric_area_pokemon_worker = prometheus_client.Gauge('rmd_metric_area_pokemon_worker', 'Area worker pokemon mode count', ['area_id', 'area_name'])
        self.rmd_metric_area_quest_worker = prometheus_client.Gauge('rmd_metric_area_quest_worker', 'Area worker quest mode count', ['area_id', 'area_name'])
        self.rmd_metric_area_fort_worker = prometheus_client.Gauge('rmd_metric_area_fort_worker', 'Area worker fort mode count', ['area_id', 'area_name'])

    
    def getDeviceStatusData(self):
        # Get device data from flygon api
        try:
            logging.debug("Get device data from flygon api")
            response = requests.get(self._api_endpoint_workers)
            deviceStatusData = response.json()

        except:
            logging.error("Get device data from flygon api failed.")
            logging.error("sleep 30s and retry")            
            time.sleep(30)
            self.getDeviceStatusData()			

        return deviceStatusData

    def getAreaData(self):
        # Get area data from flygon api
        try:
            logging.debug("Get area data from flygon api")
            response = requests.get(self._api_endpoint_areas)
            areaData = response.json()

            # Prepare data for prometheus
            for area in areaData['data']:
                self._area_data[area['id']]= {'name': area['name'],
                                              'pokemon_mode_workers': area['pokemon_mode']['workers'],
                                              'quest_mode_workers': area['quest_mode']['workers'],
                                              'fort_mode_workers': area['pokemon_mode']['workers']}

        except:
            logging.error("Get area data from flygon api failed.")
            logging.error("sleep 30s and retry")            
            time.sleep(30)
            self.getAreaData()			

        return areaData

    def check_client(self, device, deviceStatusData, areaData):
        uuid = device
        self._device_origin = uuid

        # Update data from deviceStatusData in _rmd_data set
        if any(device['uuid'] == uuid for device in deviceStatusData['data']):
            device_data = next(device for device in deviceStatusData['data'] if device['uuid'] == uuid)
            self._rmd_data[uuid]['last_seen'] = device_data['last_seen']
            self._rmd_data[uuid]['acc_username'] = device_data['username']
            for area in areaData['data']:
                if area['id'] == device_data['area_id']: 
                    self._rmd_data[uuid]['area_name'] = area['name']
            self._rmd_data[uuid]['area_id'] = device_data['area_id']
            self._rmd_data[uuid]['start_step'] = device_data['start_step']			
            self._rmd_data[uuid]['end_step'] = device_data['end_step']			
            self._rmd_data[uuid]['step'] = device_data['step']
            self._rmd_data[uuid]['host'] = device_data['host']

            # Analyze DATA of device
            logging.debug("Checking device {} for nessessary reboot.".format(self._device_origin))
    
            if self.calc_past_min_from_now(self._rmd_data[self._device_origin]['last_seen']) > int(self._proto_timeout):
    
                if self.calc_past_min_from_now(self._rmd_data[self._device_origin]['last_reboot_time']) < int(self._reboot_waittime):
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

        # API-call for area names
        areaData = self.getAreaData()
        #print(areaData)

        try:    
            threads = []
            for device in self._rmd_data:
                thread = Thread(target=self.check_client, args=(device, deviceStatusData, areaData))
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
                rebootedDevicedList.append({'device': device, 'worker_status': self._rmd_data[device]['worker_status'], 'last_seen': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_seen']), 'offline_minutes': self.calc_past_min_from_now(self._rmd_data[device]['last_seen']), 'count': self._rmd_data[device]['reboot_count'], 'last_reboot_time': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_reboot_time']), 'reboot_ago_min': self.calc_past_min_from_now(self._rmd_data[device]['last_reboot_time']), 'type': self._rmd_data[device]['reboot_type']})

                # Update no_data time and existing Discord messages
                if self._rmd_data[device]['webhook_id'] != 0:
                        logging.info('Update Discord message')
                        self.discord_message(device)

        if not rebootedDevicedList:
            self.printTable([{'device': '-','worker_status': '-','last_seen': '-','offline_minutes': '-','count': '-','last_reboot_time': '-','reboot_ago_min': '-','type': '-'}], ['device','worker_status','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
            logging.info("")
        else:
            self.printTable(rebootedDevicedList, ['device','worker_status','last_seen','offline_minutes','count','last_reboot_time','reboot_ago_min','type'])
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
                badDevicedList.append({'device': device, 'worker_status': self._rmd_data[device]['worker_status'], 'last_seen': self.timestamp_to_readable_datetime(self._rmd_data[device]['last_seen']), 'offline_minutes': self.calc_past_min_from_now(self._rmd_data[device]['last_seen']), 'count': self._rmd_data[device]['reboot_count'], 'reboot_nessessary': self._rmd_data[device]['reboot_nessessary'], 'force': self._rmd_data[device]['reboot_force']})

        if not badDevicedList:
            self.printTable([{'device': '-','worker_status': '-','last_seen': '-','offline_minutes': '-','count': '-','reboot_nessessary': '-', 'force': '-'}], ['device','worker_status','last_seen','offline_minutes','count','reboot_nessessary','force'])
            logging.info("")
        else:
            self.printTable(badDevicedList, ['device','worker_status','last_seen','offline_minutes','count','reboot_nessessary','force'])
            logging.info("")

        ## reboot in threads
        reboot_threads = []

        for badDevice in badDevicedList:
            reboot_thread = Thread(target=self.doRebootDevice, args=(badDevice["device"]))
            reboot_thread.start()
            reboot_threads.append(thread)
    
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
            self.call_reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
            return
        while counter < try_counter:
            if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'] in adb_tools.adb_tools.list_adb_connected_devices(self._adb_path,self._adb_port):
                logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
                if eval(self._try_restart_mapper_first):
                    logging.info("Try to restart {} on Device {}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'],DEVICE_ORIGIN_TO_REBOOT))
                    return_code = reboot.reboot.restart_mapper_sw(self._adb_path, self._adb_port, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], self._rootdir, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['mapper_mode'])
                    if return_code == 0:
                        logging.info("Restart Mapper on Device {} was successfull.".format(DEVICE_ORIGIN_TO_REBOOT))
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "MAPPER"
                        return
                    else:
                        logging.info("Execute of restart Mapper on Device {} was not successfull. Try reboot device now.".format(DEVICE_ORIGIN_TO_REBOOT))

                    logging.info("rebooting Device {}. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
                    return_code = reboot.reboot.adb_reboot(self._adb_path, self._adb_port, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'])
                    if return_code == 0:
                        logging.info("Restart via adb of Device {} was successfull.".format(DEVICE_ORIGIN_TO_REBOOT))
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
                        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "ADB"
                    else:
                        logging.warning("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
                        self.call_reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)                    
                return
                break;
            else:
                logging.debug("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
                adb_tools.adb_tools.connect_device(self._adb_path, self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'])
                counter = counter + 1
        else:
            self.call_reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
            return


    def call_reboot_device_via_power(self, DEVICE_ORIGIN_TO_REBOOT):
        ## read powerSwitch config
        powerSwitchMode = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_mode']
        powerSwitchOption = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_option']
        powerSwitchValue = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_value']

        ## setting data for webhook
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = powerSwitchMode

        reboot.reboot.reboot_device_via_power(powerSwitchMode, powerSwitchOption, powerSwitchValue)


    def create_prometheus_metrics(self):
        logging.info(f'create metrics for prometheus...')
       
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
                self.rmd_metric_device_workerarea_id.labels(device).set(self._rmd_data[device]['area_id'])	
                self.rmd_metric_device_acc_username.labels(device, self._rmd_data[device]['acc_username'] ).set(1)
                self.rmd_metric_device_workstep.labels(device, self._rmd_data[device]['start_step'], self._rmd_data[device]['end_step'], self._rmd_data[device]['area_id'], self._area_data[self._rmd_data[device]['area_id']]['name']).set(self._rmd_data[device]['step'])
            except:
                logging.error("Error creating prometheus metrics for device {} ".format(device))

        for area in self._area_data:
            try:
                self.rmd_metric_area_pokemon_worker.labels(area ,self._area_data[area]['name'] ).set(self._area_data[area]['pokemon_mode_workers'])
                self.rmd_metric_area_quest_worker.labels(area ,self._area_data[area]['name'] ).set(self._area_data[area]['quest_mode_workers'])
                self.rmd_metric_area_fort_worker.labels(area ,self._area_data[area]['name'] ).set(self._area_data[area]['fort_mode_workers'])
            except:
                logging.error("Error creating prometheus metrics for area {} ".format(area))                


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
        """ make timestamp human readable """
        timestamp = datetime.datetime.fromtimestamp(vartimestamp)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")


    ## print list as table for logging
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

    ## Import modul classes
    if rmdData._ip_ban_check_enable:
        from lib import check_ipban
    from lib import adb_tools
    from lib import reboot

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
                check_ipban.check_ipban(rmdData._ip_ban_check_wh, rmdData._ip_ban_check_ping )
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