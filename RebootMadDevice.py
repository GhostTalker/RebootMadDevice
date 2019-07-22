#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2019, The GhostTalker project"
__version__ = "0.1.0"
__status__ = "Dev"

# Requirements:
#        pip3 install ConfigParser
#

# generic/built-in and other libs
import sys
import subprocess
import configparser
import time
import os

# check syntax and arguments
if (len(sys.argv) < 1 or len(sys.argv) > 2):
    print('wrong count of arguments')
    print("RebootMadDevice.py <DEVICE_ORIGIN_TO_REBOOT>")
    sys.exit(0)
DEVICE_ORIGIN_TO_REBOOT = (sys.argv[1])


conf_file = os.path.join(os.path.dirname(__file__), "configs", "config.ini")
if not os.path.isfile(conf_file):
    print('"{}" does not exist'.format(conf_file))

class ConfigItem(object):
    adb_path = None
    adb_port = None
    mitm_receiver_ip = None
    mitm_receiver_port = None
    poweroff = None
    poweron = None
    devices = []

    def __init__(self, config):
        self.config = config
        self._set_data()

    def list_adb_connected_devices(self):
        global connectedDevices
        cmd =  "{}/adb devices | /bin/grep {}".format(self.adb_path, self.adb_port)
        try:
            connectedDevices = subprocess.check_output([cmd], shell=True)
            connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
                "\\n", ",").replace("\\tdevice", "").split(",")
        except subprocess.CalledProcessError:
            connectedDevices = "no devices connected"

    def connect_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = "{}/" + "adb connect {}".format(self.adb_path, dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT])
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            print("Connection failed")
        # Wait for 2 seconds
        time.sleep(2)

    def reboot_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = self.adb_path + "/" + "adb -s " + dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT] + ":" + self.adb_port + " reboot"
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            self.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)

    def reboot_device_via_power(self, DEVICE_ORIGIN_TO_REBOOT):
        print(self.poweroff)
        time.sleep(5)
        print(self.poweron)

    def _set_data(self):
        for section in self.config.sections():
            for option in self.config.options(section):
                if section == 'Devices':
                    self.devices.append(self.config.get(section, option))
                else:
                    self.__setattr__(option, self.config.get(section, option))


CONFIG = configparser.ConfigParser()
CONFIG.read(conf_file)

conf_item = ConfigItem(CONFIG)



DEVICELIST = []
actDeviceConfig = 0
while actDeviceConfig < ANZAHL_DEVICES:
    newDeviceName = "device_" + str(actDeviceConfig)
    actDevice = ConfigSectionMap("Devices")[newDeviceName]
    actDevice = actDevice.split(";", 1)
    DEVICE_ORIGIN = actDevice.pop(0)
    DEVICE_IP = actDevice.pop(0)
    newDEVICELIST = [(DEVICE_ORIGIN, DEVICE_IP)]
    DEVICELIST = DEVICELIST + newDEVICELIST
    actDeviceConfig = actDeviceConfig + 1
else:
    dictDEVICELIST = dict(DEVICELIST)





# Do reboot of device
TRY_COUNTER = 5
COUNTER = 0
while COUNTER < TRY_COUNTER:
    conf_item.list_adb_connected_devices()
    if dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT] in connectedDevices:
        conf_item.reboot_device(DEVICE_ORIGIN_TO_REBOOT)
        break;
    else:
        conf_item.connect_device(DEVICE_ORIGIN_TO_REBOOT)
        COUNTER = COUNTER + 1
else:
    conf_item.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)

# exit
sys.exit(0)
