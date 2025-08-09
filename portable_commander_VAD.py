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
import time
from collections import deque

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

WHISPER_CPP_DIR = os.path.join(BASE_DIR, "whisper.cpp")
WHISPER_EXECUTABLE = os.path.join(WHISPER_CPP_DIR, "whisper-cli")
WHISPER_MODEL_PATH = os.path.join(WHISPER_CPP_DIR, "models", "ggml-medium.en.bin")
SAMPLERATE = 16000
CHUNK_DURATION = 0.1  # 100ms chunks for VAD
SILENCE_THRESHOLD = 500  # Set between background (~100) and speech (~2000+)
MIN_SPEECH_DURATION = 1.0  # Minimum 1 second of speech
SILENCE_DURATION = 1.5  # 1.5 seconds of silence to trigger transcription

class AutoRecorder:
    def __init__(self):
        self.recording = True
        self.audio_buffer = deque(maxlen=int(30 * SAMPLERATE / (SAMPLERATE * CHUNK_DURATION)))  # 30 second buffer
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_start = None
        self.transcription_queue = []
        self.processing = False
        self.lock = threading.Lock()

    def start_listening(self):
        print(">>> Auto-recording started. Speak naturally, transcription is automatic.")
        threading.Thread(target=self._audio_loop, daemon=True).start()
        threading.Thread(target=self._transcription_worker, daemon=True).start()

    def stop_listening(self):
        self.recording = False

    def _audio_loop(self):
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32') as stream:
            while self.recording:
                chunk, _ = stream.read(int(SAMPLERATE * CHUNK_DURATION))
                chunk_int16 = (chunk * 32767).astype(np.int16)
                
                # Simple VAD using RMS energy
                rms = np.sqrt(np.mean(chunk_int16.astype(np.float32) ** 2))
                is_speech = rms > SILENCE_THRESHOLD
                
                current_time = time.time()
                
                with self.lock:
                    self.audio_buffer.append(chunk_int16)
                    
                    if is_speech:
                        if not self.is_speaking:
                            print(">>> Speech detected, recording...")
                            self.is_speaking = True
                            self.speech_buffer = list(self.audio_buffer)  # Include some pre-speech context
                        else:
                            self.speech_buffer.append(chunk_int16)
                        self.silence_start = None
                    else:
                        if self.is_speaking:
                            if self.silence_start is None:
                                self.silence_start = current_time
                            elif current_time - self.silence_start > SILENCE_DURATION:
                                # Speech ended, queue for transcription
                                speech_duration = len(self.speech_buffer) * CHUNK_DURATION
                                if speech_duration >= MIN_SPEECH_DURATION:
                                    print(">>> Speech ended, queuing for transcription...")
                                    audio_data = np.concatenate(self.speech_buffer)
                                    self.transcription_queue.append(audio_data.copy())
                                
                                self.is_speaking = False
                                self.speech_buffer = []
                                self.silence_start = None

    def _transcription_worker(self):
        while self.recording or self.transcription_queue:
            if self.transcription_queue:
                with self.lock:
                    if self.transcription_queue and not self.processing:
                        audio_data = self.transcription_queue.pop(0)
                        self.processing = True
                
                threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()
            
            time.sleep(0.1)

    def _process_audio(self, audio_data):
        print("Transcribing...")
        tmp_audio_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        write_wav(tmp_audio_path, SAMPLERATE, audio_data)

        # Simple whisper command without VAD (which needs separate model)
        command = [
            WHISPER_EXECUTABLE,
            "-m", WHISPER_MODEL_PATH,
            "-f", tmp_audio_path,
            "-nt"  # No timestamps
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        os.remove(tmp_audio_path)

        original_transcribed_text = result.stdout.strip()
        
        if original_transcribed_text:
            transcribed_text = original_transcribed_text.lower()
            print(f"Transcribed: {original_transcribed_text}")
            self._execute_command(transcribed_text, original_transcribed_text)
        elif result.stderr:
            print(f"Transcription error: {result.stderr}")

        with self.lock:
            self.processing = False

    def _execute_command(self, transcribed_text, original_text):
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
            pyperclip.copy(original_text)
            print("Text copied to clipboard. Pasting...")
            with controller.pressed(keyboard.Key.ctrl):
                controller.press('v')
                controller.release('v')
            with controller.pressed(keyboard.Key.ctrl, keyboard.Key.shift):
                controller.press('v')
                controller.release('v')
            print("Paste command sent.")

recorder = AutoRecorder()

def on_press(key):
    # Keep F8 as manual override to stop/start
    if key == keyboard.Key.f8:
        if recorder.recording:
            print(">>> Manual stop requested")
            recorder.stop_listening()
        else:
            print(">>> Manual restart requested")
            recorder.recording = True
            recorder.start_listening()

def main():
    print("VoiceCommander (Auto-VAD) is starting...")
    print("Automatic speech detection enabled.")
    print("Press F8 to manually stop/start listening.")
    print("Close this window or press Ctrl+C to exit.")
    
    recorder.start_listening()
    
    with keyboard.Listener(on_press=on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print(">>> Shutting down...")
            recorder.stop_listening()

if __name__ == "__main__":
    main()
