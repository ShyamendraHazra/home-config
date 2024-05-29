#!/bin/bash

# Generate Pywal colors
wal -i /path/to/your/image.jpg -n -q

# Read Pywal-generated colors
readarray -t pywal_colors < ~/.cache/wal/colors

# Function to convert hexadecimal to RGB
hex_to_rgb() {
    local hex=$1
    local r=$(printf "%d" 0x${hex:1:2})
    local g=$(printf "%d" 0x${hex:3:2})
    local b=$(printf "%d" 0x${hex:5:2})
    echo "$r,$g,$b"
}

# Extract relevant colors and convert from hex to RGB
foreground_normal=$(hex_to_rgb "${pywal_colors[0]}")
background_normal=$(hex_to_rgb "${pywal_colors[1]}")
# Add more colors as needed

# Update kdeglobals file
kdeglobals_path=~/.config/kdeglobals

# Update ForegroundNormal color
sed -i "s|^ForegroundNormal=.*$|ForegroundNormal=$foreground_normal|" "$kdeglobals_path"

# Update BackgroundNormal color
sed -i "s|^BackgroundNormal=.*$|BackgroundNormal=$background_normal|" "$kdeglobals_path"

# Update more colors as needed

