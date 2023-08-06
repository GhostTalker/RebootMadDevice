#!/usr/bin/env python3
#
# RebootMadDevices - ManualReboot
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2022, The GhostTalker project"
__version__ = "3.1.0"
__status__ = "TEST"

# generic/built-in and other libs
import configparser
import os
import configparser
import subprocess
import sys
import getopt
import time
import requests
import json

# check syntax and arguments
if (len(sys.argv) < 1 or len(sys.argv) > 3):
    print('ManualReboot.py -o <DEVICE_ORIGIN_TO_REBOOT>')
    print('ManualReboot.py --origin <DEVICE_ORIGIN_TO_REBOOT>')
    sys.exit(1)


def main():
    DEVICE_ORIGIN_TO_REBOOT = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:h", ["origin=", "help"])
    except getopt.GetoptError:
        print('ManualReboot.py -o <DEVICE_ORIGIN_TO_REBOOT>')
        print('ManualReboot.py --origin <DEVICE_ORIGIN_TO_REBOOT>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print('ManualReboot.py -o <DEVICE_ORIGIN_TO_REBOOT>')
            print('ManualReboot.py --origin <DEVICE_ORIGIN_TO_REBOOT>')
            sys.exit()
        elif opt in ("-o", "--origin"):
            DEVICE_ORIGIN_TO_REBOOT = arg

    return DEVICE_ORIGIN_TO_REBOOT


class rmdConfig(object):
    _config = configparser.ConfigParser()
    _rootdir = os.path.dirname(os.path.abspath('config.ini'))
    _config.read(_rootdir + "//config/config.ini")
    _gpio_usage = _config.get("GPIO", "GPIO_USAGE")
    _adb_path = _config.get("ENVIROMENT", "ADB_PATH", fallback='/usr/bin')
    _adb_port = _config.get("ENVIROMENT", "ADB_PORT", fallback='5555')
    _try_adb_first = _config.get("REBOOTOPTIONS", "TRY_ADB_FIRST", fallback='False')
    _off_on_sleep = _config.get("REBOOTOPTIONS", "OFF_ON_SLEEP", fallback=5)

    def __init__(self):
        self.initRMDdata()

    def initRMDdata(self):
        # init dict 
        self._rmd_data = {}
    
        # read json file
        logging.debug("Read data from devices.json file.")
        with open('config/devices.json') as json_file:
           _jsondata = json.load(json_file) 
    
        # init rmd data in dict
        logging.info("Init rmd data dictonary.")
        for device in _jsondata:
            self._rmd_data[device]= {'ip_address': _jsondata[device]["IP_ADDRESS"],
                                'switch_mode': _jsondata[device]["SWITCH_MODE"],
                                'switch_option': _jsondata[device]["SWITCH_OPTION"],
                                'switch_value': _jsondata[device]["SWITCH_VALUE"],
                                'led_position': _jsondata[device]["LED_POSITION"],


    def doRebootDevice(self, DEVICE_ORIGIN_TO_REBOOT):
        logging.info("Origin to reboot is: {}".format(DEVICE_ORIGIN_TO_REBOOT))
        try_counter = 2
        counter = 0
        
        if eval(self._try_adb_first):
            while counter < try_counter:
                if self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['ip_address'] in self.list_adb_connected_devices():
                    logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
                    logging.info("rebooting Device {} via ADB. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
                    return_code = self.adb_reboot(DEVICE_ORIGIN_TO_REBOOT)
                    if return_code == 0:
                        logging.info("Restart via adb of Device {} was successfull.".format(DEVICE_ORIGIN_TO_REBOOT))
                        return
                    else:
                        logging.warning("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
                        self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)                    
                        break;
                else:
                    logging.debug("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
                    self.connect_device(DEVICE_ORIGIN_TO_REBOOT)
                    counter = counter + 1

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


def create_stdout_log():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)
	

if __name__ == '__main__':
    ## init rmdConfig
    rmdConfig = rmdConfig()

    ## create logging
    create_stdout_log()
		
    # GPIO import libs
    if eval(rmdConfig._gpio_usage):
        logging.info("import GPIO libs")
        import RPi.GPIO as GPIO

    rmdConfig.doRebootDevice(DEVICE_ORIGIN_TO_REBOOT)
