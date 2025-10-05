# RU Assistant Backend

FastAPI backend server that connects the frontend to the Gemini AI chat pipeline.

## Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up Gemini API:**
Create a `.env` file in the `backend` directory:
```bash
cp .env.example .env
```

Then edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Running the Server

Start the FastAPI server:

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --reload
```

The server will run on `http://localhost:8000`

## API Endpoints

### `GET /`
Health check endpoint

**Response:**
```json
{
  "message": "RU Assistant API is running"
}
```

### `POST /api/chat`
Send a message to the RU Assistant

**Request Body:**
```json
{
  "message": "What's for lunch at Busch dining hall?",
  "api_key": "your-gemini-api-key"
}
```

**Response:**
```json
{
  "response": "AI assistant response here..."
}
```

## CORS Configuration

The server is configured to allow all origins for development. For production, update the `allow_origins` in `main.py` to specific domains.

## Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- Pydantic: Data validation
- google-genai: Gemini AI integration
