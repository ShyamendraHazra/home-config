#!/bin/bash

# Check if a filename is provided
if [ -z "$1" ]; then
    echo "Please provide a source code file."
    exit 1
fi

# Extract filename and extension
filename=$(basename -- "$1")
extension="${filename##*.}"
filename="${filename%.*}"

# Cross-compile for Windows x86_64
x86_64-w64-mingw32-gcc -o "${filename}_win_x86_64.exe" "$1" &&

# Cross-compile for Windows ARM
arm-none-eabi-gcc -o "${filename}_win_arm.exe" "$1" &&

# Compile for macOS x86_64
gcc -o "${filename}_mac_x86_64" "$1" &&

# Cross-compile for macOS ARM
/usr/local/Cellar/gcc/11.0.0_1/bin/gcc-11 -arch arm64 -o "${filename}_mac_arm" "$1" &&

# Compile for Linux x86_64
gcc -o "${filename}_linux_x86_64" "$1" &&

# Cross-compile for Linux ARM
arm-linux-gnueabihf-gcc -o "${filename}_linux_arm" "$1"

