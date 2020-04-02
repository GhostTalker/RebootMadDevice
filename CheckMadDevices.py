#!/usr/bin/env python3
__author__ = "GhostTalker"
__copyright__ = "Copyright 2020, The GhostTalker project"
__version__ = "1.2.0"
__status__ = "Prod"

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
from discord_webhook import DiscordWebhook, DiscordEmbed
from neopixel import *


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
    strip = None

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
            response = requests.get(check_url, auth=requests.auth.HTTPBasicAuth(auth_user, auth_pass))
            response.raise_for_status()
            if response.status_code != 200:
                logging.warning(
                    "Statuscode is {}, not 200. Retry connect to statuspage...".format(response.status_code))
                time.sleep(30)
                self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.HTTPError as errh:
            logging.error("Http Error:", errh)
            logging.error("Retry connect to statuspage in 10s...")
            time.sleep(10)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.ConnectionError as errc:
            logging.error("Error Connecting:", errc)
            logging.error("Retry connect to statuspage in 30s...")
            time.sleep(30)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.Timeout as errt:
            logging.error("Timeout Error:", errt)
            logging.error("Retry connect to statuspage in 10s...")
            time.sleep(10)
            self.check_status_page(check_url, auth_user, auth_pass)
        except requests.exceptions.RequestException as err:
            logging.error("OOps: Something Else", err)
            logging.error("Retry connect to statuspage in 30s...")
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
        json_respond = self.check_status_page(check_url, self.mitm_user, self.mitm_pass)
        while json_respond is None:
            logging.warning("Response of status page is null. Retry in 5s...")
            time.sleep(5)
            json_respond = self.check_status_page(check_url, self.mitm_user, self.mitm_pass)

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
        """ Read Values for a device from MADMIN status page """
        check_url = "{}://{}:{}/{}".format(self.madmin_proto, self.madmin_ip, self.madmin_port,
                                           self.madmin_status_endpoint)
        json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)
        while json_respond is None:
            logging.warning("Response is null. Retry in 5s...")
            time.sleep(5)
            json_respond = self.check_status_page(check_url, self.madmin_user, self.madmin_pass)

        try:
            # Read Values
            counter = 0;
            while json_respond[counter]["name"] != device_origin:
                counter += 1
            else:
                devices_route_manager = (json_respond[counter]["rmname"])
                if json_respond[counter]["lastPogoReboot"] is None:
                    device_last_reboot = "2019-01-01 00:00:00"
                else:
                    device_last_reboot = datetime.datetime.fromtimestamp(
                        (json_respond[counter]["lastPogoReboot"])).strftime('%Y-%m-%d %H:%M:%S')
                if json_respond[counter]["lastPogoRestart"] is None:
                    device_last_restart = "2019-01-01 00:00:00"
                else:
                    device_last_restart = datetime.datetime.fromtimestamp(
                        (json_respond[counter]["lastPogoRestart"])).strftime('%Y-%m-%d %H:%M:%S')
                if json_respond[counter]["lastProtoDateTime"] is None:
                    device_last_proto = "2019-01-01 00:00:00"
                else:
                    device_last_proto = datetime.datetime.fromtimestamp(
                        (json_respond[counter]["lastProtoDateTime"])).strftime('%Y-%m-%d %H:%M:%S')
                device_route_init = (json_respond[counter]["init"])
                return devices_route_manager, device_last_reboot, device_last_restart, device_last_proto, device_route_init
        except IndexError:
            logging.error("IndexError: list index out of range")
            logging.error("retry to read mad status values from status page")
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

    def initiate_led(self):
        global strip
        # Create NeoPixel object with appropriate configuration.
        strip = Adafruit_NeoPixel(int(self.led_count), int(self.led_pin), int(self.led_freq_hz), int(self.led_dma),
                                  eval(self.led_invert), int(self.led_brightness))
        # Intialize the library (must be called once before other functions).
        strip.begin()
        for j in range(256 * 1):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, self.wheel_led((i + j) & 255))
            strip.show()
            time.sleep(20 / 1000.0)
        """Wipe color across display a pixel at a time."""
        for i in range(strip.numPixels()):
            strip.setPixelColorRGB(i, 0, 0, 0)
            strip.show()
            time.sleep(50 / 1000.0)

    def wheel_led(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    def setStatusLED(self, device_origin, alertColor, mode):
        # get device number
        for key, value in self.devices.items():
            dev_origin = value.split(';', 1)
            if dev_origin[0] == device_origin:
                dev_nr = key.replace("device_", "")
                break
        # define color values
        if alertColor == "crit":
            rLED = 255
            gLED = 0
            bLED = 0
        elif alertColor == "warn":
            rLED = 255
            gLED = 150
            bLED = 0
        elif alertColor == "ok":
            rLED = 0
            gLED = 255
            bLED = 0
        # execute to led strip
        strip.setPixelColorRGB(int(dev_nr) - 1, int(gLED), int(rLED), int(bLED))
        strip.show()


def create_timed_rotating_log(log_file):
    logging.basicConfig(filename=log_file, filemode='a', format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(mon_item.log_level))
    logger = logging.getLogger(__name__)
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=3)
    logger.addHandler(file_handler)


