#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2019, The GhostTalker project"
__version__ = "0.8.0"
__status__ = "Dev"

# generic/built-in and other libs
import configparser
import os
import subprocess
import sys
import time
import requests
import RPi.GPIO as GPIO

# check syntax and arguments
if (len(sys.argv) < 1 or len(sys.argv) > 2):
    print('wrong count of arguments')
    print("RebootMadDevice.py <DEVICE_ORIGIN_TO_REBOOT>")
    sys.exit(0)
DEVICE_ORIGIN_TO_REBOOT = (sys.argv[1])


class ConfigItem(object):
    adb_path = None
    adb_port = None
    mitm_receiver_ip = None
    mitm_receiver_port = None
    poweroff = None
    poweron = None
    devices = {}
    powerswitchcommands = {}
    device_list = None

    def __init__(self):
        self._set_data()

    def list_adb_connected_devices(self):
        cmd = "{}/adb devices | /bin/grep {}".format(self.adb_path, self.adb_port)
        try:
            connectedDevices = subprocess.check_output([cmd], shell=True)
            connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
                "\\n", ",").replace("\\tdevice", "").split(",")
        except subprocess.CalledProcessError:
            connectedDevices = ()
        return connectedDevices

    def connect_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = "{}/adb connect {}".format(self.adb_path, device_list[DEVICE_ORIGIN_TO_REBOOT])
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            print("Connection failed")
        # Wait for 2 seconds
        time.sleep(2)

    def reboot_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = "{}/adb -s {}:{} reboot".format(self.adb_path, device_list[DEVICE_ORIGIN_TO_REBOOT], self.adb_port)
        print("rebooting Device {}. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            print("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)

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
        elif powerswitch_dict['''switch_mode'''] == 'GPIO':
            gpioname = "gpio_{}".format(dev_nr)
            gpionr = int(powerswitch_dict[gpioname])
            print("turn GPIO PowerSwitch off")
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            if powerswitch_dict['''relay_mode'''] == 'NO':
                GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.HIGH)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.LOW)
            else:
                print("wrong relay_mode in config")
            time.sleep(10)
            print("turn GPIO PowerSwitch on")
            if powerswitch_dict['''relay_mode'''] == 'NO':
                GPIO.output(gpionr, GPIO.LOW)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                GPIO.output(gpionr, GPIO.HIGH)
            else:
                print("wrong relay_mode in config")
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

    def create_device_list(self):
        device_list = []
        for device_name, device_value in self.devices.items():
            active_device = device_value.split(';', 1)
            dev_origin = active_device[0]
            dev_ip = active_device[1]
            device_list.append((dev_origin, dev_ip))
        device_list = dict(device_list)
        return device_list

    def _check_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), "configs", "config.ini")
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


if __name__ == '__main__':
    conf_item = ConfigItem()
    device_list = conf_item.create_device_list()
    try_counter = 2
    counter = 0
    while counter < try_counter:
        if device_list[DEVICE_ORIGIN_TO_REBOOT] in conf_item.list_adb_connected_devices():
            print("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
            conf_item.reboot_device(DEVICE_ORIGIN_TO_REBOOT)
            break;
        else:
            print("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
            conf_item.connect_device(DEVICE_ORIGIN_TO_REBOOT)
            counter = counter + 1
    else:
        conf_item.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)

    # exit
    sys.exit(0)
