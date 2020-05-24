#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2019, The GhostTalker project"
__version__ = "0.12.3"
__status__ = "Dev"

# generic/built-in and other libs
import configparser
import os
import subprocess
import sys
import getopt
import time
import requests

# check syntax and arguments
if (len(sys.argv) < 2 or len(sys.argv) > 4):
    print('RebootMadDevice.py -o <DEVICE_ORIGIN_TO_REBOOT> [-f]')
    print('RebootMadDevice.py --origin <DEVICE_ORIGIN_TO_REBOOT> [--force]')
    sys.exit(1)


def main():
    forceOption = False
    DEVICE_ORIGIN_TO_REBOOT = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:f", ["origin=", "force", "help"])
    except getopt.GetoptError:
        print('RebootMadDevice.py -o <DEVICE_ORIGIN_TO_REBOOT> [-f]')
        print('RebootMadDevice.py --origin <DEVICE_ORIGIN_TO_REBOOT> [--force]')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print('RebootMadDevice.py -o <DEVICE_ORIGIN_TO_REBOOT> [-f]')
            print('RebootMadDevice.py --origin <DEVICE_ORIGIN_TO_REBOOT> [--force]')
            sys.exit()
        elif opt in ("-o", "--origin"):
            DEVICE_ORIGIN_TO_REBOOT = arg
        elif opt in ("-f", "--force"):
            forceOption = True
    return DEVICE_ORIGIN_TO_REBOOT, forceOption


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
            return 100
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
            return 200
        elif powerswitch_dict['''switch_mode'''] == 'GPIO':
            gpioname = "gpio_{}".format(dev_nr)
            gpionr = int(powerswitch_dict[gpioname])
            print("turn GPIO PowerSwitch off")
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
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
                GPIO.output(gpionr, GPIO.LOW)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                GPIO.output(gpionr, GPIO.HIGH)
            else:
                print("wrong relay_mode in config")
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


def create_exitcode_and_exit(exitcode):
    # exit
    # EXIT Code 100 = Reboot via adb
    # EXIT Code 200 = Reboot via HTML
    # EXIT Code 300 = Reboot via GPIO
    # EXIT Code 400 = Reboot via i2c
    # EXIT Code 500 = Reboot via cmd
    # EXIT Code 600 = Reboot via PB
    # EXIT Code +50 = force Option
    if forceOption == True:
        exitcode += 50
    print(exitcode)
    sys.exit(0)


if __name__ == '__main__':
    sysparams = main()
    conf_item = ConfigItem()
    if conf_item.powerswitchcommands['switch_mode'] == 'GPIO':
        import RPi.GPIO as GPIO
    device_list = conf_item.create_device_list()
    try_counter = 2
    counter = 0
    DEVICE_ORIGIN_TO_REBOOT = sysparams[0]
    forceOption = sysparams[1]
    print('Origin to reboot is', DEVICE_ORIGIN_TO_REBOOT)
    print('Force option is', forceOption)
    if forceOption == True:
        exitcode = conf_item.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        create_exitcode_and_exit(exitcode)
    while counter < try_counter:
        if device_list[DEVICE_ORIGIN_TO_REBOOT] in conf_item.list_adb_connected_devices():
            print("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
            exitcode = conf_item.reboot_device(DEVICE_ORIGIN_TO_REBOOT)
            create_exitcode_and_exit(exitcode)
            break;
        else:
            print("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
            conf_item.connect_device(DEVICE_ORIGIN_TO_REBOOT)
            counter = counter + 1
    else:
        exitcode = conf_item.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        create_exitcode_and_exit(exitcode)
