#!/bin/bash

#safe protect
trap undead_trap SIGTERM SIGINT SIGQUIT

if [[ $EUID -ne 0 ]]; then
    #exec sudo -E "$0" "$@"
    exec sudo --reset-timestamp -u root "$0" "$@"
    exit $?
fi

if which schedtool >/dev/null; then
    schedtool -R 1 -e ionice -c 1 -n 0 -p $$
fi

flash_func(){
    echo "Start extruder_mcu_update_fw.sh now!!!"

    FIRMWARE_PATH="/home/sovol/printer_data/build/extruder_mcu_klipper.bin"
    if [ ! -f "$FIRMWARE_PATH" ]; then
        echo "Error: Firmware file not found at $FIRMWARE_PATH. Exiting..."
        exit 1
    fi
    
    FLASH_TOOL_PATH="/home/sovol/printer_data/build/flash_can.py"
    if [ ! -f "$FLASH_TOOL_PATH" ]; then
        echo "Error: Flash tool not found at $FLASH_TOOL_PATH. Exiting..."
        exit 1
    fi
    
    #step 1
    echo "Attempting to enter bootloader..."
    ret=$(python3 flash_can.py -u 61755fe321ac -r | grep -oP 'Success')
    echo "$ret"
    if [ "$ret" != "Success" ]; then
        echo "Enter bootloader failed, please retry."
        exit -1
    else
        echo "Enter bootloader success."
    fi
    
    #step 2
    echo "Querying bootloader UUID..."
    python3 "$FLASH_TOOL_PATH" -i can0 -q
    UUIDS=$(python3 "$FLASH_TOOL_PATH" -i can0 -q | grep -oP 'Detected UUID: \K[a-f0-9]+')
    
    if [ -z "$UUIDS" ]; then
        echo "Error: No devices detected on CAN bus. Exiting..."
        exit 1
    fi
    
    DEFAULT_UUID="61755fe321ac"
    UNSUPPORTED_UUID="58a72bb93aa4"
    
    BOOTLOADER_ID=$(echo "$UUIDS" | head -n 1)
    if [ "$BOOTLOADER_ID" == "$UNSUPPORTED_UUID" ]; then
        echo "Error: Firmware mismatch detected. UUID $UNSUPPORTED_UUID is not supported. Exiting..."
        exit 1
    fi
    
    if [ "$BOOTLOADER_ID" == "$DEFAULT_UUID" ]; then
        echo "Default UUID $DEFAULT_UUID found. Using it for firmware update."
    else
        echo "Detected UUID: $BOOTLOADER_ID. Proceeding with firmware update."
    fi
    
    #step 3
    echo "Flashing MCU firmware with UUID: $BOOTLOADER_ID"
    sleep 0.5
    python3 "$FLASH_TOOL_PATH" -i can0 -f "$FIRMWARE_PATH" -u "$BOOTLOADER_ID" & CHECK_PID=$!
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    TIMEOUT=20
    ELAPSED=0
    while kill -0 $CHECK_PID 2>/dev/null && (( ELAPSED < TIMEOUT )); do
        sleep 1
        ((ELAPSED++))
    done
    
    if kill -0 $CHECK_PID 2>/dev/null; then
        echo "Warning: Process does not complete within ${TIMEOUT} seconds, forced termination..."
        kill -9 $CHECK_PID 2>/dev/null
        wait $CHECK_PID 2>/dev/null
    fi
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    
    if [ $? -eq 0 ]; then
        echo "Firmware update completed successfully!"
    else
        echo "Error: Firmware update failed."
        exit 1
    fi
}
flash_func
