@echo off
REM Start OVOS STT Bridge with Precise Lite
REM
REM This script starts both the WSL2 OVOS bridge and Windows STT bridge

echo ============================================================
echo   Starting OVOS STT Bridge
echo   Precise Lite + Whisper (100%% FREE)
echo ============================================================
echo.

echo [1/2] Starting WSL2 OVOS bridge...
wsl bash -c "cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge ; nohup python3 wsl_ovos_bridge.py > wsl_bridge.log 2>&1 &"
timeout /t 3 /nobreak > nul

echo [2/2] Starting Windows STT bridge...
echo.
echo 🎤 Say "Hey Mycroft" followed by your command
echo.
python "%~dp0windows_stt_bridge_final.py"
