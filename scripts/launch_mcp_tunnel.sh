#!/usr/bin/env bash
set -eo pipefail

# Colors for log output
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DOMAIN=${MCP_DOMAIN:-"mazie-nonmodificatory-noncontemporaneously.ngrok-free.app"}
PORT=${MCP_PORT:-"9000"}

echo -e "${BLUE}Starting MCP ngrok tunneling...${NC}"

# 1. Check if MCP server is running
if pgrep -f ngrok > /dev/null; then
  echo -e "${YELLOW}[mcp-server]${NC} is already running. Continuing without starting a new instance."
  NGROK_PID=$(pgrep -f ngrok | head -n1)
else 
  # 2. Start ngrok tunnel
  echo -e "${GREEN}[mcp-ngrok]${NC} Exposing MCP server via ngrok tunnel..."
  ngrok http --url=${DOMAIN} ${PORT} &
  NGROK_PID=$!
fi

echo -e "${GREEN}[mcp-ngrok]${NC} mcp-ngrok PID:  $NGROK_PID"

# 3. Trap to clean up processes on exit
trap "echo -e '${GREEN}[mcp-ngrok] ${NC}Stopping ngrok processes...'; kill -9 $NGROK_PID" SIGINT SIGTERM

# 4. Keep script running, showing logs
wait
