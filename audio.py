import streamlit as st
import os
import tempfile
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
import uuid
import subprocess
import numpy as np
from pydub import AudioSegment

# --- CONFIGURATION ---
WHISPER_CPP_DIR = "/home/masih/whisper.cpp"
WHISPER_EXECUTABLE = os.path.join(WHISPER_CPP_DIR, "build", "bin", "whisper-cli")
WHISPER_MODEL_PATH = os.path.join(WHISPER_CPP_DIR, "models", "ggml-medium.en.bin")

KOKORO_SCRIPT_DIR = "/home/masih/My_freelance_website/scripts"
KOKORO_SCRIPT_PATH = os.path.join(KOKORO_SCRIPT_DIR, "kokoro_tts.py")

# --- SYNCHRONOUS HELPER FUNCTION ---
def run_subprocess_sync(command, cwd=None):
    """Runs a subprocess synchronously and returns stdout, stderr."""
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode

# --- PAGE SETUP ---
st.set_page_config(page_title="Juliette AI", layout="centered")
st.title("Juliette AI 🎙️")
st.caption("Your personal, local, lightning-fast voice assistant.")

# --- SESSION STATE INITIALIZATION ---
if "recording" not in st.session_state:
    st.session_state.recording = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = []
if "tts_text" not in st.session_state:
    st.session_state.tts_text = "Welcome, my King. Record your voice or type here."
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "last_audio_format" not in st.session_state:
    st.session_state.last_audio_format = 'audio/wav'


# --- UI & LOGIC ---
st.subheader("1. Listen (STT)")

if not st.session_state.recording:
    if st.button("Start Recording"):
        st.session_state.recording = True
        st.session_state.audio_data = []
        st.rerun()
else:
    st.info("🔴 Recording... Press 'Stop Recording' when you are finished.")
    if st.button("Stop Recording"):
        st.session_state.recording = False
        
        with st.spinner("Transcribing..."):
            if not st.session_state.audio_data:
                st.warning("No audio recorded.")
            else:
                samplerate = 16000 # Assuming 16kHz
                recording = np.concatenate(st.session_state.audio_data, axis=0)
                
                tmp_audio_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
                write_wav(tmp_audio_path, samplerate, recording)

                command = [WHISPER_EXECUTABLE, "-m", WHISPER_MODEL_PATH, "-f", tmp_audio_path, "-nt"]
                stdout, stderr, returncode = run_subprocess_sync(command)

                if returncode == 0:
                    # Update the single text area with the transcription result
                    st.session_state.tts_text = stdout.strip()
                else:
                    st.error("Whisper.cpp failed:")
                    st.code(stderr)
                
                os.remove(tmp_audio_path)
        st.rerun()

# This part is a bit of a hack to keep the recording running
if st.session_state.recording:
    with st.spinner("Recording..."):
        samplerate = 16000
        # Record in small chunks to keep the app responsive
        chunk = sd.rec(int(1 * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        st.session_state.audio_data.append(chunk)
        st.rerun()

st.subheader("2. Speak (TTS)")

# Unified, editable text area for transcription result and manual input
# The `value` is set from session_state, but we don't use a `key`.
# The user's edits will be captured in the return value `tts_input`.
tts_input = st.text_area("Text to Speak", value=st.session_state.tts_text, height=150)

speed_options = {"1.0x": 1.0, "1.25x": 1.25, "1.5x": 1.5, "1.75x": 1.75}
selected_speed_label = st.selectbox("Playback Speed", options=list(speed_options.keys()))
selected_speed = speed_options[selected_speed_label]

if st.button("Generate Speech"):
    text_to_speak = tts_input # Read from the widget's return value
    if text_to_speak:
        with st.spinner("Generating and processing speech..."):
            tmp_input_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.txt")
            tmp_output_wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
            tmp_output_mp3_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.mp3")

            with open(tmp_input_path, 'w') as f:
                f.write(text_to_speak)

            # Generate the initial WAV file
            command = ["python", KOKORO_SCRIPT_PATH, tmp_input_path, tmp_output_wav_path]
            stdout, stderr, returncode = run_subprocess_sync(command, cwd=KOKORO_SCRIPT_DIR)

            if returncode == 0 and os.path.exists(tmp_output_wav_path):
                # Load the WAV file with pydub
                audio = AudioSegment.from_wav(tmp_output_wav_path)

                # Speed up the audio if necessary
                if selected_speed != 1.0:
                    audio = audio.speedup(playback_speed=selected_speed)

                # Export as MP3
                audio.export(tmp_output_mp3_path, format="mp3")

                # Read the final audio data
                with open(tmp_output_mp3_path, 'rb') as f:
                    st.session_state.last_audio = f.read()
                    st.session_state.last_audio_format = 'audio/mp3'

            elif returncode != 0:
                st.error("Speech generation failed. Please try again.")
            else:
                st.error("Generated audio file not found. Please try again.")

            # Cleanup temporary files
            os.remove(tmp_input_path)
            if os.path.exists(tmp_output_wav_path):
                os.remove(tmp_output_wav_path)
            if os.path.exists(tmp_output_mp3_path):
                os.remove(tmp_output_mp3_path)
            st.rerun()
    else:
        st.warning("There is no text to speak.")

if st.session_state.last_audio:
    st.audio(st.session_state.last_audio, format=st.session_state.last_audio_format)
    st.download_button(
        label="Save Audio",
        data=st.session_state.last_audio,
        file_name="juliette_ai_speech.mp3",
        mime="audio/mp3"
    )
