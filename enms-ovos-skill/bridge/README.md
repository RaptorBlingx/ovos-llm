# 🎤 OVOS Hybrid Audio Bridge

Solves the WSLg audio corruption issue by capturing audio natively on Windows and sending recognized text to OVOS in WSL2.

## Architecture

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│   Windows (This Bridge)     │         │    WSL2 (OVOS Server)       │
│                             │         │                             │
│  ┌─────────────────────┐    │  text   │   ┌─────────────────────┐   │
│  │ Windows Microphone  │    │ ──────► │   │ ovos-messagebus     │   │
│  │ (Native 16kHz)      │    │   ws    │   └──────────┬──────────┘   │
│  └──────────┬──────────┘    │         │              │              │
│             │               │         │   ┌──────────▼──────────┐   │
│  ┌──────────▼──────────┐    │         │   │ ovos-core           │   │
│  │ Vosk (wake word)    │    │         │   │ (EnMS Skill)        │   │
│  │ + Whisper (command) │    │         │   └──────────┬──────────┘   │
│  └──────────┬──────────┘    │         │              │              │
│             │               │  text   │   ┌──────────▼──────────┐   │
│  ┌──────────▼──────────┐    │ ◄────── │   │ Response Text       │   │
│  │ TTS + Speaker       │    │   ws    │   └─────────────────────┘   │
│  └─────────────────────┘    │         │                             │
└─────────────────────────────┘         └─────────────────────────────┘
```

**Current Implementation:**
- **Wake Word Detection**: Whisper "small" model (continuous, 3s chunks)
- **Command Transcription**: Whisper "small" model
- **Model Size**: 461MB (one-time download)
- **Note**: Using Whisper for wake word is CPU-intensive. Future: Vosk for wake word, Whisper for commands.

## Quick Start

### Step 1: Setup WSL2 (Run in WSL2 terminal)

```bash
# Activate OVOS environment
source ~/ovos-env/bin/activate

# Install bridge requirements
pip install -r /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge/requirements-wsl.txt

# Start OVOS core services (in separate terminals)
# Terminal 1: ovos-messagebus
# Terminal 2: ovos-core
# Terminal 3: Start the bridge
python /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/bridge/wsl_ovos_bridge.py
```

### Step 2: Setup Windows (Run in PowerShell)

```powershell
# Navigate to project
cd D:\ovos-llm-core\ovos-llm\enms-ovos-skill\bridge

# Create virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements-windows.txt

# Download Vosk model (if not already done)
# Option A: Download manually from https://alphacephei.com/vosk/models
# Option B: Use existing model
# Place at: D:\vosk-model-en-us-0.22\

# Start the bridge
python windows_stt_bridge.py
```

### Step 3: Test It!

1. Say "Hey Mycroft" (or "Hey Computer", "Hey Jarvis")
2. Wait for wake word detection
3. Say your command: "Factory overview"
4. Watch the magic happen! 🎉

## Configuration

### Wake Words

Edit `windows_stt_bridge.py` to change wake words:

```python
WAKE_WORDS = ["hey mycroft", "hey jarvis", "computer", "hey computer"]
```

### Vosk Model

The bridge looks for the Vosk model in these locations:
1. `./vosk-model-en-us-0.22` (same directory as script)
2. `D:\vosk-model-en-us-0.22`
3. `C:\vosk-model-en-us-0.22`
4. `%USERPROFILE%\vosk-model-en-us-0.22`

### Network Settings

Default WebSocket port is `5678`. Change with:

```bash
# WSL2
python wsl_ovos_bridge.py --port 5679

# Windows
python windows_stt_bridge.py --port 5679
```

## Troubleshooting

### "Connection refused" on Windows

1. Make sure `wsl_ovos_bridge.py` is running in WSL2
2. Check firewall isn't blocking port 5678
3. Try using WSL2 IP instead of localhost:
   ```powershell
   # Get WSL2 IP
   wsl hostname -I
   # Use that IP
   python windows_stt_bridge.py --host 172.x.x.x
   ```

### "Vosk model not found"

Download the model:
```powershell
# Using curl
curl -L -o vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
# Extract to D:\vosk-model-en-us-0.22
```

### No audio devices found

1. Check Windows Sound settings
2. Make sure microphone is enabled
3. Run: `python -c "import sounddevice as sd; print(sd.query_devices())"`

### Wake word not detected / misheard as "Minecraft" etc

**Issue**: Whisper sometimes mishears wake words:
- "Hey Mycroft" → "Hey Minecraft" 
- "Computer" → "Commuter"

**Workaround**: Say wake word **clearly and slowly**, or use simpler wake word:
- ✅ **"Computer"** (one word, easier)
- ✅ **"Jarvis"** (one word, easier)  
- ⚠️ "Hey Mycroft" (two words, harder)

**Better Solution** (TODO): Use Vosk for wake word detection (faster + more accurate for wake words), Whisper only for commands.

## Files

| File | Location | Purpose |
|------|----------|---------|
| `windows_stt_bridge.py` | Windows | Audio capture + STT |
| `wsl_ovos_bridge.py` | WSL2 | WebSocket ↔ OVOS messagebus |
| `requirements-windows.txt` | Windows | Python dependencies |
| `requirements-wsl.txt` | WSL2 | Python dependencies |

## Why This Works

The WSLg RDP audio tunnel corrupts audio through:
1. Virtualized RDPSource device (not real hardware)
2. Lossy sample rate conversion (44.1kHz → 16kHz)
3. RDP protocol overhead and reconnection issues

By capturing audio natively on Windows, we get clean 16kHz audio that Vosk can recognize correctly.

**Proof:**
- WSL2 captured audio → "fuck that", "we are worried" ❌
- Windows captured audio → "factory overview" ✅
