#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2019, The GhostTalker project"
__version__ = "0.9.5"
__status__ = "Dev"

# generic/built-in and other libs
import configparser
import os
import requests
import sys
import time
import subprocess
import logging
import logging.handlers
import datetime


# Returns the directory the current script (or interpreter) is running in
def get_script_directory():
    path = os.path.realpath(sys.argv[0])
    if os.path.isdir(path):
        return path
    else:
        return os.path.dirname(path)


class MonitoringItem(object):
    mitm_receiver_ip = None
    mitm_receiver_port = None
    mitm_receiver_status_endpoint = None
    device_list = None
    devices = {}
    device_values = None
    device_last_reboot = {}
    injection_status = None
    latest_data = None
    response = None
    auth_user = None
    auth_pass = None

    def __init__(self):
        self._set_data()

    def _set_data(self):
        config = self._read_config()
        for section in config.sections():
            for option in config.options(section):
                if section == 'Devices':
                    self.devices[option] = config.get(section, option)
                else:
                    self.__setattr__(option, config.get(section, option))
        self.create_device_origin_list()

    def create_device_origin_list(self):
        device_list = []
        for device_name, device_value in self.devices.items():
            active_device = device_value.split(';', 1)
            dev_origin = active_device[0]
            device_list.append((dev_origin))
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

    def check_status_page(self, check_url, auth_user, auth_pass):
        """  Check Response Code and Output from status page """
        response = ""

        try:
            response = requests.get(check_url, auth=(auth_user, auth_pass))
            response.raise_for_status()
            if response.status_code != 200:
                print("Statuscode is {}, not 200. Retry connect to statuspage...".format(response.status_code))
                time.sleep(30)
                self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.HTTPError as errh:
            print("Http Error:", errh)
            print("Retry connect to statuspage in 10s...")
            time.sleep(10)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
            print("Retry connect to statuspage in 30s...")
            time.sleep(30)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
            print("Retry connect to statuspage in 10s...")
            time.sleep(10)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
            print("Retry connect to statuspage in 30s...")
            time.sleep(30)
            self.check_status_page(check_url, auth_user, auth_pass)

        try:
            return response.json()
        except:
            time.sleep(10)
            self.check_status_page(check_url, auth_user, auth_pass)

    def read_device_status_values(self, device_origin):
        """ Read Values for a device from MITM status page """
        check_url = "{}://{}:{}/{}/".format(self.mitm_proto, self.mitm_receiver_ip, self.mitm_receiver_port,
                                            self.mitm_receiver_status_endpoint)
        # Read Values
        json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)
        while json_respond is None:
            print("Response of status page is null. Retry in 5s...")
            time.sleep(5)
            json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)

        devices = (json_respond["origin_status"])
        device_values = (devices[device_origin])
        injection_status = (device_values["injection_status"])
        latest_data = (device_values["latest_data"])
        return injection_status, latest_data

    def check_time_since_last_data(self, device_origin):
        """ calculate time between now and latest_data """
        actual_time = time.time()
        if self.read_device_status_values(device_origin)[1] is None:
            return 99999, "unknown"
        sec_since_last_data = actual_time - self.read_device_status_values(device_origin)[1]
        min_since_last_data = sec_since_last_data / 60
        min_since_last_data = int(min_since_last_data)
        latest_data_hr = time.strftime('%Y-%m-%d %H:%M:%S',
                                       time.localtime(self.read_device_status_values(device_origin)[1]))
        return min_since_last_data, latest_data_hr

    def read_mad_status_values(self, device_origin):
        """ Read Values for a device from MITM status page """
        check_url = "{}://{}:{}/{}".format(self.madmin_proto, self.madmin_ip, self.madmin_port,
                                           self.madmin_status_endpoint)
        json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)
        while json_respond is None:
            print("Response is null. Retry in 5s...")
            time.sleep(5)
            json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)

        try:
            # Read Values
            counter = 0;
            while json_respond[counter]["origin"] != device_origin:
                counter += 1
            else:
                devices_route_manager = (json_respond[counter]["routemanager"])
                device_last_reboot = (json_respond[counter]["lastPogoReboot"])
                device_last_restart = (json_respond[counter]["lastPogoRestart"])
                device_last_proto = (json_respond[counter]["lastProtoDateTime"])
                device_route_init = (json_respond[counter]["init"])
                return devices_route_manager, device_last_reboot, device_last_restart, device_last_proto, device_route_init
        except IndexError:
            print("IndexError: list index out of range")
            print("retry to read mad status values from status page")
            self.read_mad_status_values(device_origin)

    def calc_past_min_from_now(self, timedate):
        """ calculate time between now and given timedate """
        actual_time = time.time()
        if timedate == None or timedate == "":
            return 99999
        timedate = datetime.datetime.strptime(timedate, '%Y-%m-%d %H:%M:%S').timestamp()
        past_sec_from_now = actual_time - timedate
        past_min_from_now = past_sec_from_now / 60
        past_min_from_now = int(past_min_from_now)
        return past_min_from_now

    def check_last_reboot(self, device_origin):
        last_reboot_time = self.device_last_reboot.get(device_origin, "2019-01-01 00:00:00")
        return last_reboot_time

    def set_device_reboot_time(self, device_origin):
        dateTimeObj = datetime.datetime.now()
        timestampStr = dateTimeObj.strftime('%Y-%m-%d %H:%M:%S')
        valueupdate = {device_origin: str(timestampStr)}
        self.device_last_reboot.update(valueupdate)


# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        pass


if __name__ == '__main__':
    mon_item = MonitoringItem()

    # Logging params
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.getLevelName(mon_item.log_level))
    handler = logging.handlers.TimedRotatingFileHandler(mon_item.log_filename, when="midnight", backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    logger.addHandler(handler)

    # redirect stdout and stderr to logfile
    sys.stdout = MyLogger(logger, logging.INFO)
    sys.stderr = MyLogger(logger, logging.ERROR)

    # check and reboot device if nessessary

    print(" ")
    print(" ")
    print("===================================================================")
    print("=           MAD - Check and Reboot - Daemon started               =")
    print("===================================================================")
    print(" ")

    while 1:
        device_origin_list = mon_item.create_device_origin_list()
        for device_origin in device_origin_list:
            # logging
            print("-------------------------------------------------------------------")
            print("Device:             {}".format(device_origin))
            print("Inject:             {}".format(mon_item.read_device_status_values(device_origin)[0]))
            print("Worker:             {} (Init={})".format(mon_item.read_mad_status_values(device_origin)[0],
                                                            mon_item.read_mad_status_values(device_origin)[4]))
            print("LastData:           {} ( {} minutes ago )".format(
                mon_item.check_time_since_last_data(device_origin)[1],
                mon_item.check_time_since_last_data(device_origin)[0]))
            print("LastProtoDate:      {} ( {} minutes ago )".format(mon_item.read_mad_status_values(device_origin)[3],
                                                                     mon_item.calc_past_min_from_now(
                                                                         mon_item.read_mad_status_values(device_origin)[
                                                                             3])))
            print("LastRestartByMAD:   {} ( {} minutes ago )".format(mon_item.read_mad_status_values(device_origin)[2],
                                                                     mon_item.calc_past_min_from_now(
                                                                         mon_item.read_mad_status_values(device_origin)[
                                                                             2])))
            print("LastRebootByMAD:    {} ( {} minutes ago )".format(mon_item.read_mad_status_values(device_origin)[1],
                                                                     mon_item.calc_past_min_from_now(
                                                                         mon_item.read_mad_status_values(device_origin)[
                                                                             1])))
            print("LastRebootByScript: {} ( {} minutes ago )".format(mon_item.check_last_reboot(device_origin),
                                                                     mon_item.calc_past_min_from_now(
                                                                         mon_item.check_last_reboot(device_origin))))

            # do reboot if nessessary
            if mon_item.read_device_status_values(device_origin)[0] == False and mon_item.check_time_since_last_data(
                    device_origin)[0] > int(mon_item.mitm_timeout) or mon_item.calc_past_min_from_now(
                mon_item.read_mad_status_values(device_origin)[3]) > int(mon_item.proto_timeout):
                if mon_item.calc_past_min_from_now(
                        mon_item.check_last_reboot(device_origin)) > int(mon_item.reboot_waittime):
                    print("Device {} will be rebooted now.".format(device_origin))
                    mon_item.set_device_reboot_time(device_origin)
                    if mon_item.calc_past_min_from_now(mon_item.read_mad_status_values(device_origin)[3]) > int(
                            mon_item.force_reboot_timeout):
                        cmd = "{}/RebootMadDevice.py --force --origin {}".format(get_script_directory(), device_origin)
                        try:
                            subprocess.check_output([cmd], shell=True)
                        except subprocess.CalledProcessError:
                            print("Failed to call reboot script with force option")
                    else:
                        cmd = "{}/RebootMadDevice.py --origin {}".format(get_script_directory(), device_origin)
                        try:
                            subprocess.check_output([cmd], shell=True)
                        except subprocess.CalledProcessError:
                            print("Failed to call reboot script")
                else:
                    print("Device {} was rebooted {} minutes ago. Let it time to initalize completely.".format(
                        device_origin, mon_item.calc_past_min_from_now(
                            mon_item.check_last_reboot(device_origin))))
            print()
        time.sleep(int(mon_item.sleeptime_between_check))
