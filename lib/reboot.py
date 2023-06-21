#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# reboot class
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "1.0.0"
__status__ = "TEST"

# generic/built-in and other libs
import os
import sys
import time
import subprocess
import requests

class reboot:
    def __init__(self):
        print()

    def restart_mapper_sw(self, adbloc, adbport, IP, rootdir, mapper_mode):
        self._adbloc = "{}/adb".format(adbloc)
        self._deviceloc = "{}:{}".format(IP, adbport)
        self._mapperscript = "{}/mapperscripts/restart{}.sh".format(rootdir, mapper_mode)
        try:
            subprocess.Popen([self._mapperscript, self._adbloc, self._deviceloc])
            return 0
        except:
            return 1
		 

    def adb_reboot(self, adbloc, adbport, IP):
        self._adbloc = "{}/adb".format(adbloc)
        self._deviceloc = "{}:{}".format(IP, adbport)
        try:
            subprocess.Popen([adbloc, '-s', DEVICELOC, 'reboot'])
            return 0
        except:
            return 1


    def reboot_device_via_power(self, powerSwitchMode, powerSwitchOption, powerSwitchValue):
        ## read powerSwitch config
        self._powerSwitchMode = powerSwitchMode
        self._powerSwitchOption = powerSwitchOption
        self._powerSwitchValue = powerSwitchValue

        ## HTML 
        if self._powerSwitchMode == 'HTML':
            print("PowerSwitch with HTML starting.")
            poweron = self._powerSwitchValue.split(";")[0]
            poweroff = self._powerSwitchValue.split(";")[1]
            print("turn HTTP PowerSwitch off")
            requests.get(poweroff)
            time.sleep(int(self._off_on_sleep))
            print("turn HTTP PowerSwitch on")
            requests.get(poweron)
            print("PowerSwitch with HTML done.")
            return        

        ## GPIO 
        elif self._powerSwitchMode == 'GPIO':
            import RPi.GPIO as GPIO
            print("PowerSwitch with GPIO starting.")
            relay_mode = self._powerSwitchOption.split(";")[0]
            cleanup_mode = self._powerSwitchOption.split(";")[1]
            gpionr = int(self._powerSwitchValue)
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
                logging.error("wrong relay_mode in config")
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
                logging.error("wrong relay_mode in config")

            if eval(cleanup_mode):
                GPIO.cleanup()
                print("GPIO cleanup done!")
            print("PowerSwitch with GPIO done.")
            return

        ## CMD 
        elif self._powerSwitchMode == 'CMD':
            print("PowerSwitch with CMD starting.")
            try:
                subprocess.check_output(self._powerSwitchValue, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire command")
            time.sleep(int(self._off_on_sleep))
            print("PowerSwitch with CMD done.")
            return

        ## SCRIPT 
        elif self._powerSwitchMode == 'SCRIPT':
            print("PowerSwitch with SCRIPT starting.")
            poweron = self._powerSwitchValue.split(";")[0]
            poweroff = self._powerSwitchValue.split(";")[1]
            print("execute script for PowerSwitch off")
            try:
                subprocess.check_output(poweroff, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to start script")
            time.sleep(int(self._off_on_sleep))
            print("execute script for PowerSwitch on")
            try:
                subprocess.check_output(poweron, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to start script")
            print("PowerSwitch with SCRIPT done.")
            return

        ## POE 
        elif self._powerSwitchMode == 'POE':
            print("PowerSwitch with POE starting.")
            try:
                subprocess.check_output(self._powerSwitchValue, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire poe port reset")
            time.sleep(int(self._off_on_sleep))
            print("PowerSwitch with POE done.")
            return

        ## PB
        elif self._powerSwitchMode == 'PB':
            print("PowerSwitch with PB starting.")
            pbport = self._powerSwitchValue
            pb_interface = self._powerSwitchOption
            pbporton = '/bin/echo -e "on {}" > {}'.format(pbport, pb_interface)
            pbportoff = '/bin/echo -e "off {}" > {}'.format(pbport, pb_interface)
            print("send command to PowerBoard for PowerSwitch off")
            try:
                subprocess.check_output(pbportoff, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            time.sleep(int(self._off_on_sleep))
            print("send command to Powerboard for PowerSwitch on")
            try:
                subprocess.check_output(pbporton, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            print("PowerSwitch with PB done.")
            return
			
        ## SNMP
        elif self._powerSwitchMode == 'SNMP':
            print("PowerSwitch with SNMP starting.")
            switchport = self._powerSwitchValue
            snmp_switch_ip_adress = self._powerSwitchOption.split(";")[0]
            snmp_community_string = self._powerSwitchOption.split(";")[1]
            snmpporton = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 1'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            snmpportoff = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 2'.format(snmp_community_string, snmp_switch_ip_adress, switchport)
            try:
                subprocess.check_output(snmpportoff, shell=True)
                print("send SNMP command port OFF to SWITCH")
            except subprocess.CalledProcessError:
                logging.error("failed to fire SNMP command")
            time.sleep(int(self._off_on_sleep))
            try:
                subprocess.check_output(snmpporton, shell=True)
                print("send SNMP command port ON to SWITCH")
            except subprocess.CalledProcessError:
                logging.error("failed to fire SNMP command")
            print("PowerSwitch with SNMP done.")
            return
        else:
            logging.warning("no PowerSwitch configured. Do it manually!!!")
