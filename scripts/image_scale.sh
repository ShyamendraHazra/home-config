#!/bin/bash

# Default values for width and height are unset (require both to be set by user)
width=""
height=""

# Parse flags
while getopts "i:o:w:h:" opt; do
  case ${opt} in
    i ) input_dir=$OPTARG ;;
    o ) output_dir=$OPTARG ;;
    w ) width=$OPTARG ;;
    h ) height=$OPTARG ;;
    \? ) echo "Usage: $0 -i source_directory -o output_directory -w width -h height"
         exit 1 ;;
  esac
done

# Check if all required flags are provided
if [[ -z "$input_dir" || -z "$output_dir" || -z "$width" || -z "$height" ]]; then
  echo "Error: All of the following are required: source directory (-i), output directory (-o), width (-w), and height (-h)."
  echo "Usage: $0 -i source_directory -o output_directory -w width -h height"
  exit 1
fi

# Check if input directory exists
if [[ ! -d "$input_dir" ]]; then
  echo "Error: Source directory does not exist."
  exit 1
fi

# Check if output directory exists, create it if it doesn't
if [[ ! -d "$output_dir" ]]; then
  echo "Output directory does not exist, creating it..."
  mkdir -p "$output_dir"
fi

# Function to process files with a specific extension
process_files() {
  ext=$1
  found=0
  for img in "$input_dir"/*."$ext"; do
    if [[ -f "$img" ]]; then
      found=1
      echo "Processing $img..."
      ffmpeg -i "$img" -vf scale=$width:$height "$output_dir/$(basename "$img")"
    fi
  done
  if [[ $found -eq 0 ]]; then
    echo "No .$ext files found in $input_dir."
  fi
}

# Process files for multiple extensions
for ext in jpg png jpeg bmp; do
  process_files "$ext"
done

echo "Batch processing complete."

