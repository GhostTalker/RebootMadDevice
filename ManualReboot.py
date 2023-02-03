#!/usr/bin/env python3
#
# RebootMadDevices - ManualReboot
# Script to restart ATV devices which are not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2022, The GhostTalker project"
__version__ = "3.0.2"
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


class rmdItem(object):
    _config = configparser.ConfigParser()
    _rootdir = os.path.dirname(os.path.abspath('config.ini'))
    _config.read(_rootdir + "/config.ini")
    _gpio_usage = _config.get("GPIO", "GPIO_USAGE")


    def __init__(self):
        self.initRMDdata()

    def initRMDdata(self):
        # init dict 
        self._rmd_data = {}
    
        # read json file
        print("Read data from devices.json file.")
        with open('devices.json') as json_file:
           _jsondata = json.load(json_file) 
    
        # init rmd data in dict
        print("Init rmd data dictonary.")
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
                                'last_reboot_time': "",
                                'reboot_count': "0",
                                'reboot_nessessary': False,
                                'reboot_force': False,
                                'reboot_type': None,
                                'reboot_forced': False,
                                'webhook_id': None}
    	

    def reboot_device_via_power(self, DEVICE_ORIGIN_TO_REBOOT):
        ## read powerSwitch config
        powerSwitchMode = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_mode']
        powerSwitchOption = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_option']
        powerSwitchValue = self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['switch_value']

        ## HTML 
        if powerSwitchMode == 'HTML':
            print("PowerSwitch with HTML starting.")
            poweron = powerSwitchValue.split(";")[0]
            poweroff = powerSwitchValue.split(";")[1]
            print("turn HTTP PowerSwitch off")
            requests.get(poweroff)
            time.sleep(5)
            print("turn HTTP PowerSwitch on")
            requests.get(poweron)
            print("PowerSwitch with HTML done.")
            return        

        ## GPIO 
        elif powerSwitchMode == 'GPIO':
            print("PowerSwitch with GPIO starting.")
            relay_mode = powerSwitchOption.split(";")[0]
            cleanup_mode = powerSwitchOption.split(";")[1]
            gpionr = int(powerSwitchValue)
            print("turn GPIO PowerSwitch off")
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            try:
               eval(cleanup_mode)
            except:
               cleanup_mode = "False"
            
            if eval(cleanup_mode):
                GPIO.cleanup()
                print("GPIO cleanup done!")

            if relay_mode == 'NO':
                print("Relay_mode: " + relay_mode)
                # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.HIGH)
                print("setting GPIO setup to: GPIO.OUT")
                GPIO.setup(gpionr, GPIO.OUT)
                print("setting GPIO output to: GPIO.HIGH")
                GPIO.output(gpionr, GPIO.HIGH)
            elif relay_mode == 'NC':
                print("Relay_mode: " + relay_mode)
                # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.LOW)
                print("setting GPIO setup to: GPIO.OUT")
                GPIO.setup(gpionr, GPIO.OUT)
                print("setting GPIO output to: GPIO.LOW")
                GPIO.output(gpionr, GPIO.LOW)
            else:
                print("wrong relay_mode in config")
            print("sleeping 10s")
            time.sleep(10)
            print("turn GPIO PowerSwitch on")
            if relay_mode == 'NO':
                print("Relay_mode: " + relay_mode)
                # GPIO.output(gpionr, GPIO.LOW)
                print("setting GPIO setup to: GPIO.OUT")
                GPIO.setup(gpionr, GPIO.OUT)
                print("setting GPIO output to: GPIO.LOW")
                GPIO.output(gpionr, GPIO.LOW)
            elif relay_mode == 'NC':
                print("Relay_mode: " + relay_mode)
                # GPIO.output(gpionr, GPIO.HIGH)
                print("setting GPIO setup to: GPIO.OUT")
                GPIO.setup(gpionr, GPIO.OUT)
                print("setting GPIO output to: GPIO.HIGH")
                GPIO.output(gpionr, GPIO.HIGH)
            else:
                print("wrong relay_mode in config")

            if eval(cleanup_mode):
                GPIO.cleanup()
                print("GPIO cleanup done!")
            print("PowerSwitch with GPIO done.")
            return

        ## CMD 
        elif powerSwitchMode == 'CMD':
            print("PowerSwitch with CMD starting.")
            try:
                subprocess.check_output(powerSwitchValue, shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire command")
            time.sleep(5)
            print("PowerSwitch with CMD done.")
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_forced'] = True
            self._rmd_data[DEVICE_ORIGIN_TO_REBOOT]['reboot_type'] = "CMD"
            return

        ## SCRIPT 
        elif powerSwitchMode == 'SCRIPT':
            print("PowerSwitch with SCRIPT starting.")
            poweron = powerSwitchValue.split(";")[0]
            poweroff = powerSwitchValue.split(";")[1]
            print("execute script for PowerSwitch off")
            try:
                subprocess.check_output(poweroff, shell=True)
            except subprocess.CalledProcessError:
                print("failed to start script")
            time.sleep(5)
            print("execute script for PowerSwitch on")
            try:
                subprocess.check_output(poweron, shell=True)
            except subprocess.CalledProcessError:
                print("failed to start script")
            print("PowerSwitch with SCRIPT done.")
            return

        ## POE 
        elif powerSwitchMode == 'POE':
            print("PowerSwitch with POE starting.")
            try:
                subprocess.check_output(powerSwitchValue, shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire poe port reset")
            time.sleep(5)
            print("PowerSwitch with POE done.")
            return

        ## PB
        elif powerSwitchMode == 'PB':
            print("PowerSwitch with PB starting.")
            pbport = powerSwitchValue
            pb_interface = powerSwitchOption
            pbporton = '/bin/echo -e "on {}" > {}'.format(pbport, pb_interface)
            pbportoff = '/bin/echo -e "off {}" > {}'.format(pbport, pb_interface)
            print("send command to PowerBoard for PowerSwitch off")
            try:
                subprocess.check_output(pbportoff, shell=True)
            except subprocess.CalledProcessError:
                print("failed send command to PowerBoard")
            time.sleep(5)
            print("send command to Powerboard for PowerSwitch on")
            try:
                subprocess.check_output(pbporton, shell=True)
            except subprocess.CalledProcessError:
                print("failed send command to PowerBoard")
            print("PowerSwitch with PB done.")
            return
			
        ## SNMP
        elif powerSwitchMode == 'SNMP':
            print("PowerSwitch with SNMP starting.")
            switchport = powerSwitchValue
            snmp_switch_ip_adress = powerSwitchOption.split(";")[0]
            snmp_community_string = powerSwitchOption.split(";")[1]
            snmpporton = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 1'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            snmpportoff = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 2'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            try:
                subprocess.check_output(snmpportoff, shell=True)
                print("send SNMP command port OFF to SWITCH")
            except subprocess.CalledProcessError:
                print("failed to fire SNMP command")
            time.sleep(5)
            try:
                subprocess.check_output(snmpporton, shell=True)
                print("send SNMP command port ON to SWITCH")
            except subprocess.CalledProcessError:
                print("failed to fire SNMP command")
            print("PowerSwitch with SNMP done.")
            return
        else:
            logging.warning("no PowerSwitch configured. Do it manually!!!")


if __name__ == '__main__':
    ## init rmdItem
    rmdItem = rmdItem()
		
    # GPIO import libs
    if eval(rmdItem._gpio_usage):
        print("import GPIO libs")
        import RPi.GPIO as GPIO

    print('Origin to reboot is', DEVICE_ORIGIN_TO_REBOOT)
    rmdItem.doRebootDevice(DEVICE_ORIGIN_TO_REBOOT)
    


