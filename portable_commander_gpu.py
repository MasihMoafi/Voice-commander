import os
import subprocess
import tempfile
import uuid
import threading
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
import numpy as np
import pyperclip
from pynput import keyboard

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

WHISPER_CPP_DIR = os.path.join(BASE_DIR, "whisper.cpp")
WHISPER_EXECUTABLE = os.path.join(WHISPER_CPP_DIR, "whisper-cli")
WHISPER_MODEL_PATH = os.path.join(WHISPER_CPP_DIR, "models", "ggml-medium.en.bin")
HOTKEYS = [keyboard.Key.f8, keyboard.Key.f9]
SAMPLERATE = 16000

# GPU Configuration
GPU_LAYERS = 33  # Medium model has 33 layers
USE_GPU = True


class Recorder:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.recording:
                return
            print(">>> Recording started. Press F8 or F9 to stop.")
            self.recording = True
            self.audio_data = []
            threading.Thread(target=self._record_loop, daemon=True).start()

    def stop_and_process(self):
        with self.lock:
            if not self.recording:
                return
            print(">>> Recording stopped. Processing...")
            self.recording = False
        
        threading.Thread(target=self._process_audio_data, daemon=True).start()

    def _record_loop(self):
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='int16') as stream:
            while self.recording:
                audio_chunk, overflowed = stream.read(SAMPLERATE)
                if overflowed:
                    print("Warning: Audio buffer overflowed")
                with self.lock:
                    if self.recording:
                        self.audio_data.append(audio_chunk)

    def _process_audio_data(self):
        with self.lock:
            if not self.audio_data:
                print("No audio recorded.")
                return
            recording = np.concatenate(self.audio_data, axis=0)

        print("Transcribing with GPU...")
        tmp_audio_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        write_wav(tmp_audio_path, SAMPLERATE, recording)

        command = [WHISPER_EXECUTABLE, "-m", WHISPER_MODEL_PATH, "-f", tmp_audio_path, "-nt"]
        
        result = subprocess.run(command, capture_output=True, text=True)

        os.remove(tmp_audio_path)

        original_transcribed_text = result.stdout.strip()
        
        if not original_transcribed_text and result.stderr:
            print(f"Error: {result.stderr}")
            return

        if original_transcribed_text:
            transcribed_text = original_transcribed_text.lower()
            print(f"Transcribed: {original_transcribed_text}")

            controller = keyboard.Controller()

            if transcribed_text.startswith("copy"):
                print("Executing: Copy")
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('c')
                    controller.release('c')
                with controller.pressed(keyboard.Key.ctrl, keyboard.Key.shift):
                    controller.press('c')
                    controller.release('c')
            elif transcribed_text.startswith("paste"):
                print("Executing: Paste")
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('v')
                    controller.release('v')
                with controller.pressed(keyboard.Key.ctrl, keyboard.Key.shift):
                    controller.press('v')
                    controller.release('v')
            elif transcribed_text.startswith("tab") or transcribed_text.startswith("tap"):
                print("Executing: Alt+Tab")
                with controller.pressed(keyboard.Key.alt):
                    controller.press(keyboard.Key.tab)
                    controller.release(keyboard.Key.tab)
            elif transcribed_text.startswith("dash"):
                print("Executing: Alt+-")
                with controller.pressed(keyboard.Key.alt):
                    controller.press('-')
                    controller.release('-')
            elif transcribed_text.startswith("switch"):
                print("Executing: Ctrl+PageDown (Next Terminal Tab)")
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press(keyboard.Key.page_down)
                    controller.release(keyboard.Key.page_down)
            elif transcribed_text.startswith("desktop"):
                print("Executing: Super+D (Show Desktop)")
                with controller.pressed(keyboard.Key.cmd):
                    controller.press('d')
                    controller.release('d')
            elif transcribed_text.startswith("exit"):
                print("Executing: Ctrl+D")
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('d')
                    controller.release('d')
            elif transcribed_text.startswith("enter"):
                print("Executing: Enter")
                controller.press(keyboard.Key.enter)
                controller.release(keyboard.Key.enter)
            elif transcribed_text.startswith("delete"):
                print("Executing: Delete")
                controller.press(keyboard.Key.delete)
                controller.release(keyboard.Key.delete)
            elif transcribed_text.startswith("escape"):
                print("Executing: Escape")
                controller.press(keyboard.Key.esc)
                controller.release(keyboard.Key.esc)
            else:
                pyperclip.copy(original_transcribed_text)
                print("Text copied to clipboard. Pasting...")
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('v')
                    controller.release('v')
                with controller.pressed(keyboard.Key.ctrl, keyboard.Key.shift):
                    controller.press('v')
                    controller.release('v')
                print("Paste command sent.")
        elif result.returncode != 0:
            print("Whisper.cpp failed:")
            print(result.stderr)

recorder = Recorder()

def on_press(key):
    if key in HOTKEYS:
        if recorder.recording:
            recorder.stop_and_process()
        else:
            recorder.start()

def main():
    print(f"VoiceCommander (GPU) is active. Press F8 or F9 to start/stop recording.")
    print("GPU acceleration enabled with CUDA.")
    print("The transcribed text will be pasted at your cursor's location.")
    print("Close this window or press Ctrl+C to exit.")
    
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()
