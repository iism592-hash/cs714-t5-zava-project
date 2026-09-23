#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 STARTING ZAVA DIY MULTI-AGENT CLOUD PLATFORM"
echo "=========================================================="

echo ">> 1. Launching FastMCP Customer Sales Service (Port 8000)..."
python src/python/mcp_server/customer_sales/customer_sales.py --host 127.0.0.1 --port 8000 &
MCP_PID=$!

echo ">> Waiting for MCP server..."
sleep 2

echo ">> 2. Launching Multi-Agent Specialist Service (Port 8006)..."
python src/python/services/agent_service.py &
AGENT_PID=$!

echo ">> Waiting for Agent service..."
sleep 2

echo ">> 3. Launching Public Web Interface (Port 8005)..."
python src/python/web_app/web_app.py
