#!/bin/bash

# Check if the process name is passed as an argument
if [ $# -eq 0 ]; then
  echo "Usage: $0 <process_name>"
  exit 1
fi

PROCESS_NAME=$1

# Use pgrep to check if the process is running
if pgrep -x "$PROCESS_NAME" > /dev/null; then
  echo "Process '$PROCESS_NAME' is running."
  exit 0
else
  echo "Process '$PROCESS_NAME' is not running."
  exit 1
fi

