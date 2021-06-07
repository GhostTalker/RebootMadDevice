#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2019, The GhostTalker project"
__version__ = "2.2.3"
__status__ = "Prod"

# generic/built-in and other libs
import configparser
import os
import subprocess
import sys
import getopt
import time
import requests

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


class ConfigItem(object):
    adb_path = None
    adb_port = None
    mitm_receiver_ip = None
    mitm_receiver_port = None
    poweroff = None
    poweron = None
    devices = {}
    powerswitchcommands = {}

    def __init__(self):
        self._set_data()

    def reboot_device_via_power(self, DEVICE_ORIGIN_TO_REBOOT):
        dev_nr = ""
        powerswitch_dict = dict(self.powerswitchcommands.items())

        for key, value in self.devices.items():
            dev_origin = value.split(';', 1)
            if dev_origin[0] == DEVICE_ORIGIN_TO_REBOOT:
                dev_nr = key
                break

        if powerswitch_dict['''switch_mode'''] == 'HTML':
            poweron = "poweron_{}".format(dev_nr)
            poweroff = "poweroff_{}".format(dev_nr)
            print("turn HTTP PowerSwitch off")
            requests.get(powerswitch_dict[poweroff])
            time.sleep(5)
            print("turn HTTP PowerSwitch on")
            requests.get(powerswitch_dict[poweron])
            return 200
        elif powerswitch_dict['''switch_mode'''] == 'GPIO':
            gpioname = "gpio_{}".format(dev_nr)
            gpionr = int(powerswitch_dict[gpioname])
            print("turn GPIO PowerSwitch off")
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            try:
                powerswitch_dict['''cleanup_mode''']
            except KeyError:
                powerswitch_dict.update({'''cleanup_mode''' : 'no'})

            if powerswitch_dict['''cleanup_mode'''] == 'yes':
                GPIO.cleanup()
                print("CleanupParameter: " + powerswitch_dict['''cleanup_mode'''])
                print("Cleanup done!")

            if powerswitch_dict['''relay_mode'''] == 'NO':
                #GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.HIGH)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.HIGH)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                #GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.LOW)
            else:
                print("wrong relay_mode in config")
            time.sleep(10)
            print("turn GPIO PowerSwitch on")
            if powerswitch_dict['''relay_mode'''] == 'NO':
                #GPIO.output(gpionr, GPIO.LOW)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.LOW)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                #GPIO.output(gpionr, GPIO.HIGH)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.HIGH)
            else:
                print("wrong relay_mode in config")

            if powerswitch_dict['''cleanup_mode'''] == 'yes':
                GPIO.cleanup()
                print("CleanupParameter: " + powerswitch_dict['''cleanup_mode'''])
                print("Cleanup done!")
            return 300
        elif powerswitch_dict['''switch_mode'''] == 'CMD':
            poweron = "poweron_{}".format(dev_nr)
            poweroff = "poweroff_{}".format(dev_nr)
            print("fire command for PowerSwitch off")
            try:
                subprocess.check_output([powerswitch_dict[poweroff]], shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire command")
            time.sleep(5)
            print("fire command for PowerSwitch on")
            try:
                subprocess.check_output([powerswitch_dict[poweron]], shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire command")
            return 500
        elif powerswitch_dict['''switch_mode'''] == 'PB':
            pbport = "pb_{}".format(dev_nr)
            pbporton = '/bin/echo -e "on {}" > {}'.format(powerswitch_dict[pbport],powerswitch_dict['pb_interface'])
            pbportoff = '/bin/echo -e "off {}" > {}'.format(powerswitch_dict[pbport],powerswitch_dict['pb_interface'])
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
            return 600
        elif powerswitch_dict['''switch_mode'''] == 'POE':
            poescript = "poe_{}".format(dev_nr)
            print("fire command for POE port reset")
            try:
                subprocess.check_output([powerswitch_dict[poescript]], shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire command")
            return 700
        elif powerswitch_dict['''switch_mode'''] == 'SNMP':
            switchport = "snmp_{}".format(dev_nr)
            snmpporton = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 1'.format(powerswitch_dict['snmp_community_string'], powerswitch_dict['snmp_switch_ip_adress'], powerswitch_dict[switchport])
            snmpportoff = 'snmpset -v 2c -c {} {} 1.3.6.1.2.1.105.1.1.1.3.1.{} i 2'.format(powerswitch_dict['snmp_community_string'], powerswitch_dict['snmp_switch_ip_adress'], powerswitch_dict[switchport])
            try:
                subprocess.check_output(snmpportoff, shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire SNMP command")
            print("send SNMP command port OFF to SWITCH")
            time.sleep(5)
            try:
                subprocess.check_output(snmpporton, shell=True)
            except subprocess.CalledProcessError:
                print("failed to fire SNMP command")
            print("send SNMP command port ON to SWITCH")
            return 800
        else:
            print("no PowerSwitch configured. Do it manually!!!")

    def _set_data(self):
        config = self._read_config()
        for section in config.sections():
            for option in config.options(section):
                if section == 'Devices':
                    self.devices[option] = config.get(section, option)
                elif section == 'PowerSwitchCommands':
                    self.powerswitchcommands[option] = config.get(section, option)
                else:
                    self.__setattr__(option, config.get(section, option))

    def _check_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), "config.ini")
        if not os.path.isfile(conf_file):
            raise FileExistsError('"{}" does not exist'.format(conf_file))
        self.conf_file = conf_file

    def _read_config(self):
        try:
            self._check_config()
        except FileExistsError as e:
            raise e
        config = configparser.ConfigParser()
        config.read(self.conf_file)

        return config


def create_exitcode_and_exit(exitcode):
    if exitcode == 200:
        print("EXIT Code 250 = Reboot via HTML")
    elif exitcode == 300:
        print("EXIT Code 350 = Reboot via GPIO")
    elif exitcode == 400:
        print("EXIT Code 450 = Reboot via i2c")
    elif exitcode == 500:
        print("EXIT Code 550 = Reboot via cmd")
    elif exitcode == 600:
        print("EXIT Code 650 = Reboot via PB")
    elif exitcode == 700:
        print("EXIT Code 650 = Reboot via POE")
    elif exitcode == 800:
        print("EXIT Code 650 = Reboot via SNMP")
    sys.exit(0)


if __name__ == '__main__':
    conf_item = ConfigItem()
    if conf_item.powerswitchcommands['switch_mode'] == 'GPIO':
        import RPi.GPIO as GPIO

    DEVICE_ORIGIN_TO_REBOOT = main() 
    print('Origin to reboot is', DEVICE_ORIGIN_TO_REBOOT)

    exitcode = conf_item.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
    create_exitcode_and_exit(exitcode)

