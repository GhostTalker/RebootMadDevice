#!/bin/bash

# Parameter (ADB location, Device IP:Port)
ADBLOC=$1
DEVICELOC=$2

# ADB command to restart ATLAS
$ADBLOC -s $DEVICELOC shell "su -c am force-stop com.nianticlabs.pokemongo & am force-stop com.pokemod.atlas && am startservice com.pokemod.atlas/com.pokemod.atlas.services.MappingService"
RETURNCODE=$?

# Returncode
exit $RETURNCODE
