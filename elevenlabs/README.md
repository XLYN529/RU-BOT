# Rutgers Voice Assistant

A voice-enabled AI assistant that uses **OpenAI Whisper** for highly accurate speech recognition and **ElevenLabs** for natural text-to-speech, powered by **Google Gemini** for intelligent responses.

## Features

- 🎤 **Voice Input**: Record your questions using your microphone
- 🗣️ **Voice Output**: Get spoken responses back using ElevenLabs TTS
- 🧠 **OpenAI Whisper**: Industry-leading speech recognition (works offline, highly accurate)
- 🤖 **AI-Powered**: Uses Google Gemini for intelligent, context-aware responses
- 🎓 **Rutgers-Focused**: Designed specifically for Rutgers University students

## Requirements

- Python 3.8+
- Microphone for voice input
- Speaker/headphones for voice output
- API Keys:
  - Google Gemini API key
  - ElevenLabs API key

## Setup

### 1. Install Dependencies

From the root project directory:

```bash
pip install -r requirements.txt
```

This will install:
- `google-genai` - Google Gemini AI SDK
- `elevenlabs` - ElevenLabs voice services
- `sounddevice` - Audio recording
- Other required packages

### 2. Configure API Keys

Create a `.env` file in the root directory (if you haven't already) and add your API keys:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

**Getting API Keys:**

- **Gemini API**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **ElevenLabs API**: Get from [ElevenLabs](https://elevenlabs.io/) (free tier available)

### 3. Test Your Setup

Run the test script to verify everything is configured correctly:

```bash
python test_voice_assistant.py
```

You should see all tests passing ✅

## Usage

### Running the Voice Assistant

From the root directory:

```bash
python elevenlabs/11labs.py
```

Or from the elevenlabs directory:

```bash
cd elevenlabs
python 11labs.py
```

### How to Use

1. **Start**: Run the script - you'll see "RU_AI_Assistant started. Say 'exit' to quit."
2. **Record**: Press Enter when prompted
3. **Speak**: You have 5 seconds to ask your question
4. **Wait**: The assistant will transcribe, process, and respond with voice
5. **Exit**: Say "exit" to quit the program

### Example Interactions

- "What's the weather like on campus?"
- "Tell me about Rutgers University"
- "What resources are available for students?"
- "How can I get involved on campus?"

## How It Works

1. **Voice Input**: Records 5 seconds of audio from your microphone
2. **Transcription**: Uses OpenAI Whisper (offline, highly accurate) to transcribe your speech
3. **AI Processing**: Sends transcribed text to Google Gemini for an intelligent response
4. **Voice Output**: Converts Gemini's response to speech using ElevenLabs TTS
5. **Playback**: Plays the audio response through your speakers

**Why Whisper?** OpenAI Whisper is the most accurate open-source speech recognition available. It works completely offline and handles accents, background noise, and various speaking styles much better than alternatives.

## Configuration Options

You can modify these settings in `11labs.py`:

```python
# Audio recording settings
FS = 16000        # Sample rate (Hz)
DURATION = 5      # Recording duration (seconds)

# Whisper model (line 68)
whisper_model = whisper.load_model("base")
# Options: tiny, base, small, medium, large
# tiny = fastest, least accurate
# base = good balance (recommended)
# large = most accurate, slower

# TTS settings
model_id = "eleven_multilingual_v2"  # ElevenLabs TTS model
```

## Troubleshooting

### "mpv not found" Error

The ElevenLabs SDK requires `mpv` media player for audio streaming:

**macOS:**
```bash
brew install mpv
```

**Linux:**
```bash
sudo apt-get install mpv  # Debian/Ubuntu
```

**Windows:**
Download from [mpv.io](https://mpv.io/installation/) or use Chocolatey:
```bash
choco install mpv
```

### First Time Running - Slow Startup

On first run, Whisper will download the model file (~140MB for "base" model). This is a one-time download and will be cached for future use.

### No Audio Input/Output

- Check that your microphone is connected and enabled
- Check that your speakers/headphones are working
- On macOS, you may need to grant microphone permissions

### "Could not understand audio"

If Whisper isn't recognizing your speech:
- Speak clearly and at a normal pace
- Reduce background noise
- Make sure you're speaking during the 5-second recording window
- Try upgrading to a better model: change `"base"` to `"small"` or `"medium"` on line 68

### API Errors

- Verify your API keys are correct in `.env`
- Check your internet connection
- Ensure you haven't exceeded API rate limits

### Import Errors

If you get module import errors:
```bash
pip install --upgrade -r requirements.txt
```

## File Structure

```
elevenlabs/
├── 11labs.py          # Main voice assistant script
└── README.md          # This file

Related files:
├── test_voice_assistant.py  # Test script
├── requirements.txt         # Python dependencies
└── .env.example            # Environment variables template
```

## Notes

- The voice assistant uses a 5-second recording window by default
- ElevenLabs provides high-quality voice synthesis
- Gemini AI provides intelligent, contextual responses
- All processing happens in real-time

## Future Enhancements

Potential improvements:
- [ ] Integration with Rutgers-specific database (dining, events, etc.)
- [ ] Wake word detection (hands-free activation)
- [ ] Longer conversation context
- [ ] Custom voice selection
- [ ] Voice activity detection (dynamic recording length)

## Support

If you encounter issues:
1. Run the test script: `python test_voice_assistant.py`
2. Check the troubleshooting section above
3. Verify your API keys are valid and have sufficient credits
4. Check that all dependencies are installed

---

Built for Rutgers University students 🎓
