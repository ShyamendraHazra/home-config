#!/bin/bash

image_path=$(yad --width 1200 --height 800 --file --add-preview --large-preview --title='Choose wallpaper' --workdir="$HOME/Wallpapers")

echo $image_path