def create_stdout_log():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(mon_item.log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)


def create_webhook(web_hook_url, device_origin, script_output):
    # decode returncode for information

    script_output = str(script_output).replace("b'", "").replace("\\n'", "")
    script_output_len = len(script_output)
    returncode = script_output[script_output_len - 3:script_output_len]

    # EXIT Code 100 = Reboot via adb
    # EXIT Code 200 = Reboot via HTML
    # EXIT Code 300 = Reboot via GPIO
    # EXIT Code 400 = Reboot via i2c
    # EXIT Code 500 = Reboot via cmd
    # EXIT Code +50 = force Option
    if returncode == '100':
        reboot_type = 'ADB'
        force_option = 'no'
    elif returncode == '200':
        reboot_type = 'HTML'
        force_option = 'no'
    elif returncode == '250':
        reboot_type = 'HTML'
        force_option = 'yes'
    elif returncode == '300':
        reboot_type = 'GPIO'
        force_option = 'no'
    elif returncode == '350':
        reboot_type = 'HTML'
        force_option = 'yes'
    elif returncode == '400':
        reboot_type = 'I2C'
        force_option = 'no'
    elif returncode == '450':
        reboot_type = 'I2C'
        force_option = 'yes'
    elif returncode == '500':
        reboot_type = 'CMD'
        force_option = 'no'
    elif returncode == '550':
        reboot_type = 'CMD'
        force_option = 'yes'

    # create embed object for webhook
    webhook = DiscordWebhook(url=web_hook_url)
    embed = DiscordEmbed(description='Device Reboot executed', color=242424)
    embed.set_author(name='RebootMadDevice', url='https://github.com/GhostTalker',
                     icon_url='https://avatars2.githubusercontent.com/u/49254289')
    embed.set_footer(text='')
    embed.set_timestamp()
    embed.add_embed_field(name='Device', value=device_origin)
    embed.add_embed_field(name='Reboot', value=reboot_type)
    embed.add_embed_field(name='Force', value=force_option)
    # add embed object to webhook
    webhook.add_embed(embed)
    webhook.execute()


