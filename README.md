# Voice Commander 🎙️

Local voice transcription for coding using whisper.cpp. Works offline, privacy-focused.

## Features
- F8/F9 hotkeys for recording
- Auto-paste transcribed text
- GPU acceleration support
- VS Code extension included

## Setup
1. Install whisper.cpp in parent directory
2. Install Python dependencies: `pip install sounddevice scipy numpy pyperclip pynput`
3. Run: `python portable_commander.py`

## VS Code Extension
See `VScode_extension/` folder for VS Code integration.

## Usage
- Press F8 to start recording
- Press F9 to stop and paste text
- Works in any application 