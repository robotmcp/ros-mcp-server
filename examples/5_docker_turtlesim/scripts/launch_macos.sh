#!/bin/bash
# Simple macOS startup script for turtlesim GUI
# This script handles all the X11 forwarding complexity automatically

set -e

echo "Starting Turtlesim on macOS with GUI"
echo "========================================"

# Function to detect display number
detect_display() {
    if pgrep -f "Xquartz :1" > /dev/null; then
        echo "1"
    elif pgrep -f "Xquartz :0" > /dev/null; then
        echo "0"
    else
        echo "0"  # Default fallback
    fi
}

# Function to get machine IP
get_machine_ip() {
    # Try en0 first (most common)
    local ip=$(ifconfig en0 2>/dev/null | grep 'inet ' | awk '{print $2}' | head -n1)
    
    # If en0 doesn't work, try other interfaces
    if [[ -z "$ip" ]]; then
        ip=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -n1)
    fi
    
    echo "$ip"
}

# Step 1: Start XQuartz if not running
if ! pgrep -x "X11.bin" > /dev/null; then
    echo "Starting XQuartz..."
    open -a XQuartz
    
    # Wait for XQuartz to start (up to 10 seconds)
    for i in {1..10}; do
        if pgrep -x "X11.bin" > /dev/null; then
            echo "XQuartz started"
            break
        fi
        echo "   Waiting for XQuartz... ($i/10)"
        sleep 1
    done
    
    if ! pgrep -x "X11.bin" > /dev/null; then
        echo "ERROR: XQuartz failed to start. Please start it manually."
        exit 1
    fi
else
    echo "XQuartz already running"
fi

# Step 2: Detect display number and machine IP
DISPLAY_NUM=$(detect_display)
MACHINE_IP=$(get_machine_ip)

if [[ -z "$MACHINE_IP" ]]; then
    echo "ERROR: Could not detect machine IP address"
    echo "Please run: ifconfig en0 | grep inet"
    exit 1
fi

echo "Display detected: :$DISPLAY_NUM"
echo "Machine IP: $MACHINE_IP"

# Step 3: Set up X11 permissions
export DISPLAY=:$DISPLAY_NUM
if command -v xhost >/dev/null 2>&1; then
    echo "Allowing X11 connections..."
    xhost + >/dev/null 2>&1 || echo "WARNING: xhost command failed, but continuing..."
else
    echo "WARNING: xhost not found - X11 forwarding may not work"
fi

# Step 4: Export DISPLAY for Docker
export DISPLAY="$MACHINE_IP:$DISPLAY_NUM"
echo "Docker will use DISPLAY=$DISPLAY"

# Step 5: Start the container
echo ""
echo "Starting Turtlesim container..."
echo "   If successful, you should see a window with a turtle!"
echo ""

docker compose up turtlesim

echo ""
echo "Done! The turtle window should be visible on your screen."