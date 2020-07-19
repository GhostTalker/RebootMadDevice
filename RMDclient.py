#!/usr/bin/env python3
# MAD Plugin - RebootMadDevices
# RMD Client
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2020, The GhostTalker project"
__version__ = "2.0.12"
__status__ = "PROD"

# generic/built-in and other libs
import configparser
import os
import sys
import subprocess
import time
import requests
import socket
import pickle
import logging
import logging.handlers


class rmdItem(object):
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
            logging.info("Connection via adb failed")
        # Wait for 2 seconds
        time.sleep(2)

    def reboot_device(self, DEVICE_ORIGIN_TO_REBOOT):
        cmd = "{}/adb -s {}:{} reboot".format(self.adb_path, device_list[DEVICE_ORIGIN_TO_REBOOT], self.adb_port)
        logging.info("rebooting Device {}. Please wait".format(DEVICE_ORIGIN_TO_REBOOT))
        try:
            subprocess.check_output([cmd], shell=True)
            return 100
        except subprocess.CalledProcessError:
            logging.warning("rebooting Device {} via ADB not possible. Using PowerSwitch...".format(DEVICE_ORIGIN_TO_REBOOT))
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
            logging.info("turn HTTP PowerSwitch off")
            requests.get(powerswitch_dict[poweroff])
            time.sleep(5)
            logging.info("turn HTTP PowerSwitch on")
            requests.get(powerswitch_dict[poweron])
            return 200
        elif powerswitch_dict['''switch_mode'''] == 'GPIO':
            gpioname = "gpio_{}".format(dev_nr)
            gpionr = int(powerswitch_dict[gpioname])
            logging.info("turn GPIO PowerSwitch off")
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            try:
                powerswitch_dict['''cleanup_mode''']
            except KeyError:
                powerswitch_dict.update({'''cleanup_mode''': 'no'})

            if powerswitch_dict['''cleanup_mode'''] == 'yes':
                GPIO.cleanup()
                logging.info("CleanupParameter: " + powerswitch_dict['''cleanup_mode'''])
                logging.info("Cleanup done!")

            if powerswitch_dict['''relay_mode'''] == 'NO':
                # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.HIGH)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.HIGH)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                # GPIO.setup(gpionr, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.LOW)
            else:
                logging.error("wrong relay_mode in config")
            time.sleep(10)
            logging.info("turn GPIO PowerSwitch on")
            if powerswitch_dict['''relay_mode'''] == 'NO':
                # GPIO.output(gpionr, GPIO.LOW)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.LOW)
            elif powerswitch_dict['''relay_mode'''] == 'NC':
                # GPIO.output(gpionr, GPIO.HIGH)
                GPIO.setup(gpionr, GPIO.OUT)
                GPIO.output(gpionr, GPIO.HIGH)
            else:
                logging.error("wrong relay_mode in config")

            if powerswitch_dict['''cleanup_mode'''] == 'yes':
                GPIO.cleanup()
                logging.info("CleanupParameter: " + powerswitch_dict['''cleanup_mode'''])
                logging.info("Cleanup done!")
            return 300
        elif powerswitch_dict['''switch_mode'''] == 'CMD':
            poweron = "poweron_{}".format(dev_nr)
            poweroff = "poweroff_{}".format(dev_nr)
            logging.info("fire command for PowerSwitch off")
            try:
                subprocess.check_output([powerswitch_dict[poweroff]], shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire command")
            time.sleep(5)
            logging.info("fire command for PowerSwitch on")
            try:
                subprocess.check_output([powerswitch_dict[poweron]], shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed to fire command")
            return 500
        elif powerswitch_dict['''switch_mode'''] == 'PB':
            pbport = "pb_{}".format(dev_nr)
            pbporton = '/bin/echo -e "on {}" > {}'.format(powerswitch_dict[pbport], powerswitch_dict['pb_interface'])
            pbportoff = '/bin/echo -e "off {}" > {}'.format(powerswitch_dict[pbport], powerswitch_dict['pb_interface'])
            logging.info("send command to PowerBoard for PowerSwitch off")
            try:
                subprocess.check_output(pbportoff, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            time.sleep(5)
            logging.info("send command to Powerboard for PowerSwitch on")
            try:
                subprocess.check_output(pbporton, shell=True)
            except subprocess.CalledProcessError:
                logging.error("failed send command to PowerBoard")
            return 600
        else:
            logging.warning("no PowerSwitch configured. Do it manually!!!")

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

    def setStatusLED(self, device_origin, alertColor):
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
            gLED = 255
            bLED = 0
        elif alertColor == "ok":
            rLED = 0
            gLED = 255
            bLED = 0

        if rmdItem.led_type == "internal":
            # execute to led strip
            logging.debug("LED alertlvl: " + str(alertColor))
            logging.debug("LED Colors: " + str(rLED) + ", " + str(gLED) + ", " + str(bLED))
            strip.setPixelColorRGB(int(dev_nr) - 1, int(rLED), int(gLED), int(bLED))
            strip.show()
        elif rmdItem.led_type == "external":
            websocket.enableTrace(False)
            ws = create_connection(rmdItem.led_ws_external)  # open socket
            hexcolor = webcolors.rgb_to_hex((rLED, gLED, bLED)).replace("#", "")
            led_number = '%0.4d' % (int(dev_nr) - 1)
            payload = "!{} {}".format(led_number, hexcolor)
            ws.send(payload)  # send to websocket
            ws.close()  # close websocket

def create_timed_rotating_log(log_file):
    logging.basicConfig(filename=log_file, filemode='a', format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(rmdItem.log_level))
    logger = logging.getLogger(__name__)
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=3)
    logger.addHandler(file_handler)

def create_stdout_log():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(rmdItem.log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)

def doRebootDevice(DEVICE_ORIGIN_TO_REBOOT, FORCE_OPTION):
    # EXIT Code 100 = Reboot via adb
    # EXIT Code 200 = Reboot via HTML
    # EXIT Code 300 = Reboot via GPIO
    # EXIT Code 400 = Reboot via i2c
    # EXIT Code 500 = Reboot via cmd
    # EXIT Code 600 = Reboot via PB
    # EXIT Code +50 = force Option
    try_counter = 2
    counter = 0
    logging.info("Origin to reboot is: {}".format(DEVICE_ORIGIN_TO_REBOOT))
    logging.info("Force option is: {}".format(FORCE_OPTION))
    if FORCE_OPTION == 'yes':
        rebootcode = rmdItem.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        rebootcode += 50
        return rebootcode
    while counter < try_counter:
        if device_list[DEVICE_ORIGIN_TO_REBOOT] in rmdItem.list_adb_connected_devices():
            logging.debug("Device {} already connected".format(DEVICE_ORIGIN_TO_REBOOT))
            rebootcode = rmdItem.reboot_device(DEVICE_ORIGIN_TO_REBOOT)
            return rebootcode
            break;
        else:
            logging.debug("Device {} not connected".format(DEVICE_ORIGIN_TO_REBOOT))
            rmdItem.connect_device(DEVICE_ORIGIN_TO_REBOOT)
            counter = counter + 1
    else:
        rebootcode = rmdItem.reboot_device_via_power(DEVICE_ORIGIN_TO_REBOOT)
        return rebootcode

if __name__ == '__main__':
    rmdItem = rmdItem()

    # Logging Options
    if rmdItem.log_mode == "console":
        create_stdout_log()
    elif rmdItem.log_mode == "file":
        create_timed_rotating_log(rmdItem.log_filename)
    else:
        create_timed_rotating_log('/dev/null')

    # GPIO import libs
    if rmdItem.powerswitchcommands['switch_mode'] == 'GPIO':
        logging.debug("import GPIO libs")
        import RPi.GPIO as GPIO

    # LED initalize / import libs
    if rmdItem.led_enable == "True":
        logging.debug("LED feature activated")
        if rmdItem.led_type == "internal":
            logging.debug("import rpi_ws281x libs")
            from rpi_ws281x import *
            logging.debug("initiate led stripe")
            rmdItem.initiate_led()
        elif rmdItem.led_type == "external":
            logging.debug("import webcolors and websocket libs")
            import webcolors
            import websocket
            from websocket import create_connection

    try:
        while True:
            for device in rmdItem.create_device_list():
                try:
                    # create connection to server
                    BUFFER_SIZE = 2000
                    tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    logging.debug("Try connect to websocket: {}:{}".format(rmdItem.madmin_host, rmdItem.plugin_port))
                    tcpClient.connect((rmdItem.madmin_host, int(rmdItem.plugin_port)))
                    logging.debug("Connection established...")
                    time.sleep(5)
                    # send token for auth
                    try:
                        logging.debug("Sending auth token...")
                        tcpClient.send(rmdItem.plugin_token.encode('utf-8'))
                        time.sleep(5)
                        # send device origin
                        try:
                            logging.debug("Sending device_origin: {}".format(device))
                            tcpClient.send(device.encode('utf-8'))
                            try:
                                # receive device status data
                                data = pickle.loads(tcpClient.recv(BUFFER_SIZE))
                                logging.debug("Client received data: " + str(data))
                                # analyse data and do action if nessessary
                                if data['reboot_nessessary'] == 'yes':
                                    logging.info("Reboot nessessary for device {}. Initialize reboot.".format(device))
                                    rebootcode = doRebootDevice(device, data['reboot_force'])
                                    try:
                                        if rmdItem.led_enable == "True":
                                            logging.debug("Set status LED to critical for device {}".format(device))
                                            rmdItem.setStatusLED(device, 'crit')
                                    except:
                                        logging.error("Error setting status LED for device: {} ".format(device))
                                elif data['reboot_nessessary'] == 'rebooting':
                                    logging.debug("Wait for device {} comming up after reboot.".format(device))
                                    rebootcode = 0
                                    try:
                                        if rmdItem.led_enable == "True":
                                            logging.debug("Set status LED to warning for device {}".format(device))
                                            rmdItem.setStatusLED(device, 'warn')
                                    except:
                                        logging.error("Error setting status LED for device {} ".format(device))
                                else:
                                    logging.info("No reboot nessessary for device: {}".format(device))
                                    rebootcode = 0
                                    try:
                                        if rmdItem.led_enable == "True":
                                            logging.debug("Set status LED to ok for device {}".format(device))
                                            rmdItem.setStatusLED(device, 'ok')
                                    except:
                                        logging.error("Error setting status LED for device {} ".format(device))
                                # send webhook info if reboot
                                try:
                                    logging.info("Returncode for device " + device + " is " + str(rebootcode))
                                    tcpClient.send(str(rebootcode).encode('utf-8'))
                                except:
                                    logging.error("Error while sending returncode for device {} to RMDserver".format(device))
                            except:
                                logging.error("Error receiving status data for device {} ".format(device))
                        except:
                             logging.error("Error while sending device_origin {} to RMDserver.".format(device))
                    except:
                        logging.error("Error with authentification to RMDserver.")
                    # close connection
                    logging.debug("Closing websocket connection: {}:{}".format(rmdItem.madmin_host, rmdItem.plugin_port))
                    try:
                        tcpClient.close()
                        time.sleep(5)
                    except:
                        logging.error("Error while closing websocket connection: {}:{}".format(rmdItem.madmin_host, rmdItem.plugin_port))
                except:
                    logging.error("Error with websocket connection to RMDserver or server is not ready to accept connections.")
                    logging.info("Sleep for 60s and then retry!")
                    time.sleep(60)
            time.sleep(120)

    except KeyboardInterrupt:
        print("RMDclient will be stopped")
        exit(0)