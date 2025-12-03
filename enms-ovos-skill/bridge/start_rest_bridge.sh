#!/bin/bash
# Start OVOS REST Bridge (Terminal 6)
# Run this AFTER terminals 1-5 are started

echo "=============================================="
echo "  OVOS REST Bridge for EnMS Integration"
echo "=============================================="
echo ""

# Activate OVOS environment
source ~/ovos-env/bin/activate

# Install dependencies if needed
pip install -q fastapi uvicorn pydantic ovos-bus-client 2>/dev/null

# Get Windows IP for reference
echo "Your Windows IP (for EnMS config):"
ip route | grep default | awk '{print $3}' | head -1
echo ""

# Start the bridge
echo "Starting REST Bridge on port 5000..."
echo "EnMS should call: http://<your-windows-ip>:5000/query"
echo ""

python3 /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge/ovos_rest_bridge.py
