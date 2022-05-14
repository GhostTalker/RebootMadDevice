#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2022, The GhostTalker project"
__version__ = "3.1.1"
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
from mysql.connector import Error
from mysql.connector import pooling


class rmdItem(object):
    
    ## read config
    _config = configparser.ConfigParser()
    _rootdir = os.path.dirname(os.path.abspath('config.ini'))
    _config.read(_rootdir + "/config.ini")
    _mysqlhost = _config.get("DATABASE", "DB_HOST", fallback='127.0.0.1')
    _mysqlport = _config.get("DATABASE", "DB_PORT", fallback='3306')
    _mysqldb = _config.get("DATABASE", "DB_NAME")
    _mysqluser = _config.get("DATABASE", "DB_USER")
    _mysqlpass = _config.get("DATABASE", "DB_PASS")
    _mysqldbtype = _config.get("DATABASE", "DB_TYPE")
    _try_adb_first = _config.get("REBOOTOPTIONS", "TRY_ADB_FIRST")
    _sleeptime_between_check = _config.get("REBOOTOPTIONS", "SLEEPTIME_BETWEEN_CHECK", fallback=5)
    _proto_timeout = _config.get("REBOOTOPTIONS", "PROTO_TIMEOUT", fallback=15)
    _force_reboot_timeout = _config.get("REBOOTOPTIONS", "FORCE_REBOOT_TIMEOUT", fallback=20)
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
    _ip_ban_check_enable = _config.get("IP_BAN_CHECK", "BANCHECK_ENABLE")
    _ip_ban_check_wh = _config.get("IP_BAN_CHECK", "BANCHECK_WEBHOOK", fallback='')
    _ip_ban_check_ping = _config.get("IP_BAN_CHECK", "BANPING", fallback=0)
    _discord_webhook_enable = _config.get("DISCORD", "WEBHOOK")
    _discord_webhook_url = _config.get("DISCORD", "WEBHOOK_URL", fallback='')
    _reboot_cycle = _config.get("REBOOT_CYCLE", "REBOOT_CYCLE", fallback='False')
    _reboot_cycle_last_timestamp = int(datetime.datetime.timestamp(datetime.datetime.now()))
    _reboot_cycle_wait_time = _config.get("REBOOT_CYCLE", "REBOOT_CYCLE_WAIT_TIME", fallback=20)

    def __init__(self):
        self.createConnectionPool()  
        self.initRMDdata()		

    
    def createConnectionPool(self):
        ## create connection pool and connect to MySQL
        try:
            self.connection_pool = pooling.MySQLConnectionPool(pool_name="mysql_connection_pool",
                                                          pool_size=2,
                                                          pool_reset_session=True,
                                                          host=self._mysqlhost,
                                                          port=self._mysqlport,
                                                          database=self._mysqldb,
                                                          user=self._mysqluser,
                                                          password=self._mysqlpass)
        

            logging.info("Create connection pool: ")
            logging.debug("Connection Pool Name - " + str(self.connection_pool.pool_name))
            logging.debug("Connection Pool Size - " + str(self.connection_pool.pool_size))
        
            # Get connection object from a pool
            connection_object = self.connection_pool.get_connection()
        
            if connection_object.is_connected():
                db_Info = connection_object.get_server_info()
                logging.debug("Connected to MySQL database using connection pool ... MySQL Server version on " + db_Info)
        
                cursor = connection_object.cursor()
                cursor.execute("select database();")
                record = cursor.fetchone()
                logging.info("Your connected to database " + str(record))
        
        except Error as e:
            logging.error("Error while connecting to MySQL using Connection pool: " + e)
        
        finally:
            # closing database connection.
            if connection_object.is_connected():
                cursor.close()
                connection_object.close()
                logging.debug("MySQL connection is closed")
    
    
    def initRMDdata(self):
        # init dict 
        self._rmd_data = {}
    
        # read json file
        logging.debug("Read data from devices.json file.")
        with open('devices.json') as json_file:
           _jsondata = json.load(json_file) 
    
        # init rmd data in dict
        logging.debug("Init rmd data dictonary.")
        for device in _jsondata:
            self._rmd_data[device]= {'ip_address': _jsondata[device]["IP_ADDRESS"],
                                'switch_mode': _jsondata[device]["SWITCH_MODE"],
                                'switch_option': _jsondata[device]["SWITCH_OPTION"],
                                'switch_value': _jsondata[device]["SWITCH_VALUE"],
                                'led_position': _jsondata[device]["LED_POSITION"],
                                'worker_status': "",
                                'idle_status': "",
                                'last_proto_data': "",
                                'current_sleep_time': "",
                                'last_reboot_time': 0,
                                'reboot_count': 0,
                                'reboot_nessessary': False,
                                'reboot_force': False,
                                'reboot_type': None,
                                'reboot_forced': False,
                                'webhook_id': None}
    	
    
    def getDeviceStatusData(self):
        # get device status data

        if self._mysqldbtype == "MAD":
            logging.debug("DB Type is MAD.")
            select_device_status_data = (
                    "SELECT s.name, t.lastProtoDateTime, t.currentSleepTime, t.idle, a.name  FROM trs_status t, settings_device s, settings_area a where s.device_id = t.device_id and t.area_id = a.area_id; "
                      )        
        elif self._mysqldbtype == "RDM":
            logging.debug("DB Type is RDM.")
            select_device_status_data = (
                    "SELECT d.uuid, d.last_seen, d.instance_name  FROM device d;"
                      )
        else:
            logging.error("DB Type not known. Please check config")

        try:
            logging.debug("Get db connection from connection pool.")
            connection_object = self.connection_pool.get_connection()
        
            # Get connection object from a pool
            if connection_object.is_connected():
                logging.debug("MySQL pool connection is open.")
                # Executing the SQL command
                cursor = connection_object.cursor()
                cursor.execute(select_device_status_data)
                # get all records
                records = cursor.fetchall()
                logging.debug("Select status data from database and update rmd data.")
                for row in records:
                    if self._mysqldbtype == "MAD":
                        try:
                            self._rmd_data[row[0]]['last_proto_data'] = datetime.datetime.timestamp(datetime.datetime.strptime(str(row[1]),"%Y-%m-%d %H:%M:%S"))
                            self._rmd_data[row[0]]['current_sleep_time'] = row[2]
                            self._rmd_data[row[0]]['idle_status'] = row[3]
                            self._rmd_data[row[0]]['worker_status'] = row[4]
                        except:
                            logging.debug("Device not configured. Ignoring data.")
                    elif self._mysqldbtype == "RDM":	
                        try:
                            self._rmd_data[row[0]]['last_proto_data'] = row[1]
                            self._rmd_data[row[0]]['current_sleep_time'] = 0
                            self._rmd_data[row[0]]['idle_status'] = 0
                            self._rmd_data[row[0]]['worker_status'] = row[2]
                        except:
                            logging.debug("Device not configured. Ignoring data.")
                    else:
                        logging.error("DB Type not known. Please check config")

        except Exception as e:
            logging.error("Error get connection from Connection pool ", e)
        
        finally:
            # closing database connection.
            if connection_object.is_connected():
                cursor.close()
                connection_object.close()
                logging.debug("MySQL pool connection is closed.")


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


    ## IP ban check
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
        
        banned = True
        wh_send = False
        while banned: 
            logging.info("Checking MAD Backend Login Servers...")
            try:
                result = requests.head('https://auth.maddev.eu')
                result.raise_for_status()
            except requests.exceptions.RequestException as err:
                logging.info(f"MAD Backend Servers are not reachable! Error: {err}")
                logging.info("Waiting 5 minutes and trying again")
                time.sleep(300)
                continue
            if result.status_code != 200:
                logging.info("IP is banned by MAD, waiting 5 minutes and trying again")
                # Only send a message once per ban and only when a webhook is set
                if not wh_send and rmdItem._ip_ban_check_wh:
                    unbantime = datetime.datetime.now() + datetime.timedelta(hours=3)
                    data = {
                        "username": "Alert!",
                        "avatar_url": "https://github.com/GhostTalker/icons/blob/main/rmd/messagebox_critical_256.png?raw=true",
                        "content": f"<@{rmdItem._ip_ban_check_ping}> IP address is currently banned by MAD! \nApproximate remaining time until unban: <t:{int(unbantime.timestamp())}:R> ({unbantime.strftime('%H:%M')})",
                    }
                    try:
                        result = requests.post(rmdItem._ip_ban_check_wh, json=data)
                        result.raise_for_status()
                    except requests.exceptions.RequestException as err:
                        logging.info(err)
                wh_send = True
                time.sleep(300)
                continue
            else:
                logging.info("IP is not banned by MAD, continuing...")
                banned = False
                wh_send = False
    
    
    def discord_message(self, device_origin, fixed=False):
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

        if self._rmd_data[device_origin]['webhook_id'] is None:
            data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_proto_data'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`"
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
                data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_proto_data'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`\nFixed :x:"
            else:
                data["embeds"][0]["description"] = f"`{device_origin}` did not send useful data for more than `{self.calc_past_min_from_now(self._rmd_data[device_origin]['last_proto_data'])}` minutes!\nReboot count: `{self._rmd_data[device_origin]['reboot_count']}`\nFixed :white_check_mark:"

            try:
                result = requests.patch(self._discord_webhook_url + "/messages/" + self._rmd_data[device_origin]["webhook_id"], json = data)
                result.raise_for_status()
            except requests.exceptions.RequestException as err:
                logging.error(err)

        return result.status_code


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


    def doRebootDevice(self, DEVICE_ORIGIN_TO_REBOOT):
        try_counter = 2
        counter = 0

        logging.info("Origin to reboot is: {}".format(DEVICE_ORIGIN_TO_REBOOT))
        logging.info("Force option is: {}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force']))

        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_count'] + 1
        self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['last_reboot_time'] = self.makeTimestamp()

        if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_force']:
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
            return
        while counter < try_counter:
            if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'] in self.list_adb_connected_devices():
                logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
                self.reboot_device(DEVICE_ORIGIN_TO_REBOOT)
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


    def reboot_device(self, DEVICE_ORIGIN_TO_REBOOT):
        #cmd = "{}/adb -s {}:{} reboot".format(self.adb_path, self.device_list[DEVICE_ORIGIN_TO_REBOOT], self.adb_port)
        logging.info("rebooting Device {}. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
        try:
            #subprocess.check_output([cmd], shell=True)
            ADBLOC="{}/adb".format(self._adb_path)
            DEVICELOC="{}:{}".format(self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'], self._adb_port)
            subprocess.Popen([ADBLOC, '-s', DEVICELOC, 'reboot'])
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = False
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "ADB"
            return
        except subprocess.CalledProcessError:
            logging.warning("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)


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
            time.sleep(5)
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
            time.sleep(10)
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
            time.sleep(5)
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
            time.sleep(5)
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
            time.sleep(5)
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
            time.sleep(5)
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
            time.sleep(5)
            try:
                subprocess.check_output(snmpporton, shell=True)
                logging.info("send SNMP command port ON to SWITCH")
            except subprocess.CalledProcessError:
                logging.error("failed to fire SNMP command")
            logging.debug("PowerSwitch with SNMP done.")
            return
        else:
            logging.warning("no PowerSwitch configured. Do it manually!!!")


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
    logrootdir = os.path.dirname(os.path.abspath('config.ini'))
    logconfig.read(logrootdir + "/config.ini")
    log_mode = logconfig.get("LOGGING", "LOG_MODE", fallback='console')
    log_level = logconfig.get("LOGGING", "LOG_LEVEL", fallback='INFO')

    if log_mode == "console":
        create_stdout_log()
    elif _log_mode == "file":
        create_timed_rotating_log('RMDclient.log')
    else:
        create_timed_rotating_log('/dev/null')

    ## init rmdItem
    rmdItem = rmdItem()
		
    # GPIO import libs
    if eval(rmdItem._gpio_usage):
        logging.debug("import GPIO libs")
        import RPi.GPIO as GPIO

    # LED initalize / import libs
    if eval(rmdItem._led_enable):
        logging.debug("LED feature activated")        
        if rmdItem._led_type == "internal":
            logging.debug("import rpi_ws281x libs")
            from rpi_ws281x import *
            logging.debug("initiate led stripe")
            rmdItem.initiate_led()
        elif rmdItem._led_type == "external":
            logging.debug("import webcolors and websocket libs")
            import webcolors
            import websocket
            from websocket import create_connection
		
    try:
        while True:
            if eval(rmdItem._ip_ban_check_enable):
                rmdItem.check_ipban()
                logging.info("IP ban check done successfully")			     

            logging.info("Update device status data.")	
            rmdItem.getDeviceStatusData()

            ##checking devices for nessessary reboot
            logging.info("Checking devices for nessessary reboot.")
            for device in list(rmdItem._rmd_data):

                if rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_proto_data']) - int(rmdItem._rmd_data[device]['current_sleep_time']) > int(rmdItem._proto_timeout) and rmdItem._rmd_data[device]['idle_status'] == 0:

                    if rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_reboot_time']) < int(rmdItem._reboot_waittime):
                        rmdItem._rmd_data[device]['reboot_nessessary'] = 'rebooting'
                        ## set led status warn if enabled
                        try:
                            if eval(rmdItem._led_enable):
                                logging.debug("Set status LED to warning for device {}".format(device))
                                rmdItem.setStatusLED(device, 'warn')
                        except:
                            logging.error("Error setting status LED for device {} ".format(device))

                    else:						
                        rmdItem._rmd_data[device]['reboot_nessessary'] = True
                        if rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_proto_data']) - int(rmdItem._rmd_data[device]['current_sleep_time']) > int(rmdItem._force_reboot_timeout) or eval(rmdItem._try_adb_first) is False: 
                            rmdItem._rmd_data[device]['reboot_force'] = True

                        ## set led status critical if enabled
                        try:
                            if eval(rmdItem._led_enable):
                                logging.debug("Set status LED to critical for device {}".format(device))
                                rmdItem.setStatusLED(device, 'crit')
                        except:
                            logging.error("Error setting status LED for device: {} ".format(device))

                else:
                    rmdItem._rmd_data[device]['reboot_nessessary'] = False
                    rmdItem._rmd_data[device]['reboot_force'] = False
                    rmdItem._rmd_data[device]['reboot_count'] = 0

                    # clear webhook_id after fixed message
                    if rmdItem._rmd_data[device]['webhook_id'] is not None:
                        rmdItem.discord_message(device, fixed=True)
                        rmdItem._rmd_data[device]['reboot_type'] = None
                        rmdItem._rmd_data[device]['reboot_forced'] = False
                        rmdItem._rmd_data[device]['webhook_id'] = None  

                    ## set led status ok if enabled
                    try:
                        if eval(rmdItem._led_enable):
                            logging.debug("Set status LED to ok for device {}".format(device))
                            rmdItem.setStatusLED(device, 'ok')
                    except:
                        logging.error("Error setting status LED for device {} ".format(device))

            if eval(rmdItem._reboot_cycle):
                ## Check for daily PowerCycle
                logging.info("Checking devices which are not rebooted within 24h.")
                if int(rmdItem._reboot_cycle_last_timestamp) < int(datetime.datetime.timestamp(datetime.datetime.now() - datetime.timedelta(minutes = int(rmdItem._reboot_cycle_wait_time)))):
                    logging.debug("Last reboot cycle was before more than 5 minutes. Marking one device for doing reboot.") 
                    dailyPowerCycleList = []
                    rmdItem._reboot_cycle_last_timestamp = int(datetime.datetime.timestamp(datetime.datetime.now()))
                    for device in list(rmdItem._rmd_data):
                        if int(rmdItem._rmd_data[device]['last_reboot_time']) < int(datetime.datetime.timestamp(datetime.datetime.now() - datetime.timedelta(hours = 24))):
                            logging.debug("Device " + device  + " not rebooted within 24h. Adding to list.")
                            dailyPowerCycleList.append(device)
                    if dailyPowerCycleList:
                        logging.debug("Device " + dailyPowerCycleList[0] + " marked for reboot because its on the list dailyPowerCycleList.")
                        rmdItem._rmd_data[dailyPowerCycleList[0]]['reboot_nessessary'] = True
                    else:
                        logging.debug("No device added to list dailyPowerCycleList.")
                else:
                    logging.debug("reboot_cycle_last_timestamp not older than configured wait time. skipping.")
                    
            ## checking for rebooted devices
            rebootedDevicedList = []
            logging.debug("Find rebooted devices for information and update discord message.")	
            logging.info("")
            logging.info("---------------------------------------------")
            logging.info("Devices are rebooted. Waiting to come online:")	
            logging.info("---------------------------------------------")
            logging.info("")

            for device in list(rmdItem._rmd_data):
                if str(rmdItem._rmd_data[device]['reboot_nessessary']) == 'rebooting': 
                    rebootedDevicedList.append({'device': device, 'worker_status': rmdItem._rmd_data[device]['worker_status'], 'last_proto_data': rmdItem.timestamp_to_readable_datetime(rmdItem._rmd_data[device]['last_proto_data']), 'offline_minutes': rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_proto_data']), 'reboot_count': rmdItem._rmd_data[device]['reboot_count'], 'last_reboot_time': rmdItem.timestamp_to_readable_datetime(rmdItem._rmd_data[device]['last_reboot_time']), 'reboot_ago_min': rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_reboot_time'])})

                    # Update no_data time and existing Discord messages
                    if rmdItem._rmd_data[device]['webhook_id'] is not None:
                            logging.info('Update Discord message')
                            rmdItem.discord_message(device)

            if not rebootedDevicedList:
                rmdItem.printTable([{'device': '-','worker_status': '-','last_proto_data': '-','offline_minutes': '-','reboot_count': '-','last_reboot_time': '-','reboot_ago_min': '-'}], ['device','worker_status','last_proto_data','offline_minutes','reboot_count','last_reboot_time','reboot_ago_min'])
                logging.info("")
            else:
                rmdItem.printTable(rebootedDevicedList, ['device','worker_status','last_proto_data','offline_minutes','reboot_count','last_reboot_time','reboot_ago_min'])
                logging.info("")						

            ##checking for bad devices
            badDevicedList = []
            logging.debug("Find bad devices and reboot them.")	
            logging.info("")
            logging.info("---------------------------------------------")
            logging.info("Devices for reboot:")	
            logging.info("---------------------------------------------")
            logging.info("")

            for device in list(rmdItem._rmd_data):
                if str(rmdItem._rmd_data[device]['reboot_nessessary']) == 'True':
                    badDevicedList.append({'device': device, 'worker_status': rmdItem._rmd_data[device]['worker_status'], 'last_proto_data': rmdItem.timestamp_to_readable_datetime(rmdItem._rmd_data[device]['last_proto_data']), 'offline_minutes': rmdItem.calc_past_min_from_now(rmdItem._rmd_data[device]['last_proto_data']), 'reboot_count': rmdItem._rmd_data[device]['reboot_count'], 'reboot_nessessary': rmdItem._rmd_data[device]['reboot_nessessary'], 'reboot_force': rmdItem._rmd_data[device]['reboot_force']})

            if not badDevicedList:
                rmdItem.printTable([{'device': '-','worker_status': '-','last_proto_data': '-','offline_minutes': '-','reboot_count': '-','reboot_nessessary': '-','reboot_force': '-'}], ['device','worker_status','last_proto_data','offline_minutes','reboot_count','reboot_nessessary','reboot_force'])
                logging.info("")
            else:
                rmdItem.printTable(badDevicedList, ['device','worker_status','last_proto_data','offline_minutes','reboot_count','reboot_nessessary','reboot_force'])
                logging.info("")

            for badDevice in badDevicedList:
                rmdItem.doRebootDevice(badDevice["device"])
                rmdItem.discord_message(badDevice["device"])

            logging.info("")
            logging.debug("End of loop and waiting configured time before continue.")			
            time.sleep(int(rmdItem._sleeptime_between_check)*60)
		
    except KeyboardInterrupt:
        logging.info("RMD will be stopped")
        exit(0)		