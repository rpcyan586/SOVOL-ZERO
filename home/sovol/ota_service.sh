#!/bin/bash

# Configurable variables
OTA_URL="https://www.comgrow.com/files/printer/ver.json"  # Replace with actual OTA URL
DOWNLOAD_DIR="/home/sovol/printer_data/build/tmp"  # Temporary download directory
LOG_FILE="/home/sovol/download_progress.log"

# 定义文件路径
FILE="/home/sovol/klipper/klippy/extras/display/menu.cfg"

# 检查文件是否存在
if [ ! -f "$FILE" ]; then
    echo "File not found!"
    exit 1
fi

# 使用 awk 提取 version
VERSION=$(awk '
    /\[menu __main __info __version\]/ {found=1; next}
    found && /^name:/ {
        sub(/^name: /, "", $0)
        print $0
        exit
    }
' "$FILE")

# 检查是否提取成功
if [ -n "$VERSION" ]; then
    echo "Extracted version: $VERSION"
else
    echo "Version not found in the file."
fi

# Function to create a directory if it doesn't exist
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo "Created directory: $1"
    fi
}

cleanup_log_file() {
    if [ -f "$LOG_FILE" ]; then
        rm "$LOG_FILE"
        echo "Existing log file deleted: $LOG_FILE"
    fi
}

# Fetch JSON data from OTA URL
get_json_data() {
    local url=$1
    curl -s "$url"
}

# Parse JSON to get versionCode and firmwareMD5
parse_json() {
    echo "$1" | jq -r '.rows | "\(.versionCode) \(.firmwareMD5) \(.path)"'
}

# Calculate MD5 checksum
calculate_md5() {
    md5sum "$1" | awk '{ print $1 }'
}

# Download file with progress bar
download_file() {
    local url=$1
    local output_path=$2

    curl --progress-bar -o "$output_path" "$url" 2>&1 | tee -a "$LOG_FILE" &
}

# Install .deb file
install_deb() {
    local file_path=$1

    if sudo dpkg -i --force-overwrite "$file_path"; then
        echo "Installation successful." >> "$LOG_FILE"
        sync
        reboot
    else
        echo "Installation failed!" >> "$LOG_FILE"
    fi
}

# Main OTA download and install process
main() {
    python3 /home/sovol/pyhelper/ota_process.py "ota checking"

    # Step 1: Get OTA info JSON data
    json_data=$(get_json_data "$OTA_URL")
    if [ -z "$json_data" ]; then
        echo "Failed to fetch OTA information."
        return 1
    fi

    # Parse JSON
    read -r versionCode firmwareMD5 path <<< "$(parse_json "$json_data")"
    if [ -z "$versionCode" ] || [ -z "$firmwareMD5" ] || [ -z "$path" ]; then
        echo "Failed to parse OTA JSON data."
        return 1
    fi

    echo "Version Code: $versionCode" >> "$LOG_FILE"
    echo "Expected MD5: $firmwareMD5" >> "$LOG_FILE"
    echo "Path: $path" >> "$LOG_FILE"

    cleanup_log_file
    echo "Version match. Local version ($VERSION) and OTA version ($versionCode)" >> ~/ota.log
    
    if [ "$VERSION" == "$versionCode" ]; then
        python3 /home/sovol/pyhelper/ota_process.py "latest version"
        return 0
    else
        echo "Version mismatch found. Starting download."
        python3 /home/sovol/pyhelper/ota_process.py "ota 0%"
    fi

    # Prepare download directory
    create_dir "$DOWNLOAD_DIR"
    ota_full_url="${path}"
    output_filepath="$DOWNLOAD_DIR/$(basename "$path")"

    # Download file
    echo "Downloading file from: $ota_full_url" >> "$LOG_FILE"
    download_file "$ota_full_url" "$output_filepath"
    CURL_PID=$!

    while kill -0 "$CURL_PID" 2>/dev/null; do
        last_line=$(tail -n 1 "$LOG_FILE")
        progress=$(echo "$last_line" | awk '{print $NF}' | grep -oP '\d+\.\d+')

        if [[ -n "$progress" ]]; then
            python3 /home/sovol/pyhelper/ota_process.py "ota ${progress}%"
        fi
        sleep 1
    done

    # Verify MD5
    actual_md5=$(calculate_md5 "$output_filepath")
    if [ "$actual_md5" != "$firmwareMD5" ]; then
        echo "MD5 verification failed. OTA update failed!"
        rm -f "$output_filepath"
        return 1
    fi
    echo "MD5 verification successful." >> "$LOG_FILE"

    # Install the .deb package
    install_deb "$output_filepath"

    # Cleanup
    rm -rf "$DOWNLOAD_DIR"
    echo "Download and installation completed successfully." >> "$LOG_FILE"
    python3 /home/sovol/pyhelper/restart_firmware.py
}

# Trap SIGUSR1 to trigger the main function
trap 'main' SIGUSR1

# Keep script alive indefinitely
while true; do
    sleep 1
done

