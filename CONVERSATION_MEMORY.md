# Conversation Memory Implementation

## Overview
The chat application uses a **persistent session-based memory** system that maintains full conversation context using Gemini's native chat API.

## How It Works

### Frontend (React)
- Stores messages in React state for UI display
- Receives a `session_id` from backend on first message
- Sends `session_id` with each subsequent message
- No need to send conversation history - backend handles everything!

### Backend (FastAPI)
- Maintains active chat sessions in memory (dictionary)
- Each session has a unique `session_id` (UUID)
- Creates new `ChatSession` for first message
- Reuses existing `ChatSession` for subsequent messages
- Sessions persist across requests until server restart

### Gemini Pipeline (ChatSession class)
- Creates ONE persistent Gemini chat session per user
- Gemini's native API automatically maintains full conversation context
- No manual history replay needed - conversation memory is built-in
- **Unlimited conversation history** (no artificial limits!)
- Much more efficient and reliable than replaying history

## Benefits

✅ **Full Memory**: AI remembers ALL previous messages in the conversation
✅ **Efficient**: No replaying history - uses Gemini's native session management
✅ **Reliable**: No crashes from long conversations or memory queries
✅ **Fast**: Single API call per message, no context reconstruction
✅ **Simple**: Backend handles all memory, frontend just displays messages

## Example Conversation Flow

```
User: "What dining halls are on Busch campus?"
Assistant: [Lists dining halls]

User: "What are the hours for the first one?"
Assistant: [Remembers "first one" refers to the dining hall mentioned above]

User: "What about breakfast options?"
Assistant: [Understands context is still about that dining hall]
```

## Technical Details

### Message Format
```typescript
{
  role: 'user' | 'assistant',
  content: string
}
```

### API Request
```json
{
  "message": "Current user message",
  "session_id": "uuid-of-session"
}
```

### API Response
```json
{
  "response": "Assistant's response",
  "session_id": "uuid-of-session"
}
```

## Limitations

- Sessions stored in backend memory (lost on server restart)
- Sessions reset on page refresh (frontend loses session_id)
- No limit on conversation length (could grow large over time)

## Future Enhancements

- Add localStorage to persist session_id across page refreshes
- Add database/Redis for persistent session storage
- Implement session cleanup (auto-delete old/inactive sessions)
- Add session management UI (clear conversation, view history)
