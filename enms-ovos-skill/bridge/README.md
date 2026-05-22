# OVOS Bridge Utilities

This directory contains the bridge components that connect external clients or
desktop audio workflows to OVOS.

## Components

- `ovos_rest_bridge.py`: REST API gateway for text queries and structured
  responses
- `wsl_ovos_bridge.py`: WSL-side bridge for Windows audio workflows
- `windows_stt_bridge.py`: Windows microphone capture and speech-to-text helper
- `start_rest_bridge.sh`: convenience launcher for the REST bridge

## REST Bridge

The REST bridge is the main integration point for browser clients, dashboards,
or automation scripts.

### Start it directly

```bash
pip install -r requirements-rest-bridge.txt
python ovos_rest_bridge.py
```

### Default endpoint

- `POST /query`
- `POST /query/voice`
- `GET /health`
- `GET /docs`

Example request:

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the power of Compressor-1?"}'
```

## Windows and WSL2 Audio Workflow

If you want live microphone input on Windows while OVOS runs in WSL2, use the
pair `windows_stt_bridge.py` and `wsl_ovos_bridge.py`.

### WSL2 side

```bash
pip install -r requirements-wsl.txt
python wsl_ovos_bridge.py
```

### Windows side

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements-windows.txt
python windows_stt_bridge.py
```

The Windows bridge performs speech capture and forwards recognized text to the
WSL2 bridge, which then relays it into the OVOS messagebus.

## Configuration Notes

- default bridge port: `5678`
- wake words are configured in `windows_stt_bridge.py`
- Vosk or Whisper assets should be downloaded separately and kept outside git

## Troubleshooting

- verify OVOS messagebus is running before starting bridge components
- confirm firewall rules allow the selected bridge port
- check microphone permissions on Windows if no devices are detected
- use the REST bridge first when validating backend connectivity
