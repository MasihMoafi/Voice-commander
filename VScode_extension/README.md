# Voice Commander VS Code Extension

Local voice transcription for coding using whisper.cpp.

## Setup

1. Ensure whisper.cpp is in parent directory
2. Install dependencies: `npm install`
3. Compile: `npm run compile`
4. Install extension: `code --install-extension voice-commander-1.0.0.vsix`

## Usage

- F8: Start recording
- F9: Stop recording and insert text

## Publishing

```bash
npm install -g vsce
vsce package
vsce publish
``` 