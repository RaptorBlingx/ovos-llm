#!/usr/bin/env python3
"""
Test Precise Lite wake word detection
"""

import sounddevice as sd
import numpy as np
from precise_lite_runner import PreciseLiteListener
from pathlib import Path

# Download the "hey mycroft" model from OVOS
MODEL_URL = "https://github.com/OpenVoiceOS/precise-lite-models/raw/master/wakewords/en/hey_mycroft.tflite"
MODEL_PATH = Path("hey_mycroft.tflite")

print("🔍 Testing Precise Lite Wake Word Detection")
print("=" * 60)

# Download model if needed
if not MODEL_PATH.exists():
    print(f"Downloading model from {MODEL_URL}...")
    import urllib.request
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("✅ Model downloaded")

def on_activation():
    """Called when wake word is detected"""
    print("\n🎯 WAKE WORD DETECTED! ('Hey Mycroft')")

def on_prediction(prob):
    """Called for each audio chunk with probability"""
    if prob > 0.1:  # Show partial matches
        bar = "█" * int(prob * 50)
        print(f"   Listening... [{bar:<50}] {prob:.3f}", end='\r')

# Initialize Precise Lite listener
print("Loading Precise Lite engine...")
listener = PreciseLiteListener(
    str(MODEL_PATH),
    on_activation=on_activation,
    on_prediction=on_prediction,
    chunk_size=2048,
    trigger_level=3,      # How many chunks in a row to trigger
    sensitivity=0.5       # Threshold (0.0-1.0)
)
print("✅ Precise Lite loaded")
print("\n🎤 Say 'Hey Mycroft' to test wake word detection")
print("   (Background noise should be IGNORED)\n")

# Start listening
listener.start()

try:
    import time
    print("Listening for 30 seconds...")
    time.sleep(30)
except KeyboardInterrupt:
    pass

listener.stop()
print("\n✅ Test complete!")
