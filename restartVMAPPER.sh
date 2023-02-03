#!/bin/bash

# Parameter (ADB location, Device IP:Port)
ADBLOC=$1
DEVICELOC=$2

# ADB command to restart VMAPPER
$ADBLOC connect $DEVICELOC
$ADBLOC -s $DEVICELOC shell "su -c am force-stop de.vahrmap.vmapper && am force-stop com.nianticlabs.pokemongo && am broadcast -n de.vahrmap.vmapper/.RestartService && monkey -p com.nianticlabs.pokemongo -c android.intent.category.LAUNCHER 1"
RETURNCODE=$?

# Returncode
exit $RETURNCODE


