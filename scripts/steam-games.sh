#!/bin/bash

COMPATPATH=~/.steam/steam/steamapps/compatdata/
TLOUII=2580669941
FLAGS="WINEFSYNC=1 WINEPREFIX=$COMPATPATH$TLOUII/pfx"
WINEEXE="~/.steam/steam/steamapps/common/Proton\ -\ Experimental/files/bin/wine"
EXEC=""
COMMAND="$FLAGS $WINEEXE $EXEC"

echo $COMMAND
