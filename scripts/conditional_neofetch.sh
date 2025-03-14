
#!/bin/bash

# Get the trimmed output from fastfetch
output=$(fastfetch | grep 'Terminal:' | sed 's/^[[:space:]]*//')

output=$(fastfetch | grep 'Terminal:' | sed 's/^[[:space:]]*//')
echo "DEBUG: Fastfetch output is: [$output]"
terminal_name=$(echo "$output" | awk '{print $2}' | tr -d '[:space:]')
echo "DEBUG: Extracted terminal name is: [$terminal_name]"
#
# Extract the terminal name (assumed to be the second field)
terminal_name=$(echo "$output" | awk '{print $2}')

# Check if the terminal name is either "kitty" or "ghostty"
if [[ "$terminal_name" == "kitty" || "$terminal_name" == "ghostty" ]]; then
    echo "Terminal is either kitty or ghostty."
else
    echo "Terminal is not kitty or ghostty."
fi

