#!/bin/bash

echo $PATH > ~/debug_path.txt
which magick >> ~/debug_path.txt
magick -version >> ~/debug_path.txt
magick -list format >> ~/debug_path.txt

IMAGE_PATH=$(cat ~/.pwall/pwall.txt)

COMMAND="magick $IMAGE_PATH -background black -alpha remove -alpha off -depth 8 -strip ~/Pictures/wall.png"
eval "$COMMAND"
