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

# check syntax and arguments
if (len(sys.argv) < 1 or len(sys.argv) > 2):
    print('wrong count of arguments')
    print("RebootMadDevice.py <DEVICE_ORIGIN_TO_REBOOT>")
    sys.exit(0)
DEVICE_ORIGIN_TO_REBOOT = (sys.argv[1])


# read config
def ConfigSectionMap(SECTION):
    CONFIGITEM = {}
    OPTIONS = CONFIG.options(SECTION)
    for OPTION in OPTIONS:
        try:
            CONFIGITEM[OPTION] = CONFIG.get(SECTION, OPTION)
            if CONFIGITEM[OPTION] == -1:
                DebugPrint("skip: %s" % OPTION)
        except:
            print("exception on %s!" % OPTION)
            CONFIGITEM[OPTION] = None
    return CONFIGITEM


CONFIG = configparser.ConfigParser()
CONFIG.read("configs/config.ini")
ADB_PATH = ConfigSectionMap("Enviroment")['adb_path']
ADB_PORT = ConfigSectionMap("Enviroment")['adb_port']
MITM_RECEIVER_IP = ConfigSectionMap("MAD server")['mitm_receiver_ip']
MITM_RECEIVER_PORT = ConfigSectionMap("MAD server")['mitm_receiver_port']
PowerONcmd = int(ConfigSectionMap("PowerSwitchCommands")['poweron'])
PowerOFFcmd = int(ConfigSectionMap("PowerSwitchCommands")['poweroff'])

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


def list_adb_connected_devices():
    global connectedDevices
    cmd = ADB_PATH + "/" + "adb devices | /bin/grep " + ADB_PORT
    try:
        connectedDevices = subprocess.check_output([cmd], shell=True)
        connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
            "\\n", ",").replace("\\tdevice", "").split(",")
    except subprocess.CalledProcessError:
        connectedDevices = "no devices connected"


def connect_device(DEVICE_ORIGIN_TO_REBOOT):
    cmd = ADB_PATH + "/" + "adb connect " + dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT]
    try:
        subprocess.check_output([cmd], shell=True)
    except subprocess.CalledProcessError:
        print("Connection failed")
    # Wait for 2 seconds
    time.sleep(2)


def reboot_device(DEVICE_ORIGIN_TO_REBOOT):
    cmd = ADB_PATH + "/" + "adb -s " + dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT] + ":" + ADB_PORT + " reboot"
    try:
        subprocess.check_output([cmd], shell=True)
    except subprocess.CalledProcessError:
        reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)


def reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT):
    print(PowerOFFcmd)
    time.sleep(5)
    print(PowerONcmd)


# Do reboot of device
TRY_COUNTER = 5
COUNTER = 0
while COUNTER < TRY_COUNTER:
    list_adb_connected_devices()
    if dictDEVICELIST[DEVICE_ORIGIN_TO_REBOOT] in connectedDevices:
        reboot_device(DEVICE_ORIGIN_TO_REBOOT)
        break;
    else:
        connect_device(DEVICE_ORIGIN_TO_REBOOT)
        COUNTER = COUNTER + 1
else:
    reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)

# exit
sys.exit(0)
