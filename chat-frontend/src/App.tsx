import { useState, useEffect, useRef, FormEvent, KeyboardEvent } from 'react'
import axios from 'axios'
import './App.css'
import PersonalContextModal from './components/PersonalContextModal'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [queryStatus, setQueryStatus] = useState<string | null>(null)
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [volumeLevel, setVolumeLevel] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const streamingResponseRef = useRef<string>('')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSession = localStorage.getItem('ru_assistant_session')
    if (savedSession) {
      setSessionId(savedSession)
      console.log('Restored session:', savedSession)
    }
  }, [])

  // Save session to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('ru_assistant_session', sessionId)
      console.log('Saved session:', sessionId)
    }
  }, [sessionId])

  const newChat = () => {
    setMessages([])
    setSessionId(null)
    localStorage.removeItem('ru_assistant_session')
    console.log('Started new chat - cleared session')
  }

  const addPersonalContext = () => {
    // Personal context is now global - no session required
    setModalOpen(true)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const sendMessage = async (messageText?: string, shouldSpeak: boolean = false) => {
    const userMessage = (messageText || input).trim()
    if (!userMessage || loading) return

    if (!messageText) setInput('')
    
    // Add user message to state
    const newUserMessage = { role: 'user' as const, content: userMessage }
    setMessages(prev => [...prev, newUserMessage])
    setLoading(true)
    setQueryStatus('Thinking...')

    // Update status after a short delay to show querying
    const queryTimer = setTimeout(() => {
      setQueryStatus('Querying databases...')
    }, 500)

    try {
      // Use streaming endpoint
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          voice_mode: shouldSpeak
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('No response body')
      }

      streamingResponseRef.current = ''
      let receivedSessionId = sessionId
      let buffer = '' // Buffer for incomplete SSE messages
      let hasStartedStreaming = false

      // Read the stream
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true })
        
        // Split by double newline (SSE message separator)
        const sseMessages = buffer.split('\n\n')
        
        // Keep the last incomplete message in the buffer
        buffer = sseMessages.pop() || ''
        
        // Process complete messages
        for (const message of sseMessages) {
          const lines = message.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                // Handle session_id
                if (data.session_id) {
                  receivedSessionId = data.session_id
                  if (receivedSessionId !== sessionId) {
                    setSessionId(receivedSessionId)
                  }
                }
                
                // Handle content chunks
                if (data.chunk) {
                  // First chunk - clear status and add message container
                  if (!hasStartedStreaming) {
                    hasStartedStreaming = true
                    clearTimeout(queryTimer)
                    setQueryStatus(null)
                    setLoading(false)
                    setMessages(prev => [...prev, { role: 'assistant' as const, content: '' }])
                  }
                  
                  // Add chunk character by character for smooth typing effect
                  const chunkText = data.chunk
                  for (let i = 0; i < chunkText.length; i++) {
                    streamingResponseRef.current += chunkText[i]
                    setMessages(prev => {
                      const newMessages = [...prev]
                      if (newMessages.length > 0) {
                        newMessages[newMessages.length - 1] = {
                          role: 'assistant' as const,
                          content: streamingResponseRef.current
                        }
                      }
                      return newMessages
                    })
                    // Delay on every character for slower typing effect
                    await new Promise(resolve => setTimeout(resolve, 20))
                  }
                }
                
                // Handle errors
                if (data.error) {
                  throw new Error(data.error)
                }
                
                // Handle completion
                if (data.done) {
                  console.log('Stream completed:', streamingResponseRef.current.length, 'chars')
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', line, e)
              }
            }
          }
        }
      }

      // If voice mode, speak the complete response
      if (shouldSpeak && voiceMode && streamingResponseRef.current) {
        await speakText(streamingResponseRef.current)
      }

    } catch (error: any) {
      clearTimeout(queryTimer)
      console.error('Error:', error)
      
      // Extract detailed error message
      let errorMessage = 'Sorry, there was an error processing your request.'
      
      if (error.message) {
        errorMessage += `\n\nError: ${error.message}`
      }
      
      setMessages(prev => {
        // Remove the empty assistant message if it exists
        const filtered = prev.filter((msg, idx) => 
          !(idx === prev.length - 1 && msg.role === 'assistant' && msg.content === '')
        )
        return [...filtered, { 
          role: 'assistant' as const, 
          content: errorMessage
        }]
      })
    } finally {
      clearTimeout(queryTimer)
      setLoading(false)
      setQueryStatus(null)
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

  const speakText = async (text: string) => {
    try {
      setIsSpeaking(true)
      const formData = new FormData()
      formData.append('text', text)
      
      const response = await axios.post('http://localhost:8000/api/text-to-speech', formData, {
        responseType: 'blob'
      })
      
      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' })
      const audioUrl = URL.createObjectURL(audioBlob)
      
      if (audioRef.current) {
        audioRef.current.pause()
      }
      
      audioRef.current = new Audio(audioUrl)
      audioRef.current.onended = () => {
        setIsSpeaking(false)
        URL.revokeObjectURL(audioUrl)
      }
      audioRef.current.play()
    } catch (error) {
      console.error('TTS Error:', error)
      setIsSpeaking(false)
    }
  }

  const checkSilence = () => {
    if (!analyserRef.current) return
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)
    
    // Calculate average volume
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length
    
    // Update volume level for visual feedback (normalize to 0-1 range)
    const normalizedVolume = Math.min(average / 50, 1) // Scale: 50 = max expected volume
    setVolumeLevel(normalizedVolume)
    
    // Silence threshold
    const SILENCE_THRESHOLD = 5
    
    if (average < SILENCE_THRESHOLD) {
      // Start/reset silence timer
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
      }
      
      silenceTimerRef.current = setTimeout(() => {
        console.log('Silence detected - stopping recording')
        stopRecording()
      }, 5000) // 5 seconds of silence
    } else {
      // Clear silence timer if sound detected
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Setup audio context for silence detection
      audioContextRef.current = new AudioContext()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 2048
      source.connect(analyserRef.current)
      
      // Setup MediaRecorder
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        await transcribeAudio(audioBlob)
        
        // Cleanup
        stream.getTracks().forEach(track => track.stop())
        if (audioContextRef.current) {
          audioContextRef.current.close()
        }
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      
      // Start silence detection
      const silenceCheckInterval = setInterval(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          checkSilence()
        } else {
          clearInterval(silenceCheckInterval)
        }
      }, 100)
      
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Could not access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setVolumeLevel(0) // Reset volume level when stopping
      
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }
    }
  }

  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.wav')
      
      const response = await axios.post('http://localhost:8000/api/speech-to-text', formData)
      const transcribedText = response.data.text
      
      if (transcribedText) {
        // Send transcribed text as message and speak response
        await sendMessage(transcribedText, true)
      }
    } catch (error) {
      console.error('STT Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant' as const,
        content: 'Sorry, I could not understand the audio. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const toggleVoiceMode = () => {
    const newVoiceMode = !voiceMode
    setVoiceMode(newVoiceMode)
    
    // Stop any ongoing recording or speech
    if (!newVoiceMode) {
      if (isRecording) stopRecording()
      if (audioRef.current) {
        audioRef.current.pause()
        setIsSpeaking(false)
      }
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isRecording) stopRecording()
      if (audioRef.current) audioRef.current.pause()
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    }
  }, [])

  return (
    <>
      <PersonalContextModal 
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        sessionId={sessionId}
      />
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
          {sidebarExpanded && <span className="sidebar-title">RU BOT</span>}
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
            <h1 className="title">What's on your mind, Vinny?</h1>
            <p className="subtitle">Ask anything about Rutgers University while having context of your own personal info</p>
            <form onSubmit={handleSubmit} className="input-container">
              <div 
                className="input-wrapper"
                style={{
                  boxShadow: isRecording && volumeLevel > 0.1 
                    ? `0 0 ${20 + volumeLevel * 60}px rgba(204, 0, 51, ${0.2 + volumeLevel * 0.5}), 0 0 ${40 + volumeLevel * 80}px rgba(204, 0, 51, ${0.1 + volumeLevel * 0.3})`
                    : undefined
                }}
              >
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything..."
                  className="input-field"
                  rows={2}
                  disabled={loading || voiceMode}
                />
                <button
                  type="button"
                  className={`voice-button ${voiceMode ? 'active' : ''}`}
                  onClick={toggleVoiceMode}
                  title={voiceMode ? 'Switch to text mode' : 'Switch to voice mode'}
                >
                  {voiceMode ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                      <line x1="12" y1="19" x2="12" y2="23"></line>
                      <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                      <line x1="12" y1="19" x2="12" y2="23"></line>
                      <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                  )}
                </button>
                {voiceMode ? (
                  <button
                    type="button"
                    className={`record-button ${isRecording ? 'recording' : ''} ${isSpeaking ? 'speaking' : ''}`}
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={loading || isSpeaking}
                  >
                    {isRecording ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="12" r="10"></circle>
                      </svg>
                    )}
                  </button>
                ) : (
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
                )}
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.role}`}>
                  {message.role === 'user' ? (
                    <div className="message-content">{message.content}</div>
                  ) : (
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {message.content.split('\n').map((line, i) => {
                        // Format lists
                        if (line.trim().match(/^[-•]\s/)) {
                          return <div key={i} style={{ paddingLeft: '20px', marginBottom: '4px' }}>• {line.replace(/^[-•]\s/, '')}</div>
                        }
                        // Format numbered lists
                        if (line.trim().match(/^\d+\.\s/)) {
                          return <div key={i} style={{ paddingLeft: '20px', marginBottom: '4px' }}>{line}</div>
                        }
                        // Regular lines
                        return line.trim() ? <div key={i} style={{ marginBottom: '8px' }}>{line}</div> : <div key={i} style={{ height: '8px' }} />
                      })}
                    </div>
                  )}
                </div>
              ))}
              {queryStatus && (
                <div className="query-status">
                  <div className="gradient-loader"></div>
                  <span className="status-text">{queryStatus}</span>
                </div>
              )}
              {loading && !queryStatus && (
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
              <div 
                className="input-wrapper"
                style={{
                  boxShadow: isRecording && volumeLevel > 0.1 
                    ? `0 0 ${20 + volumeLevel * 60}px rgba(204, 0, 51, ${0.2 + volumeLevel * 0.5}), 0 0 ${40 + volumeLevel * 80}px rgba(204, 0, 51, ${0.1 + volumeLevel * 0.3})`
                    : undefined
                }}
              >
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything..."
                  className="input-field"
                  rows={2}
                  disabled={loading || voiceMode}
                />
                <button
                  type="button"
                  className={`voice-button ${voiceMode ? 'active' : ''}`}
                  onClick={toggleVoiceMode}
                  title={voiceMode ? 'Switch to text mode' : 'Switch to voice mode'}
                >
                  {voiceMode ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                      <line x1="12" y1="19" x2="12" y2="23"></line>
                      <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                      <line x1="12" y1="19" x2="12" y2="23"></line>
                      <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                  )}
                </button>
                {voiceMode ? (
                  <button
                    type="button"
                    className={`record-button ${isRecording ? 'recording' : ''} ${isSpeaking ? 'speaking' : ''}`}
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={loading || isSpeaking}
                  >
                    {isRecording ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="12" r="10"></circle>
                      </svg>
                    )}
                  </button>
                ) : (
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
                )}
              </div>
            </form>
          </>
        )}
      </div>
    </div>
    </>
  )
}

export default App