if __name__ == '__main__':
    mon_item = MonitoringItem()

    # Logging Options
    if mon_item.log_console_only == "True":
        create_stdout_log()
    else:
        create_timed_rotating_log(mon_item.log_filename)

    # LED
    if mon_item.led_enable == "True":
        mon_item.initiate_led()

    # check and reboot device if nessessary

    logging.info(" ")
    logging.info(" ")
    logging.info("===================================================================")
    logging.info("=           MAD - Check and Reboot - Daemon started               =")
    logging.info("===================================================================")
    logging.info(" ")

    try:
        while 1:
            device_origin_list = mon_item.create_device_origin_list()
            for device_origin in device_origin_list:
                # logging
                logging.info("-------------------------------------------------------------------")
                logging.info("Device:             {}".format(device_origin))
                logging.info("Inject:             {}".format(mon_item.read_device_status_values(device_origin)[0]))
                logging.info(
                    "Worker:             {} (Init={})".format(mon_item.read_mad_status_values(device_origin)[0],
                                                              mon_item.read_mad_status_values(device_origin)[4]))
                logging.info("LastData:           {} ( {} minutes ago )".format(
                    mon_item.check_time_since_last_data(device_origin)[1],
                    mon_item.check_time_since_last_data(device_origin)[0]))
                logging.info(
                    "LastProtoDate:      {} ( {} minutes ago )".format(
                        mon_item.read_mad_status_values(device_origin)[3],
                        mon_item.calc_past_min_from_now(
                            mon_item.read_mad_status_values(device_origin)[
                                3])))
                logging.info(
                    "LastRestartByMAD:   {} ( {} minutes ago )".format(
                        mon_item.read_mad_status_values(device_origin)[2],
                        mon_item.calc_past_min_from_now(
                            mon_item.read_mad_status_values(device_origin)[
                                2])))
                logging.info(
                    "LastRebootByMAD:    {} ( {} minutes ago )".format(
                        mon_item.read_mad_status_values(device_origin)[1],
                        mon_item.calc_past_min_from_now(
                            mon_item.read_mad_status_values(device_origin)[
                                1])))
                logging.info(
                    "LastRebootByScript: {} ( {} minutes ago )".format(mon_item.check_last_reboot(device_origin),
                                                                       mon_item.calc_past_min_from_now(
                                                                           mon_item.check_last_reboot(
                                                                               device_origin))))

                # do reboot if nessessary
                if mon_item.read_device_status_values(device_origin)[0] == False and \
                        mon_item.check_time_since_last_data(
                                device_origin)[0] > int(mon_item.mitm_timeout) or mon_item.calc_past_min_from_now(
                    mon_item.read_mad_status_values(device_origin)[3]) > int(mon_item.proto_timeout):
                    if mon_item.calc_past_min_from_now(
                            mon_item.check_last_reboot(device_origin)) > int(mon_item.reboot_waittime):
                        logging.warning("Device {} will be rebooted now.".format(device_origin))
                        mon_item.set_device_reboot_time(device_origin)
                        alertColor = "crit"
                        if mon_item.calc_past_min_from_now(mon_item.read_mad_status_values(device_origin)[3]) > int(
                                mon_item.force_reboot_timeout):
                            cmd = "{}/RebootMadDevice.py --force --origin {}".format(get_script_directory(),
                                                                                     device_origin)
                            logging.critical("Force option will be used.")
                            try:
                                script_output = subprocess.check_output([cmd], shell=True, timeout=120)
                                if mon_item.webhook_enable == "True":
                                    create_webhook(mon_item.webhookurl, device_origin, script_output)
                            except subprocess.CalledProcessError:
                                logging.error("Failed to call reboot script with force option")
                            except subprocess.TimeoutExpired:
                                logging.error("Reboot-script runs in timeout.")
                        else:
                            cmd = "{}/RebootMadDevice.py --origin {}".format(get_script_directory(), device_origin)
                            try:
                                script_output = subprocess.check_output([cmd], shell=True, timeout=120)
                                if mon_item.webhook_enable == "True":
                                    create_webhook(mon_item.webhookurl, device_origin, script_output)
                            except subprocess.CalledProcessError:
                                logging.error("Failed to call reboot script")
                            except subprocess.TimeoutExpired:
                                logging.error("Reboot-script runs in timeout.")
                    else:
                        logging.warning(
                            "Device {} was rebooted {} minutes ago. Let it time to initalize completely.".format(
                                device_origin, mon_item.calc_past_min_from_now(
                                    mon_item.check_last_reboot(device_origin))))
                        alertColor = "warn"
                else:
                    alertColor = "ok"

                if mon_item.led_enable == "True":
                    mode = 1
                    mon_item.setStatusLED(device_origin, alertColor, mode)

                print("")
            time.sleep(int(mon_item.sleeptime_between_check))

    except KeyboardInterrupt:
        print("Script will be stopped")
        if mon_item.led_enable == "True":
            mon_item.initiate_led()
        exit(0)