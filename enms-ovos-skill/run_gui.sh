#!/bin/bash
# EnMS OVOS Skill GUI Launcher
# This is the CORRECT frontend for testing - uses same logic as quick_test.py

cd /home/ubuntu/ovos/enms-ovos-skill
source venv/bin/activate
PYTHONPATH=/home/ubuntu/ovos/enms-ovos-skill:$PYTHONPATH python3 scripts/chat_gui.py
