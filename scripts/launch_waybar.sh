#!/bin/bash

# Correctly reference the check_process_status.sh script
CHECK_PROCESS_SCRIPT="$HOME/scripts/check_process_status.sh"

# Example process to check
PROCESS_NAME="waybar"

# Call the check_process_status script and check exit status immediately
$CHECK_PROCESS_SCRIPT "$PROCESS_NAME"
STATUS=$? # Capture exit status immediately

if [ $STATUS -eq 0 ]; then
  echo -e "Killing waybar\n"
  pkill waybar

else
  echo -e "Launching waybar\n"
  waybar -c ~/.config/waybar/config.json  -s .config/waybar/style.css  &
fi

