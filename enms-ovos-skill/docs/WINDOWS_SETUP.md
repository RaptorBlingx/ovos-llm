# Windows 11 Setup Guide for OVOS EnMS Skill

## Prerequisites

- Windows 11 (or Windows 10 with WSL2)
- Python 3.11+ installed
- Git installed
- Microphone and speakers

## Quick Setup (15-20 minutes)

### 1. Clone Repository

```powershell
git clone https://github.com/RaptorBlingx/ovos-llm.git
cd ovos-llm\enms-ovos-skill
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
# Core dependencies
pip install -r requirements.txt

# OVOS voice stack
pip install ovos-core ovos-dinkum-listener ovos-audio ovos-messagebus
pip install ovos-stt-plugin-vosk ovos-ww-plugin-vosk phoonnx ovos-vad-plugin-silero
```

### 4. Download Voice Models

The models will auto-download on first run, or manually:

```powershell
# Create model directories
mkdir $env:USERPROFILE\.local\share\vosk -Force
mkdir $env:USERPROFILE\.local\share\piper-tts -Force

# Download Vosk STT model (~40MB)
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile "$env:TEMP\vosk-model.zip"
Expand-Archive -Path "$env:TEMP\vosk-model.zip" -DestinationPath "$env:USERPROFILE\.local\share\vosk"

# Download Piper TTS voice (~60MB)
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -OutFile "$env:USERPROFILE\.local\share\piper-tts\en_US-lessac-medium.onnx"
Invoke-WebRequest -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -OutFile "$env:USERPROFILE\.local\share\piper-tts\en_US-lessac-medium.onnx.json"
```

### 5. Download LLM Model (if using LLM parsing)

```powershell
# Download Qwen3-1.7B (~1.2GB)
mkdir models -Force
Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen_Qwen3-1.7B-Q4_K_M.gguf" -OutFile "models\Qwen_Qwen3-1.7B-Q4_K_M.gguf"
```

### 6. Create OVOS Configuration

Create `%USERPROFILE%\.config\mycroft\mycroft.conf`:

```json
{
  "lang": "en-us",
  "stt": {
    "module": "ovos-stt-plugin-vosk",
    "ovos-stt-plugin-vosk": {
      "model": "~/.local/share/vosk/vosk-model-small-en-us-0.15"
    }
  },
  "tts": {
    "module": "phoonnx",
    "phoonnx": {
      "voice": "~/.local/share/piper-tts/en_US-lessac-medium.onnx"
    }
  },
  "listener": {
    "wake_word": "hey_mycroft"
  },
  "hotwords": {
    "hey_mycroft": {
      "module": "ovos-ww-plugin-vosk",
      "listen": true
    }
  },
  "skills": {
    "directory": "C:/path/to/ovos-llm/enms-ovos-skill"
  }
}
```

## Testing

### Text Mode (No Microphone Required)

```powershell
python scripts\test_skill_chat.py "What's the power of Compressor-1?"
```

### Voice Mode

```powershell
# Start OVOS services (in separate terminals)
ovos-messagebus
ovos-audio
ovos-dinkum-listener
```

Then say: **"Hey Mycroft, what's the power of Compressor-1?"**

## Network Configuration

The EnMS API is at `http://10.33.10.109:8001`. Ensure your Windows machine can reach this address:

```powershell
# Test connectivity
curl http://10.33.10.109:8001/api/v1/health
```

If behind a VPN or firewall, ensure port 8001 is accessible.

## Troubleshooting

### No audio devices found
- Check Windows Sound settings
- Ensure microphone is set as default input device

### STT not working
- Test microphone in Windows Settings > Sound > Input
- Check Vosk model path is correct

### TTS not speaking
- Check speaker output in Windows Sound settings
- Verify Piper model downloaded correctly

### API connection failed
- Verify `10.33.10.109:8001` is reachable
- Check firewall/VPN settings

## Alternative: WSL2 Setup

For better Linux compatibility:

```bash
# In WSL2 terminal
wsl --install -d Ubuntu-22.04

# Then follow Linux setup steps
git clone https://github.com/RaptorBlingx/ovos-llm.git
cd ovos-llm/enms-ovos-skill
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# ... continue with Linux instructions
```

Note: WSL2 requires PulseAudio bridge for Windows audio access.
