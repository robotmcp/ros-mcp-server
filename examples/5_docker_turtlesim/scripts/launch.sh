#!/bin/bash
# Unified launcher for turtlesim - auto-detects OS and runs appropriate script

set -e

# Detect operating system
OS_TYPE=$(uname -s)

case "$OS_TYPE" in
    Darwin*)
        echo "Detected macOS - launching with XQuartz support..."
        ./scripts/launch_macos.sh
        ;;
    Linux*)
        echo "Detected Linux - launching with X11 support..."
        ./scripts/launch_linux.sh
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "Detected Windows - launching with X server support..."
        ./scripts/launch_windows.sh
        ;;
    *)
        echo "Unsupported OS: $OS_TYPE"
        echo "   Please run the appropriate script manually:"
        echo "   - macOS: ./scripts/launch_macos.sh"
        echo "   - Linux: ./scripts/launch_linux.sh"
        echo "   - Windows: ./scripts/launch_windows.sh"
        exit 1
        ;;
esac
