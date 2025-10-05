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
from google import genai
from google.genai import types
import whisper

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: could not initialize Gemini client: {e}")
        gemini_client = None
else:
    gemini_client = None

# Audio recording settings
FS = 16000  # Sample rate
DURATION = 5  # Seconds to record per input

def record_audio(filename="input.wav", duration=DURATION, fs=FS):
    print(f"Recording for {duration} seconds...")
    print("🎤 Speak now!")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("✅ Recording complete")
    
    # Check recording quality
    import numpy as np
    max_amplitude = np.max(np.abs(recording))
    print(f"📊 Max amplitude: {max_amplitude} (should be > 100 for audible speech)")
    
    if max_amplitude < 100:
        print("⚠️  WARNING: Very quiet recording! Check your microphone volume/permissions")
    
    # Save as WAV file
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(fs)
        wf.writeframes(recording.tobytes())
    
    file_size = os.path.getsize(filename)
    print(f"💾 Saved recording to {filename} ({file_size} bytes)")

# Load Whisper model once at startup (cached for performance)
print("Loading Whisper speech recognition model...")
try:
    whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
    print("✅ Whisper model loaded successfully")
except Exception as e:
    print(f"⚠️  Could not load Whisper model: {e}")
    whisper_model = None

def speech_to_text(filepath="input.wav"):
    """
    Transcribe audio file using OpenAI Whisper (highly accurate, works offline).
    """
    if whisper_model is None:
        print("❌ Whisper model not available. Cannot transcribe.")
        return ""
    
    # Check if audio file exists and has content
    if not os.path.exists(filepath):
        print(f"❌ Audio file not found: {filepath}")
        return ""
    
    file_size = os.path.getsize(filepath)
    print(f"📊 Audio file size: {file_size} bytes")
    
    if file_size < 1000:  # Very small file, probably no audio
        print("⚠️  Audio file is too small - may not contain speech")
    
    print("Transcribing audio with Whisper...")
    try:
        # Whisper transcription (very accurate!)
        result = whisper_model.transcribe(filepath, language="en", fp16=False)
        
        # Debug: show what Whisper returned
        print(f"🔍 DEBUG - Whisper result keys: {result.keys()}")
        print(f"🔍 DEBUG - Raw text: '{result['text']}'")
        print(f"🔍 DEBUG - Text length: {len(result['text'])}")
        
        transcript = result["text"].strip()
        
        if transcript:
            print(f"✅ Transcription: {transcript}")
            return transcript
        else:
            print("⚠️  Whisper returned empty text - no speech detected in audio")
            # Show segments if available for debugging
            if "segments" in result and result["segments"]:
                print(f"🔍 DEBUG - Found {len(result['segments'])} segments")
                for i, seg in enumerate(result["segments"][:3]):  # Show first 3
                    print(f"  Segment {i}: '{seg.get('text', '')}' (confidence: {seg.get('no_speech_prob', 'N/A')})")
            return ""
            
    except FileNotFoundError:
        print(f"❌ Audio file not found: {filepath}")
        return ""
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return ""

def call_gemini_api(prompt):
    """
    Send prompt to Google Gemini API and get AI-generated text response.
    Uses the modern google-genai library.
    """
    if gemini_client is None:
        print("Gemini client is not configured. Please set GEMINI_API_KEY in .env")
        return "Sorry, Gemini is not configured. Please check your API key."
    
    print("Calling Gemini API...")
    try:
        # Create a chat session with system instructions
        chat = gemini_client.chats.create(
            model='gemini-2.0-flash',
            config=types.GenerateContentConfig(
                system_instruction="""You are a helpful and friendly AI assistant for Rutgers University students.
                Provide a casual, informal, short, concise, accurate, and helpful responses. Be conversational and natural.""",
                temperature=0.7,
                max_output_tokens=1024
            )
        )
        
        # Send the message and get response
        response = chat.send_message(prompt)
        generated_text = response.text
        print(f"Generated response: {generated_text[:100]}...")
        return generated_text
        
    except Exception as e:
        print(f"Gemini request exception: {e}")
        return "Sorry, I could not generate a response. Please try again."

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
        text_to_speech(response_text, voice_id="21m00Tcm4TlvDq8ikWAM")

if __name__ == "__main__":
    main()
