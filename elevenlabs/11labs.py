import os
import sounddevice as sd
import wave
import requests
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
from dotenv import load_dotenv
import contextlib
import io
import tempfile
import requests.exceptions as req_exceptions
import shutil
import subprocess

# Load environment variables from .env file but suppress parse warnings from python-dotenv
try:
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stderr(devnull), contextlib.redirect_stdout(devnull):
            load_dotenv()
except Exception:
    # Best-effort load; if it fails we'll still read os.environ below
    load_dotenv()

# Initialize ElevenLabs client lazily (only if API key present)
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if ELEVEN_API_KEY:
    try:
        eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)
    except Exception as e:
        print(f"Warning: could not initialize ElevenLabs client: {e}")
        eleven_client = None
else:
    eleven_client = None

# Google Gemini API config
API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
GEMINI_API_URL = "https://api.generativeai.googleapis.com/v1beta2/models/gemini-pro:generateText"

# Allow an escape hatch for debugging TLS issues (set GEMINI_INSECURE=1 in your env to skip verification)
GEMINI_INSECURE = os.getenv('GEMINI_INSECURE', '') == '1'

# Audio recording settings
FS = 16000  # Sample rate
DURATION = 5  # Seconds to record per input

def record_audio(filename="input.wav", duration=DURATION, fs=FS):
    print(f"Recording for {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    # Save as WAV file
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(fs)
        wf.writeframes(recording.tobytes())
    print(f"Saved recording to {filename}")

def speech_to_text(filepath="input.wav"):
    """
    Upload audio file to Eleven Labs STT and get transcription.
    """
    url = "https://api.elevenlabs.io/v1/stt/convert"
    headers = {
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
    }
    data = {
        "model_id": "scribe_v1",
        "response_format": "text"
    }
    print("Uploading audio for transcription...")
    try:
        with open(filepath, "rb") as f:
            files = {"file": f}
            response = requests.post(url, headers=headers, files=files, data=data)
    except FileNotFoundError:
        print(f"Audio file not found: {filepath}")
        return ""
    except Exception as e:
        print(f"Error uploading audio: {e}")
        return ""

    if response.status_code == 200:
        transcript = response.text
        print(f"Transcription: {transcript}")
        return transcript
    else:
        print(f"STT request failed: {response.status_code} - {response.text}")
        return ""

def call_gemini_api(prompt):
    """
    Send prompt to Google Gemini API and get AI-generated text response.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    json_data = {
        "prompt": {
            "text": prompt
        },
        "temperature": 0.7,
        "maxOutputTokens": 1024,
    }
    print("Calling Gemini API...")
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=json_data, verify=not GEMINI_INSECURE, timeout=15)
    except req_exceptions.SSLError as e:
        # SSL diagnostic information
        proxies = {k: os.environ.get(k) for k in ('HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy')}
        cert_env = {k: os.environ.get(k) for k in ('REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE')}
        print("Gemini SSL error:", e)
        print("Proxies:", proxies)
        print("Cert env vars:", cert_env)
        print("If you're behind a proxy or corporate firewall that intercepts TLS, try setting GEMINI_INSECURE=1 temporarily to diagnose (not recommended for production).")
        return "Gemini SSL error: network verification failed. See logs for diagnostics."
    except Exception as e:
        print("Gemini request exception:", e)
        return "Gemini request failed: see logs"

    if response.status_code == 200:
        try:
            result = response.json()
            generated_text = result['candidates'][0]['output']
            print(f"Generated response: {generated_text}")
            return generated_text
        except Exception as e:
            print("Error parsing Gemini response:", e)
            return "Sorry, I could not parse the response."
    else:
        print(f"Gemini API error: {response.status_code} {response.text}")
        return "Sorry, I could not generate a response."

def text_to_speech(text, voice_id=None, model_id="eleven_multilingual_v2"):
    """
    Convert text to speech and play audio stream.
    """
    if eleven_client is None:
        print("ElevenLabs client is not configured. Skipping TTS.")
        return

    try:
        voices = eleven_client.voices.get_all().voices
    except Exception as e:
        print(f"Could not fetch voices from ElevenLabs: {e}")
        return

    if voice_id is None:
        if not voices:
            print("No available voices found.")
            return
        voice_id = voices[0].voice_id

    print(f"Speaking with voice ID: {voice_id}")
    try:
        audio_stream = eleven_client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id=model_id
        )
        stream(audio_stream)
    except Exception as e:
        # Common issue: mpv player is required to stream audio; provide clearer guidance
        msg = str(e)
        if 'mpv not found' in msg.lower():
            print("Error during TTS streaming: mpv not found. mpv is required to play streamed audio.")
            print("On Windows you can install mpv from https://mpv.io/ or via package managers like Chocolatey: 'choco install mpv'.")
            print("Falling back to local OS TTS (not ElevenLabs voice).")
            # Cross-platform simple fallback using OS TTS (Windows SAPI via PowerShell, macOS `say`, Linux `espeak`)
            try:
                import platform, subprocess, shlex

                system = platform.system()
                if system == 'Windows':
                    # Use PowerShell to call System.Speech.Synthesis; find a powershell executable first
                    safe_text = text.replace("'", "''")
                    ps_script = ("Add-Type -AssemblyName System.Speech; "
                                 "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + safe_text + "')")
                    pwsh = shutil.which('powershell') or shutil.which('pwsh')
                    if not pwsh:
                        # fallback to the Windows default location
                        pwsh = r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
                    try:
                        subprocess.run([pwsh, "-NoProfile", "-Command", ps_script], check=False)
                    except FileNotFoundError:
                        print('PowerShell not found for local TTS fallback; cannot speak.')
                elif system == 'Darwin':
                    # macOS 'say'
                    subprocess.run(["say", text], check=False)
                else:
                    # Try espeak on Linux; if not present, print the text
                    if shutil.which('espeak'):
                        subprocess.run(['espeak', text], check=False)
                    else:
                        print('Local TTS fallback: please install espeak or mpv, or run the assistant in a shell with mpv available.')
                        print('Text to speak:\n', text)
            except Exception as e2:
                print('Fallback TTS failed:', e2)
            return
        else:
            print(f"Error during TTS streaming: {e}")

def main():
    print("RU_AI_Assistant started. Say 'exit' to quit.")
    while True:
        input("Press Enter to start recording your question...")
        record_audio()
        user_text = speech_to_text()
        if user_text.strip().lower() == "exit":
            print("Exiting assistant...")
            break

        # Send user speech text to Gemini LLM API for response
        response_text = call_gemini_api(user_text)

        # Speak the LLM's response back to user
        text_to_speech(response_text)

if __name__ == "__main__":
    main()
