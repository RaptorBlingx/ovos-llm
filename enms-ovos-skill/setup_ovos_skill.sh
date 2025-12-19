#!/bin/bash
# ============================================================================
# OVOS EnMS Skill Setup Script
# ============================================================================
# Interactive configuration for YOUR EnMS installation
# WASABI Portability: Works with any EnMS, not just Humanergy
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🔧 OVOS EnMS Skill Setup - WASABI Compatible             ║"
echo "║  Configure voice assistant for YOUR energy system         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ==================== Configuration ====================

# Check if config.yaml exists
if [ -f "config.yaml" ]; then
    echo -e "${YELLOW}⚠️  config.yaml already exists.${NC}"
    read -p "Overwrite existing configuration? (y/n): " OVERWRITE
    if [ "$OVERWRITE" != "y" ]; then
        echo "Setup cancelled. Existing config.yaml preserved."
        exit 0
    fi
    echo ""
fi

# Step 1: Adapter Type
echo "Step 1/6: Select EnMS Adapter"
echo "─────────────────────────────────────"
echo "Available adapters:"
echo "  1) humanergy  - Humanergy's EnMS (default)"
echo "  2) generic    - Generic REST API EnMS"
echo "  3) custom     - Your own adapter"
echo ""
read -p "Select adapter type [1]: " ADAPTER_CHOICE
ADAPTER_CHOICE=${ADAPTER_CHOICE:-1}

case $ADAPTER_CHOICE in
    1) ADAPTER_TYPE="humanergy" ;;
    2) ADAPTER_TYPE="generic" ;;
    3) ADAPTER_TYPE="custom" ;;
    *) ADAPTER_TYPE="humanergy" ;;
esac

echo -e "${GREEN}✓${NC} Selected adapter: $ADAPTER_TYPE"
echo ""

# Step 2: API Connection
echo "Step 2/6: API Connection"
echo "─────────────────────────────────────"
read -p "Enter your EnMS API URL [http://localhost:8001/api/v1]: " API_URL
API_URL=${API_URL:-http://localhost:8001/api/v1}

read -p "API timeout in seconds [90]: " API_TIMEOUT
API_TIMEOUT=${API_TIMEOUT:-90}

echo -e "${GREEN}✓${NC} API configured: $API_URL"
echo ""

# Step 3: Factory Information
echo "Step 3/6: Factory Information"
echo "─────────────────────────────────────"
read -p "Enter your factory name [My Factory]: " FACTORY_NAME
FACTORY_NAME=${FACTORY_NAME:-My Factory}

read -p "Enter factory ID [factory_001]: " FACTORY_ID
FACTORY_ID=${FACTORY_ID:-factory_001}

read -p "Enter timezone [Europe/Berlin]: " TIMEZONE
TIMEZONE=${TIMEZONE:-Europe/Berlin}

echo -e "${GREEN}✓${NC} Factory: $FACTORY_NAME"
echo ""

# Step 4: Machine Discovery
echo "Step 4/6: Machine Discovery"
echo "─────────────────────────────────────"
read -p "Auto-discover machines from API? (y/n) [y]: " AUTO_DISCOVER
AUTO_DISCOVER=${AUTO_DISCOVER:-y}

if [ "$AUTO_DISCOVER" = "y" ]; then
    AUTO_DISCOVER_BOOL="true"
    echo -e "${GREEN}✓${NC} Will auto-discover machines from $API_URL/machines"
else
    AUTO_DISCOVER_BOOL="false"
    echo -e "${YELLOW}ℹ${NC}  Manual machine list required in config.yaml"
fi
echo ""

# Step 5: Test Connection
echo "Step 5/6: Test API Connection"
echo "─────────────────────────────────────"
echo "Testing connection to $API_URL..."

if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/../health" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC} API connection successful!"
        
        # Try to discover machines
        if [ "$AUTO_DISCOVER" = "y" ]; then
            echo ""
            echo "Discovering machines..."
            MACHINES=$(curl -s "$API_URL/machines" 2>/dev/null | grep -o '"machine_name":"[^"]*"' | cut -d'"' -f4 | head -5)
            
            if [ -n "$MACHINES" ]; then
                echo -e "${GREEN}✓${NC} Found machines:"
                echo "$MACHINES" | while read -r machine; do
                    echo "  - $machine"
                done
            else
                echo -e "${YELLOW}⚠️${NC}  No machines found - check API response format"
            fi
        fi
    else
        echo -e "${RED}✗${NC} API connection failed (HTTP $HTTP_CODE)"
        echo -e "${YELLOW}⚠️${NC}  You can continue setup and fix the URL later in config.yaml"
    fi
else
    echo -e "${YELLOW}ℹ${NC}  curl not installed - skipping connection test"
fi
echo ""

# Step 6: Generate Configuration
echo "Step 6/6: Generate Configuration"
echo "─────────────────────────────────────"

cat > config.yaml <<EOF
# ============================================================================
# OVOS EnMS Skill Configuration
# ============================================================================
# Generated by setup_ovos_skill.sh on $(date)
# ============================================================================

# EnMS Adapter
adapter_type: $ADAPTER_TYPE
api_base_url: $API_URL
api_timeout: $API_TIMEOUT
max_retries: 3

# Machine Discovery
auto_discover_machines: $AUTO_DISCOVER_BOOL
auto_discover_seus: $AUTO_DISCOVER_BOOL
refresh_interval_hours: 1

# Fallback machines (used if API discovery fails)
fallback_machines:
  - Compressor-1
  - Boiler-1
  - HVAC-Main
  - Conveyor-A
  - Pump-1

# Factory Metadata
factory_name: $FACTORY_NAME
factory_id: $FACTORY_ID
timezone: $TIMEZONE

# Terminology
terminology:
  energy_unit: kWh
  power_unit: kW
  machine_term: machine
  seu_term: significant energy use
  cost_currency: EUR
  cost_per_kwh: 0.15

# Voice Response Settings
voice:
  use_factory_name: true
  verbosity: medium
  round_numbers: true
  decimal_places: 1

# Default Values
defaults:
  time_range: today
  scope: factory_wide
  interval: 1hour

# Features
features:
  machine_status: true
  energy_queries: true
  comparisons: true
  baseline_predictions: true
  anomaly_detection: true
  report_generation: true
  iso50001_compliance: true
  performance_opportunities: true

# Logging
logging:
  level: INFO
  format: json

# Advanced Settings
advanced:
  cache_ttl: 300
  fuzzy_match_threshold: 80
  zero_trust_validation: true
  max_comparison_machines: 5
  max_historical_days: 365
EOF

echo -e "${GREEN}✓${NC} Configuration saved to config.yaml"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Setup Complete!                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration Summary:"
echo "  Adapter:      $ADAPTER_TYPE"
echo "  API URL:      $API_URL"
echo "  Factory:      $FACTORY_NAME"
echo "  Auto-discover: $AUTO_DISCOVER_BOOL"
echo ""
echo "Next Steps:"
echo "  1. Review config.yaml and customize if needed"
echo "  2. Start OVOS: docker compose up -d"
echo "  3. Test: 'Hey Jarvis, what's the energy consumption?'"
echo ""
echo "Documentation:"
echo "  - Installation Guide: docs/INSTALLATION_GUIDE.md"
echo "  - API Requirements:   docs/API_REQUIREMENTS.md"
echo "  - Troubleshooting:    TROUBLESHOOTING.md"
echo ""
echo "For support, visit: https://github.com/humanergy/ovos-llm"
echo ""
