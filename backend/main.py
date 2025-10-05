from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Optional
import os
import sys
import uuid
import traceback
import logging

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

# Store active chat sessions in memory
chat_sessions: Dict[str, ChatSession] = {}

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

@app.get("/")
async def root():
    return {"message": "RU Assistant API is running"}

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
        
        # Send message and get response
        logger.info("Sending message to Gemini...")
        try:
            response = session.send_message(request.message)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
