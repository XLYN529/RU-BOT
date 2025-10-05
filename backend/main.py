from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
from dotenv import load_dotenv
import traceback
import logging
import base64
import json
import sys
import uuid
import traceback
import logging
import io
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import gemini modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from gemini.chat_pipeline_class import ChatSession
from backend.personal_context import PersonalContextManager

# Import voice processing libraries
try:
    import whisper
    from elevenlabs.client import ElevenLabs
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    logger.warning("Voice libraries not available. Install whisper and elevenlabs for voice features.")

# Store active chat sessions in memory
chat_sessions: Dict[str, ChatSession] = {}

# Initialize personal context manager
context_manager = PersonalContextManager()

# Initialize voice processing clients
if VOICE_AVAILABLE:
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if ELEVENLABS_API_KEY:
        try:
            eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            logger.info("ElevenLabs client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs: {e}")
            eleven_client = None
    else:
        eleven_client = None
        logger.warning("ELEVENLABS_API_KEY not found")
    
    # Load Whisper model
    try:
        whisper_model = whisper.load_model("base")
        logger.info("Whisper model loaded")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        whisper_model = None
else:
    eleven_client = None
    whisper_model = None

app = FastAPI(title="RU Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    api_key: str | None = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class PersonalContextRequest(BaseModel):
    session_id: Optional[str] = None  # Kept for backwards compatibility, but ignored
    context_type: str  # "schedule", "assignment", "note", "preference"
    data: Dict

@app.get("/")
async def root():
    return {"message": "RU Assistant API is running"}

@app.get("/api/context")
async def get_context():
    """Get global personal context"""
    try:
        context = context_manager.get_context()
        return {"context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/context/{session_id}")
async def get_context_legacy(session_id: str):
    """Get personal context (legacy endpoint - now returns global context)"""
    try:
        context = context_manager.get_context()
        return {"context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/context")
async def add_context(request: PersonalContextRequest):
    """Add personal context item (global context)"""
    try:
        context_type = request.context_type
        data = request.data
        
        if context_type == "schedule":
            success = context_manager.add_schedule_item(
                course=data.get("course", ""),
                day=data.get("day", ""),
                time=data.get("time", ""),
                location=data.get("location", "")
            )
        elif context_type == "assignment":
            success = context_manager.add_assignment(
                title=data.get("title", ""),
                due_date=data.get("due_date", ""),
                course=data.get("course", ""),
                description=data.get("description", "")
            )
        elif context_type == "note":
            success = context_manager.add_note(
                note=data.get("content", ""),
                category=data.get("category", "general")
            )
        elif context_type == "preference":
            success = context_manager.set_preference(
                key=data.get("key", ""),
                value=data.get("value", "")
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid context_type")
        
        if success:
            return {"success": True, "message": "Context added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save context")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/context")
async def clear_context():
    """Clear all global personal context"""
    try:
        success = context_manager.clear_context()
        if success:
            return {"success": True, "message": "Context cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear context")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/context/{session_id}")
async def clear_context_legacy(session_id: str):
    """Clear all personal context (legacy endpoint - clears global context)"""
    try:
        success = context_manager.clear_context()
        if success:
            return {"success": True, "message": "Context cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear context")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the RU Assistant and get a response
    """
    try:
        logger.info(f"Received message: {request.message[:50]}...")
        logger.info(f"Session ID: {request.session_id}")
        
        if not request.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Use API key from request or fall back to environment variable
        api_key = request.api_key or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.error("No API key found")
            raise HTTPException(status_code=400, detail="API key not found. Please set GEMINI_API_KEY in .env file")
        
        # Get or create chat session
        session_id = request.session_id
        if not session_id or session_id not in chat_sessions:
            # Create new session
            logger.info("Creating new chat session")
            session_id = str(uuid.uuid4())
            try:
                chat_sessions[session_id] = ChatSession(api_key)
                logger.info(f"Created session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to create session: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        else:
            logger.info(f"Using existing session: {session_id}")
        
        # Get the session
        session = chat_sessions[session_id]
        
        # Get global personal context (same for all sessions)
        personal_context_str = context_manager.format_context_for_llm()
        if personal_context_str:
            logger.info(f"Including global personal context ({len(personal_context_str)} chars)")
        else:
            logger.info("No personal context available")
        
        # Send message and get response
        logger.info("Sending message to Gemini...")
        try:
            response = session.send_message(request.message, personal_context_str)
            logger.info(f"Received response: {response[:100]}...")
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
        return ChatResponse(response=response, session_id=session_id)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/parse-schedule")
async def parse_schedule(image: UploadFile = File(...)):
    """Parse a schedule screenshot using Gemini Vision API"""
    try:
        logger.info("Parsing schedule from uploaded image")
        
        # Check API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
        # Read image
        image_bytes = await image.read()
        
        # Use Gemini Vision API (same client as chat pipeline)
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        prompt = """
        Extract ALL classes from this Rutgers WeReg weekly calendar schedule.
        
        This is a calendar grid with colored boxes representing classes.
        Each box contains:
        - Time range (e.g., "12:10 PM - 1:30 PM")
        - Course name (e.g., "DSGN&ANAL COMP ALGOR", "SOFTWARE METHODOLOGY", "LINEAR OPTIMIZATION")
        - Course code (e.g., "01:198:344:14:09944")
        - Location (e.g., "SEC-111", "LSH-A102")
        - Campus (indicated by color or text)
        
        Look at which COLUMN each colored box is in to determine the DAY:
        - Column 1 = Monday
        - Column 2 = Tuesday  
        - Column 3 = Wednesday
        - Column 4 = Thursday
        - Column 5 = Friday
        
        For EACH colored box/class, extract:
        - course: Full course name (e.g., "DSGN&ANAL COMP ALGOR" or "Design & Analysis of Computer Algorithms")
        - day: Full day name (Monday, Tuesday, Wednesday, Thursday, Friday)
        - time: Time range from the box (e.g., "12:10 PM - 1:30 PM")
        - location: Building and room (e.g., "SEC-111" or "LSH-A102")
        
        Return ONLY this JSON array:
        [
          {
            "course": "Design & Analysis of Computer Algorithms",
            "day": "Wednesday",
            "time": "12:10 PM - 1:30 PM",
            "location": "SEC-111"
          }
        ]
        
        IMPORTANT:
        - Create ONE entry for EACH class meeting time (if class meets Mon/Wed/Fri, that's 3 separate entries)
        - Use full day names (not abbreviations)
        - Extract the location from inside the colored box
        - Return ONLY the JSON array, nothing else
        """
        
        # Determine MIME type
        mime_type = image.content_type or "image/png"
        logger.info(f"Image MIME type: {mime_type}")
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Use gemini-2.0-flash-exp which supports vision
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(
                    role='user',
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                    ]
                )
            ]
        )
        
        # Parse the response
        response_text = response.text.strip()
        logger.info(f"Gemini response: {response_text[:500]}...")
        
        # Extract JSON from response (sometimes it's wrapped in markdown or has extra text)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Try to find JSON array if there's extra text
        if not response_text.startswith('['):
            # Look for [ to start of array
            if '[' in response_text:
                response_text = response_text[response_text.find('['):]
                if ']' in response_text:
                    response_text = response_text[:response_text.rfind(']')+1]
        
        try:
            schedules = json.loads(response_text)
            
            # Validate it's a list
            if not isinstance(schedules, list):
                raise ValueError("Response is not a JSON array")
            
            # Ensure each schedule has required fields
            for schedule in schedules:
                schedule.setdefault('course', '')
                schedule.setdefault('day', '')
                schedule.setdefault('time', '')
                schedule.setdefault('location', '')
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {response_text}")
            raise ValueError(f"Invalid JSON response from AI: {str(e)}")
        
        logger.info(f"Successfully parsed {len(schedules)} classes")
        
        return {
            "success": True,
            "schedules": schedules,
            "count": len(schedules)
        }
        
    except Exception as e:
        logger.error(f"Error parsing schedule: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to parse schedule: {str(e)}")

@app.get("/api/list-models")
async def list_models():
    """List available Gemini models"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="API key not found")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append({
                    'name': m.name,
                    'display_name': m.display_name,
                    'description': m.description,
                    'methods': m.supported_generation_methods
                })
        
        return {"models": models}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-parse")
async def test_parse():
    """Test endpoint that returns mock schedule data"""
    return {
        "success": True,
        "schedules": [
            {
                "course": "CS 112 Data Structures",
                "day": "Monday",
                "time": "10:00 AM - 11:20 AM",
                "location": "Hill Center 114"
            },
            {
                "course": "CS 112 Data Structures",
                "day": "Wednesday",
                "time": "10:00 AM - 11:20 AM",
                "location": "Hill Center 114"
            },
            {
                "course": "MATH 251 Calculus III",
                "day": "Tuesday",
                "time": "2:00 PM - 3:20 PM",
                "location": "SEC 202"
            },
            {
                "course": "MATH 251 Calculus III",
                "day": "Thursday",
                "time": "2:00 PM - 3:20 PM",
                "location": "SEC 202"
            }
        ],
        "count": 4
    }

@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech audio to text using Whisper"""
    try:
        if not VOICE_AVAILABLE or whisper_model is None:
            raise HTTPException(status_code=503, detail="Speech-to-text service not available")
        
        # Read audio file
        audio_bytes = await audio.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name
        
        try:
            # Transcribe with Whisper
            result = whisper_model.transcribe(temp_path, language="en", fp16=False)
            transcript = result["text"].strip()
            
            if not transcript:
                raise HTTPException(status_code=400, detail="No speech detected in audio")
            
            logger.info(f"Transcribed: {transcript[:100]}...")
            return {"text": transcript}
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Speech-to-text failed: {str(e)}")

@app.post("/api/text-to-speech")
async def text_to_speech(text: str = Form(...), voice_id: Optional[str] = Form(None)):
    """Convert text to speech using ElevenLabs"""
    try:
        if not VOICE_AVAILABLE or eleven_client is None:
            raise HTTPException(status_code=503, detail="Text-to-speech service not available")
        
        # Get default voice if not specified
        if voice_id is None:
            voices = eleven_client.voices.get_all().voices
            if not voices:
                raise HTTPException(status_code=500, detail="No voices available")
            voice_id = voices[0].voice_id
        
        logger.info(f"Generating speech for text: {text[:100]}...")
        
        # Generate audio
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2"
        )
        
        # Collect audio bytes
        audio_bytes = b"".join(audio_generator)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
