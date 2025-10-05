from elevenlabs.client import ElevenLabs
from elevenlabs import stream
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client with your API key
client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Get available voices
voices = client.voices.get_all()
print("Available voices:")
for voice in voices.voices:
    print(f"ID: {voice.voice_id}, Name: {voice.name}")

# Test TTS with a voice (using the first available voice)
if voices.voices:
    test_voice_id = voices.voices[0].voice_id
    print(f"\nTesting with voice: {voices.voices[0].name}")
    
    # Generate and play the audio
    audio_stream = client.text_to_speech.stream(
        text="Hello, this is a test of the ElevenLabs text-to-speech system.",
        voice_id=test_voice_id,
        model_id="eleven_multilingual_v2"
    )
    
    # Stream the audio
    stream(audio_stream)
else:
    print("No voices found. Please check your API key and internet connection.")