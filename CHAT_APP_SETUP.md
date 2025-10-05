# RU Assistant Chat Application Setup Guide

This guide will help you set up and run the complete chat application with both backend and frontend.

## Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- Gemini API key ([Get one here](https://ai.google.dev/))

## Quick Start

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create .env file with your Gemini API key
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_api_key_here

# Start the server
python main.py
```

The backend will run on `http://localhost:8000`

### 2. Frontend Setup

Open a new terminal:

```bash
# Navigate to frontend directory
cd chat-frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

The frontend will run on `http://localhost:3000`

### 3. Use the Application

1. Open your browser to `http://localhost:3000`
2. Start chatting! (The API key is loaded from the backend's `.env` file)

## Application Features

### Frontend
- **Clean UI**: Modern dark theme with red accent glow
- **Real-time Chat**: Instant responses from the AI
- **Message History**: See your conversation history
- **Loading States**: Visual feedback while waiting for responses
- **Responsive Design**: Works on mobile and desktop
- **No Setup Required**: API key is managed by the backend

### Backend
- **FastAPI**: High-performance async API
- **Gemini Integration**: Direct connection to your Gemini chat pipeline
- **CORS Enabled**: Cross-origin requests supported
- **Error Handling**: Robust error responses

## Project Structure

```
RU_AI_Assistant/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── requirements.txt     # Python dependencies
│   └── README.md           # Backend docs
├── chat-frontend/
│   ├── src/
│   │   ├── App.tsx         # Main chat component
│   │   ├── App.css         # Chat styles
│   │   ├── index.css       # Global styles
│   │   └── main.tsx        # Entry point
│   ├── package.json        # Node dependencies
│   └── README.md          # Frontend docs
└── gemini/
    └── chat_pipeline_class.py  # Gemini AI integration
```

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Kill the process using port 8000
lsof -ti:8000 | xargs kill -9

# Or change the port in main.py
uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Import errors:**
```bash
# Make sure you're in the backend directory
cd backend
pip install -r requirements.txt
```

### Frontend Issues

**Port 3000 already in use:**
```bash
# Kill the process or change the port in vite.config.ts
# The dev server will prompt you to use a different port
```

**Module not found errors:**
```bash
# Delete node_modules and reinstall
rm -rf node_modules
npm install
```

### Connection Issues

**CORS errors:**
- Make sure the backend is running on port 8000
- Check that CORS middleware is configured in `backend/main.py`

**API Key errors:**
- Check that `GEMINI_API_KEY` is set correctly in `backend/.env`
- Verify your Gemini API key is valid
- Restart the backend after updating the `.env` file

## Production Deployment

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd chat-frontend
npm run build
npm run preview
```

For production, consider:
- Using a reverse proxy (nginx)
- Setting up HTTPS
- Restricting CORS to specific origins
- Using environment variables for configuration

## API Documentation

Once the backend is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Support

For issues or questions:
1. Check the README files in backend/ and chat-frontend/
2. Review the troubleshooting section above
3. Check console logs for error messages
