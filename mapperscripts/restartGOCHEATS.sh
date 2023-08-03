#!/bin/bash

# Parameter (ADB location, Device IP:Port)
ADBLOC=$1
DEVICELOC=$2

# ADB command to restart ATLAS
$ADBLOC -s $DEVICELOC shell "su -c am force-stop com.nianticlabs.pokemongo & am force-stop com.gocheats.launcher && am startservice am start -n com.gocheats.launcher/com.gocheats.launcher.MainActivity"
RETURNCODE=$?

# Returncode
exit $RETURNCODE