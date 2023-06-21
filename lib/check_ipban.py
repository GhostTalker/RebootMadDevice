#!/usr/bin/env /srv/PyVenv/rmdV3/bin/python3
#
# RebootMadDevices
# ip ban class
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "1.0.0"
__status__ = "TEST"

import time
import datetime
import requests

class check_ipban:
   def __init__(self, ip_ban_check_wh, ip_ban_check_ping):
      self._ip_ban_check_wh = ip_ban_check_wh
      self._ip_ban_check_ping = ip_ban_check_ping

      banned = True
      wh_send = False
      while banned: 
          #print("Checking PTC Login Servers...")
          try:
              result = requests.head('https://sso.pokemon.com/sso/login')
              result.raise_for_status()
          except requests.exceptions.RequestException as err:
              print(f"PTC Servers are not reachable! Error: {err}")
              print("Waiting 5 minutes and trying again")
              time.sleep(300)
              continue
          if result.status_code != 200:
              print("IP is banned by PTC, waiting 5 minutes and trying again")
              # Only send a message once per ban and only when a webhook is set
              if not wh_send and self._ip_ban_check_wh:
                  unbantime = datetime.datetime.now() + datetime.timedelta(hours=3)
                  data = {
                      "username": "Alert!",
                      "avatar_url": "https://github.com/GhostTalker/icons/blob/main/rmd/messagebox_critical_256.png?raw=true",
                      "content": f"<@{self._ip_ban_check_ping}> IP address is currently banned by PTC! \nApproximate remaining time until unban: <t:{int(unbantime.timestamp())}:R> ({unbantime.strftime('%H:%M')})",
                  }
                  try:
                      result = requests.post(self._ip_ban_check_wh, json=data)
                      result.raise_for_status()
                  except requests.exceptions.RequestException as err:
                      print(err)
              wh_send = True
              time.sleep(300)
              continue
          else:
              #print("IP is not banned by PTC, continuing...")
              banned = False
              wh_send = False