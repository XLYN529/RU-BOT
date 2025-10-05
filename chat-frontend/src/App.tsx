import { useState, useEffect, useRef, FormEvent, KeyboardEvent } from 'react'
import axios from 'axios'
import './App.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const newChat = () => {
    setMessages([])
    setSessionId(null)
  }

  const addPersonalContext = () => {
    // TODO: Implement personal context functionality
    alert('Personal context feature coming soon!')
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message to state
    const newUserMessage = { role: 'user' as const, content: userMessage }
    setMessages(prev => [...prev, newUserMessage])
    setLoading(true)

    try {
      // Send message with session ID (backend maintains full conversation history)
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: userMessage,
        session_id: sessionId
      })

      // Store session ID from response (for first message or new session)
      if (response.data.session_id && response.data.session_id !== sessionId) {
        setSessionId(response.data.session_id)
      }

      // Add assistant response to state
      setMessages(prev => [...prev, { role: 'assistant' as const, content: response.data.response }])
    } catch (error: any) {
      console.error('Error:', error)
      
      // Extract detailed error message
      let errorMessage = 'Sorry, there was an error processing your request.'
      
      if (error.response?.data?.detail) {
        errorMessage += `\n\nError: ${error.response.data.detail}`
      } else if (error.message) {
        errorMessage += `\n\nError: ${error.message}`
      }
      
      console.error('Full error details:', {
        response: error.response?.data,
        status: error.response?.status,
        message: error.message
      })
      
      setMessages(prev => [...prev, { 
        role: 'assistant' as const, 
        content: errorMessage
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    sendMessage()
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="sidebar-header">
          <button 
            className="toggle-button"
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            title={sidebarExpanded ? 'Minimize sidebar' : 'Maximize sidebar'}
          >
            {sidebarExpanded ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 18l-6-6 6-6"/>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            )}
          </button>
          {sidebarExpanded && <span className="sidebar-title">RU Assistant</span>}
        </div>

        <button className="personal-context-button" onClick={addPersonalContext}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          {sidebarExpanded && <span>Add Personal Context</span>}
        </button>

        <button className="new-chat-button" onClick={newChat}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          {sidebarExpanded && <span>New Chat</span>}
        </button>

        {sidebarExpanded && (
          <div className="sidebar-section">
            <div className="section-title">About</div>
            <div className="section-content">
              Your Rutgers University AI assistant for dining, events, gym hours, and more!
            </div>
          </div>
        )}
      </div>

      <div className={`chat-container ${sidebarExpanded ? 'with-sidebar-expanded' : 'with-sidebar-collapsed'}`}>
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <h1 className="title">Find what YOU need?</h1>
            <p className="subtitle">Ask anything about Rutgers University while having context of your own personal info</p>
            <form onSubmit={handleSubmit} className="input-container">
              <div className="input-wrapper">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything..."
                  className="input-field"
                  rows={2}
                  disabled={loading}
                />
                <button 
                  type="submit" 
                  className="send-button"
                  disabled={loading || !input.trim()}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                  </svg>
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.role}`}>
                  <div className="message-content">
                    {message.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="message assistant">
                  <div className="message-content loading">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="input-container">
              <div className="input-wrapper">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything..."
                  className="input-field"
                  rows={2}
                  disabled={loading}
                />
                <button 
                  type="submit" 
                  className="send-button"
                  disabled={loading || !input.trim()}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                  </svg>
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

export default App
