#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# adb_tools class
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "1.0.0"
__status__ = "TEST"

import time
import subprocess

class adb_tools:
    def __init__(self):
        print()
 
    def list_adb_connected_devices(self, adb_path, adb_port):
        self._adb_path = adb_path
        self._adb_port = adb_port

        cmd = "{}/adb devices | /bin/grep {}".format(self._adb_path, self._adb_port)
        try:
            connectedDevices = subprocess.check_output([cmd], shell=True)
            connectedDevices = str(connectedDevices).replace("b'", "").replace("\\n'", "").replace(":5555", "").replace(
                "\\n", ",").replace("\\tdevice", "").split(",")
        except subprocess.CalledProcessError:
            connectedDevices = ()
        return connectedDevices


    def connect_device(self,  adb_path, ip_address):
        self._adb_path = adb_path
        self._ip_adress = ip_address

        cmd = "{}/adb connect {}".format(self._adb_path, self._ip_address)
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            logging.info("Connection via adb failed")
        # Wait for 2 seconds
        time.sleep(2)
