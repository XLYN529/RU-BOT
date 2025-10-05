# RU Assistant Chat Frontend

A clean, modern React TypeScript chat interface for the RU Assistant with a beautiful dark theme and red glow effect.

## Features

- 🎨 Modern dark UI with red accent glow
- 💬 Real-time chat interface
- ⚡ Fast and responsive
- 🔒 API key managed securely by backend (.env file)
- 📱 Mobile responsive

## Setup

1. **Install dependencies:**
```bash
cd chat-frontend
npm install
```

2. **Start the development server:**
```bash
npm run dev
```

The app will run on `http://localhost:3000`

## Building for Production

```bash
npm run build
```

The production build will be in the `dist` folder.

## Preview Production Build

```bash
npm run preview
```

## Configuration

### Backend URL

The frontend connects to the backend at `http://localhost:8000`. To change this, update the axios URL in `src/App.tsx`:

```typescript
const response = await axios.post('http://localhost:8000/api/chat', {
  message: userMessage
})
```

### API Key

The Gemini API key is managed by the backend. Make sure to set `GEMINI_API_KEY` in the `backend/.env` file before starting the backend server.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Axios** - HTTP client
- **CSS3** - Styling with custom properties

## Project Structure

```
chat-frontend/
├── src/
│   ├── App.tsx          # Main chat component
│   ├── App.css          # Chat styles with red glow
│   ├── index.css        # Global styles
│   └── main.tsx         # App entry point
├── index.html           # HTML template
├── package.json         # Dependencies
├── tsconfig.json        # TypeScript config
└── vite.config.ts       # Vite config
```

## Usage

1. Set up the backend with your API key in `.env` (see backend/README.md)
2. Start the backend server
3. Start the frontend with `npm run dev`
4. Start chatting with the RU Assistant!

## Keyboard Shortcuts

- **Enter** - Send message
- **Shift + Enter** - New line in message
