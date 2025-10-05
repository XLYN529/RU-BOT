# Voice Mode Guide

## Overview
The RU Assistant now supports voice interaction with Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities.

## Features
- **Voice Mode Toggle**: Switch between text and voice input with a microphone button
- **Automatic Silence Detection**: Recording stops after 5 seconds of silence
- **Natural Conversation**: Assistant responds with voice in voice mode
- **Same Gemini Backend**: Uses the same chat pipeline and context

## Setup

### 1. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `openai-whisper` - Speech-to-Text (runs locally)
- `elevenlabs` - Text-to-Speech API

### 2. Configure API Keys
Add your ElevenLabs API key to `.env`:
```
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

Get your ElevenLabs API key from: https://elevenlabs.io/

### 3. Start the Backend
```bash
cd backend
python main.py
```

### 4. Start the Frontend
```bash
cd chat-frontend
npm install
npm run dev
```

## Usage

### Voice Mode
1. **Enable Voice Mode**: Click the microphone button in the input box
   - The microphone icon will turn red when active
   
2. **Record Your Question**: 
   - Click the red recording button (circle icon)
   - Speak your question
   - The recording will automatically stop after 5 seconds of silence
   - Or manually click the stop button (square icon) to end recording
   
3. **Get Voice Response**:
   - Your speech is transcribed and sent to Gemini
   - The assistant's response is displayed as text
   - The response is automatically spoken using ElevenLabs TTS

### Text Mode (Default)
- Click the microphone button again to return to text mode
- Type messages as normal

## Technical Details

### Speech-to-Text (STT)
- **Engine**: OpenAI Whisper (base model)
- **Processing**: Runs locally on your machine
- **Language**: English
- **Accuracy**: High accuracy for clear speech

### Text-to-Speech (TTS)
- **Service**: ElevenLabs API
- **Model**: eleven_multilingual_v2
- **Voice**: Uses your default ElevenLabs voice
- **Quality**: Natural-sounding AI voice

### Silence Detection
- **Threshold**: 5 dB average volume
- **Timeout**: 5 seconds of silence triggers auto-stop
- **Monitoring**: Checks audio levels every 100ms

## Browser Permissions
When you first use voice mode, your browser will ask for microphone permission. Click "Allow" to enable voice recording.

## Troubleshooting

### No Microphone Access
- Check browser permissions (chrome://settings/content/microphone)
- Ensure your microphone is connected and working
- Try refreshing the page and allowing permissions again

### STT Not Working
- Speak clearly and close to the microphone
- Check that ambient noise is minimal
- Ensure Whisper model loaded successfully (check backend logs)

### TTS Not Working
- Verify your ELEVENLABS_API_KEY is set correctly in `.env`
- Check that you have API credits in your ElevenLabs account
- Review backend logs for TTS errors

### Voice Stops Too Early
- The silence detection is set to 5 seconds
- Speak continuously or increase silence timeout in `App.tsx` line 186

## API Costs
- **Whisper STT**: Free (runs locally)
- **ElevenLabs TTS**: Paid service
  - Free tier: 10,000 characters/month
  - Check pricing: https://elevenlabs.io/pricing

## Notes
- Voice mode uses the same Gemini chat pipeline as text mode
- All personal context and session history is preserved
- You can switch between text and voice mode at any time
- Recording quality depends on your microphone hardware
