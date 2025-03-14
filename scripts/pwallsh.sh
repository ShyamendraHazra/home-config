#!/bin/bash

# Original path with spaces
wall_path=$(cat ~/.pwall/pwall.txt)

# Get the trimmed output from fastfetch
output=$(fastfetch | grep 'Terminal:' | sed 's/^[[:space:]]*//')

# Extract the terminal name (assumed to be the second field)
terminal_name=$(echo "$output" | awk '{print $2}')

# Check if the terminal name is either "kitty" or "ghostty"
if [[ "$terminal_name" == "kitty" || "$terminal_name" == "ghostty" ]]; then

	fastfetch --logo-type kitty --logo-width 45 --logo "$(cat ~/.pwall/pwall.txt)"
else
	
	fastfetch 
fi
