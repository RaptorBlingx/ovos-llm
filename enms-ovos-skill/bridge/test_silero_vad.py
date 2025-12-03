#!/usr/bin/env python3
"""
Test script for Silero VAD (Voice Activity Detection)
This verifies Silero VAD works before integrating into the bridge.
"""

import torch
import sounddevice as sd
import numpy as np

# Audio settings
SAMPLE_RATE = 16000
BLOCK_SIZE = 512  # 32ms chunks

print("Loading Silero VAD model...")
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False,
                              onnx=False)

(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

print("✅ Silero VAD loaded successfully")
print("\n🎤 Listening to microphone...")
print("- Be SILENT for 5 seconds → should show low probability")
print("- Then SPEAK for 5 seconds → should show high probability")
print("\nStarting in 3 seconds...\n")

import time
time.sleep(3)

def audio_callback(indata, frames, time_info, status):
    """Process each audio chunk"""
    if status:
        print(f"Status: {status}")
    
    # Convert to tensor (float32, -1.0 to 1.0 range)
    audio_tensor = torch.from_numpy(indata[:, 0].copy())
    
    # Get speech probability from VAD
    speech_prob = model(audio_tensor, SAMPLE_RATE).item()
    
    # Visual indicator
    bar_length = int(speech_prob * 50)
    bar = "█" * bar_length + "░" * (50 - bar_length)
    
    if speech_prob > 0.5:
        print(f"🗣️  SPEECH  [{bar}] {speech_prob:.3f}")
    else:
        print(f"🔇 SILENCE [{bar}] {speech_prob:.3f}")

# Record for 10 seconds
print("Recording for 10 seconds...")
with sd.InputStream(samplerate=SAMPLE_RATE,
                   channels=1,
                   dtype='float32',
                   blocksize=BLOCK_SIZE,
                   callback=audio_callback):
    sd.sleep(10000)  # 10 seconds

print("\n✅ Test complete!")
print("\nExpected behavior:")
print("- Silence/noise: probability < 0.5")
print("- Human speech: probability > 0.5")
