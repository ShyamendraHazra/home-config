#!/bin/bash

CONFIG_PATH="$HOME/.config/hypr/hyprlock.conf"
IMAGE_PATH=$(cat ~/.pwall/pwall.txt)
# IMAGE_PATH=$(echo $IMAGE_PATH | sed 's/ /\\ /g' | tr -d '"')

cat <<EOF > "$CONFIG_PATH"
source = $HOME/.cache/wal/colors-hyprland.conf

background {
    monitor =
    path = $HOME/Pictures/wall.png
    # only png supported for now
    # color = $color1

    # all these options are taken from hyprland, see https://wiki.hyprland.org/Configuring/Variables/#blur for explanations
    blur_size = 4
    blur_passes = 3 # 0 disables blurring
    noise = 0.0117
    contrast = 1.3000 # Vibrant!!!
    brightness = 0.8000
    vibrancy = 0.2100
    vibrancy_darkness = 0.0
}

# Hours
label {
    monitor =
    text = cmd[update:1000] echo "<b><span size=\"small\"> $(date +"%H") </span></b>"
    color = $color6
    font_size = 90
    font_family = Geist Mono 10
    shadow_passes = 3
    shadow_size = 4

    position = -80, 150
    halign = center
    valign = center
}

# Minutes
label {
    monitor =
    text = cmd[update:1000] echo "<b><span size=\"small\"> $(date +"%M") </span></b>"
    color = $color6
    font_size = 90
    font_family = Geist Mono 10
    shadow_passes = 3
    shadow_size = 4

    position = 80, 150
    halign = center
    valign = center
}

# Today
label {
    monitor =
    text = cmd[update:1000] echo "<b><span size=\"small\"> $(date +'%A') </span></b>"
    color = $color7
    font_size = 24
    font_family = JetBrainsMono Nerd Font 10

    position = -70, 30
    halign = center
    valign = center
}

# Week
label {
    monitor =
    text = cmd[update:18000000] echo "<b> "$(date +'%d %b')" </b>"
    color = $color7
    font_size = 24
    font_family = JetBrainsMono Nerd Font 10

    position = 70, 30
    halign = center
    valign = center
}

# Degrees
label {
    monitor =
    text = cmd[update:18000000] echo "<b>Feels like<big> $(curl -s 'wttr.in?format=%t' | tr -d '+') </big></b>"
    color = $color7
    font_size = 14
    font_family = Geist Mono 10

    position = 0, 40
    halign = center
    valign = bottom
}

input-field {
    monitor =
    size = 200, 50
    outline_thickness = 2

    dots_size = 0.26 # Scale of input-field height, 0.2 - 0.8
    dots_spacing = 0.64 # Scale of dots' absolute size, 0.0 - 1.0
    dots_center = true
    dots_rouding = -1

    rounding = 22
    outer_color = $color0
    inner_color = $color0
    font_color = $color6
    fade_on_empty = true
    placeholder_text = <i>Password...</i> # Text rendered in the input box when it's empty.

    position = 0, 120
    halign = center
    valign = bottom
}
EOF
