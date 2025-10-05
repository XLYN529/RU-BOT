import { useState } from 'react'
import axios from 'axios'
import './PersonalContextModal.css'

interface PersonalContextModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId?: string | null  // Optional - no longer used but kept for backwards compatibility
}

type ContextType = 'schedule' | 'assignment' | 'note' | 'preference' | null

export default function PersonalContextModal({ isOpen, onClose }: PersonalContextModalProps) {
  const [step, setStep] = useState<'select' | 'form' | 'view'>('select')
  const [contextType, setContextType] = useState<ContextType>(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  // Form states
  const [scheduleData, setScheduleData] = useState({ course: '', day: '', time: '', location: '' })
  const [assignmentData, setAssignmentData] = useState({ title: '', due_date: '', course: '', description: '' })
  const [noteData, setNoteData] = useState({ content: '', category: 'general' })
  const [preferenceData, setPreferenceData] = useState({ key: '', value: '' })
  const [uploadMode, setUploadMode] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [parsedSchedules, setParsedSchedules] = useState<any[]>([])
  const [showReviewTable, setShowReviewTable] = useState(false)
  
  // View current context state
  const [currentContext, setCurrentContext] = useState<any>(null)
  const [loadingContext, setLoadingContext] = useState(false)

  if (!isOpen) return null

  const handleSelectType = (type: ContextType) => {
    setContextType(type)
    setStep('form')
  }

  const handleBack = () => {
    setStep('select')
    setContextType(null)
    setSuccess(false)
    setUploadMode(false)
    setShowReviewTable(false)
    setParsedSchedules([])
    setCurrentContext(null)
  }

  const handleViewContext = async () => {
    setLoadingContext(true)
    setStep('view')
    try {
      const response = await axios.get('http://localhost:8000/api/context')
      setCurrentContext(response.data.context)
    } catch (error) {
      console.error('Error loading context:', error)
      alert('Failed to load context')
    } finally {
      setLoadingContext(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setParsing(true)

    try {
      const formData = new FormData()
      formData.append('image', file)

      const response = await axios.post('http://localhost:8000/api/parse-schedule', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (response.data.success && response.data.schedules) {
        setParsedSchedules(response.data.schedules)
        setShowReviewTable(true)
      }
    } catch (error: any) {
      console.error('Error parsing schedule:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Unknown error'
      alert(`❌ Failed to parse schedule: ${errorMsg}\n\nPlease try manual entry or a different image.`)
    } finally {
      setParsing(false)
    }
  }

  const handleScheduleEdit = (index: number, field: string, value: string) => {
    const updated = [...parsedSchedules]
    updated[index][field] = value
    setParsedSchedules(updated)
  }

  const handleRemoveSchedule = (index: number) => {
    setParsedSchedules(parsedSchedules.filter((_, i) => i !== index))
  }

  const handleSubmitSchedules = async () => {
    setLoading(true)
    try {
      // Save all schedules to global context
      for (const schedule of parsedSchedules) {
        await axios.post('http://localhost:8000/api/context', {
          context_type: 'schedule',
          data: schedule
        })
      }
      
      setSuccess(true)
      setTimeout(() => {
        handleClose()
      }, 1500)
    } catch (error) {
      console.error('Error saving schedules:', error)
      alert('❌ Failed to save schedules')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setStep('select')
    setContextType(null)
    setSuccess(false)
    setScheduleData({ course: '', day: '', time: '', location: '' })
    setAssignmentData({ title: '', due_date: '', course: '', description: '' })
    setNoteData({ content: '', category: 'general' })
    setPreferenceData({ key: '', value: '' })
    setUploadMode(false)
    setShowReviewTable(false)
    setParsedSchedules([])
    onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    setLoading(true)
    try {
      let data = {}
      
      switch (contextType) {
        case 'schedule':
          data = scheduleData
          break
        case 'assignment':
          data = assignmentData
          break
        case 'note':
          data = noteData
          break
        case 'preference':
          data = preferenceData
          break
      }

      await axios.post('http://localhost:8000/api/context', {
        context_type: contextType,
        data: data
      })

      setSuccess(true)
      setTimeout(() => {
        handleClose()
      }, 1500)
    } catch (error) {
      console.error('Error saving context:', error)
      alert('Failed to save context. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">
            {step === 'select' ? 'Personal Context' : step === 'view' ? 'Current Context' : 'Enter Details'}
          </h2>
          <button onClick={handleClose} className="modal-close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="modal-content">
          {success ? (
            <div className="success-container">
              <div className="success-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="success-text">Context Added Successfully!</p>
            </div>
          ) : step === 'select' ? (
            <div className="type-selector">
              <button onClick={handleViewContext} className="type-option view-context">
                <div className="type-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                </div>
                <div className="type-info">
                  <h3>View Current Context</h3>
                  <p>See all saved information</p>
                </div>
              </button>
              
              <button onClick={() => handleSelectType('schedule')} className="type-option">
                <div className="type-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                  </svg>
                </div>
                <div className="type-info">
                  <h3>Class Schedule</h3>
                  <p>Add your class times and locations</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('assignment')} className="type-option">
                <div className="type-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                </div>
                <div className="type-info">
                  <h3>Assignment</h3>
                  <p>Track deadlines and coursework</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('note')} className="type-option">
                <div className="type-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 17h.01"></path>
                    <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"></path>
                    <path d="M12 6v5"></path>
                  </svg>
                </div>
                <div className="type-info">
                  <h3>Personal Note</h3>
                  <p>Save reminders and important info</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('preference')} className="type-option">
                <div className="type-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v6m0 6v6m5.196-15.196l-4.242 4.242m-5.908 5.908l-4.242 4.242M23 12h-6m-6 0H1m15.196 5.196l-4.242-4.242m-5.908-5.908l-4.242-4.242"></path>
                  </svg>
                </div>
                <div className="type-info">
                  <h3>Preference</h3>
                  <p>Set your personal preferences</p>
                </div>
              </button>
            </div>
          ) : step === 'view' ? (
            <div style={{maxHeight: '500px', overflowY: 'auto'}}>
              {loadingContext ? (
                <div style={{textAlign: 'center', padding: '40px'}}>Loading...</div>
              ) : !currentContext ? (
                <div style={{textAlign: 'center', padding: '40px'}}>No context available</div>
              ) : (
                <>
                  {/* Schedule */}
                  {currentContext.schedule && currentContext.schedule.length > 0 && (
                    <div className="context-section">
                      <div className="context-section-header">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                          <line x1="16" y1="2" x2="16" y2="6"></line>
                          <line x1="8" y1="2" x2="8" y2="6"></line>
                          <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        <h3>Class Schedule ({currentContext.schedule.length})</h3>
                      </div>
                      <div className="context-section-content">
                        {currentContext.schedule.map((item: any, index: number) => (
                          <div key={index} className="context-item">
                            <div className="context-item-title">{item.course}</div>
                            <div className="context-item-detail">{item.day} • {item.time}</div>
                            {item.location && (
                              <div className="context-item-detail">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{display: 'inline', marginRight: '4px'}}>
                                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                                  <circle cx="12" cy="10" r="3"></circle>
                                </svg>
                                {item.location}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Assignments */}
                  {currentContext.assignments && currentContext.assignments.length > 0 && (
                    <div className="context-section">
                      <div className="context-section-header">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                          <line x1="16" y1="13" x2="8" y2="13"></line>
                          <line x1="16" y1="17" x2="8" y2="17"></line>
                        </svg>
                        <h3>Assignments ({currentContext.assignments.length})</h3>
                      </div>
                      <div className="context-section-content">
                        {currentContext.assignments.map((item: any, index: number) => (
                          <div key={index} className="context-item">
                            <div className="context-item-title">{item.title}</div>
                            <div className="context-item-detail">Due: {item.due_date}</div>
                            {item.course && <div className="context-item-detail">Course: {item.course}</div>}
                            {item.description && <div className="context-item-description">{item.description}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {currentContext.notes && currentContext.notes.length > 0 && (
                    <div className="context-section">
                      <div className="context-section-header">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 17h.01"></path>
                          <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"></path>
                          <path d="M12 6v5"></path>
                        </svg>
                        <h3>Notes ({currentContext.notes.length})</h3>
                      </div>
                      <div className="context-section-content">
                        {currentContext.notes.map((item: any, index: number) => (
                          <div key={index} className="context-item">
                            <div className="context-item-category">[{item.category}]</div>
                            <div className="context-item-content">{item.content}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Preferences */}
                  {currentContext.preferences && Object.keys(currentContext.preferences).length > 0 && (
                    <div className="context-section">
                      <div className="context-section-header">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="3"></circle>
                          <path d="M12 1v6m0 6v6m5.196-15.196l-4.242 4.242m-5.908 5.908l-4.242 4.242M23 12h-6m-6 0H1m15.196 5.196l-4.242-4.242m-5.908-5.908l-4.242-4.242"></path>
                        </svg>
                        <h3>Preferences ({Object.keys(currentContext.preferences).length})</h3>
                      </div>
                      <div className="context-section-content">
                        {Object.entries(currentContext.preferences).map(([key, value]: [string, any], index: number) => (
                          <div key={index} className="context-item">
                            <div className="context-item-title">{key}</div>
                            <div className="context-item-detail">{value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(!currentContext.schedule || currentContext.schedule.length === 0) && 
                   (!currentContext.assignments || currentContext.assignments.length === 0) &&
                   (!currentContext.notes || currentContext.notes.length === 0) &&
                   (!currentContext.preferences || Object.keys(currentContext.preferences).length === 0) && (
                    <div className="empty-state">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                      </svg>
                      <p>No personal context added yet.</p>
                      <p style={{fontSize: '14px', opacity: '0.7'}}>Add your schedule, assignments, or preferences to get started!</p>
                    </div>
                  )}
                </>
              )}

              <div className="form-actions">
                <button type="button" onClick={handleBack} className="btn btn-secondary">
                  Back
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="modal-form">
              {contextType === 'schedule' && (
                <>
                  {showReviewTable ? (
                    <>
                      <div className="review-section">
                        <h3 className="review-title">
                          Review & Edit Your Classes ({parsedSchedules.length})
                        </h3>
                        <div className="table-wrapper">
                          <table className="review-table">
                            <thead>
                              <tr>
                                <th>Course</th>
                                <th>Day</th>
                                <th>Time</th>
                                <th>Location</th>
                                <th className="remove-col">Remove</th>
                              </tr>
                            </thead>
                            <tbody>
                              {parsedSchedules.map((schedule, index) => (
                                <tr key={index}>
                                  <td>
                                    <input
                                      type="text"
                                      value={schedule.course}
                                      onChange={(e) => handleScheduleEdit(index, 'course', e.target.value)}
                                      className="table-input"
                                    />
                                  </td>
                                  <td>
                                    <select
                                      value={schedule.day}
                                      onChange={(e) => handleScheduleEdit(index, 'day', e.target.value)}
                                      className="table-select"
                                    >
                                      <option value="">Select</option>
                                      <option value="Monday">Monday</option>
                                      <option value="Tuesday">Tuesday</option>
                                      <option value="Wednesday">Wednesday</option>
                                      <option value="Thursday">Thursday</option>
                                      <option value="Friday">Friday</option>
                                      <option value="Saturday">Saturday</option>
                                      <option value="Sunday">Sunday</option>
                                    </select>
                                  </td>
                                  <td>
                                    <input
                                      type="text"
                                      value={schedule.time}
                                      onChange={(e) => handleScheduleEdit(index, 'time', e.target.value)}
                                      placeholder="10:00 AM - 11:20 AM"
                                      className="table-input"
                                    />
                                  </td>
                                  <td>
                                    <input
                                      type="text"
                                      value={schedule.location}
                                      onChange={(e) => handleScheduleEdit(index, 'location', e.target.value)}
                                      placeholder="Hill Center 114"
                                      className="table-input"
                                    />
                                  </td>
                                  <td className="remove-col">
                                    <button
                                      type="button"
                                      onClick={() => handleRemoveSchedule(index)}
                                      className="remove-btn"
                                    >
                                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <line x1="18" y1="6" x2="6" y2="18"></line>
                                        <line x1="6" y1="6" x2="18" y2="18"></line>
                                      </svg>
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      <div className="form-actions">
                        <button type="button" onClick={() => { setShowReviewTable(false); setParsedSchedules([]) }} className="btn btn-secondary">
                          Cancel
                        </button>
                        <button type="button" onClick={handleSubmitSchedules} disabled={loading} className="btn btn-primary">
                          {loading ? 'Saving...' : `Save ${parsedSchedules.length} Classes`}
                        </button>
                      </div>
                    </>
                  ) : !uploadMode ? (
                    <>
                      <div className="upload-section">
                        <p className="upload-instructions">Upload a screenshot of your schedule</p>
                        <label className="btn btn-primary upload-btn">
                          {parsing ? (
                            <>
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="spinning">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                              </svg>
                              Parsing...
                            </>
                          ) : (
                            <>
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="17 8 12 3 7 8"></polyline>
                                <line x1="12" y1="3" x2="12" y2="15"></line>
                              </svg>
                              Upload Schedule Screenshot
                            </>
                          )}
                          <input
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            disabled={parsing}
                            style={{ display: 'none' }}
                          />
                        </label>
                        <p className="upload-divider">or</p>
                        <button
                          type="button"
                          onClick={() => setUploadMode(true)}
                          className="btn btn-secondary"
                        >
                          Enter Manually
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="form-label">Course Name *</label>
                        <input
                          type="text"
                          required
                          value={scheduleData.course}
                          onChange={(e) => setScheduleData({ ...scheduleData, course: e.target.value })}
                          placeholder="e.g., CS 112 Data Structures"
                          className="form-input"
                        />
                      </div>
                  <div>
                    <label className="form-label">Day *</label>
                    <select
                      required
                      value={scheduleData.day}
                      onChange={(e) => setScheduleData({ ...scheduleData, day: e.target.value })}
                      className="form-input"
                    >
                      <option value="">Select day</option>
                      <option value="Monday">Monday</option>
                      <option value="Tuesday">Tuesday</option>
                      <option value="Wednesday">Wednesday</option>
                      <option value="Thursday">Thursday</option>
                      <option value="Friday">Friday</option>
                      <option value="Saturday">Saturday</option>
                      <option value="Sunday">Sunday</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Time *</label>
                    <input
                      type="text"
                      required
                      value={scheduleData.time}
                      onChange={(e) => setScheduleData({ ...scheduleData, time: e.target.value })}
                      placeholder="e.g., 10:00 AM - 11:20 AM"
                      className="form-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Location</label>
                    <input
                      type="text"
                      value={scheduleData.location}
                      onChange={(e) => setScheduleData({ ...scheduleData, location: e.target.value })}
                      placeholder="e.g., Hill Center 114"
                      className="form-input"
                    />
                  </div>
                  </>
                  )}
                </>
              )}

              {contextType === 'assignment' && (
                <>
                  <div>
                    <label className="form-label">Assignment Title *</label>
                    <input
                      type="text"
                      required
                      value={assignmentData.title}
                      onChange={(e) => setAssignmentData({ ...assignmentData, title: e.target.value })}
                      placeholder="e.g., Project 2 - Binary Trees"
                      className="form-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Due Date *</label>
                    <input
                      type="date"
                      required
                      value={assignmentData.due_date}
                      onChange={(e) => setAssignmentData({ ...assignmentData, due_date: e.target.value })}
                      className="form-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Course</label>
                    <input
                      type="text"
                      value={assignmentData.course}
                      onChange={(e) => setAssignmentData({ ...assignmentData, course: e.target.value })}
                      placeholder="e.g., CS 112"
                      className="form-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Description</label>
                    <textarea
                      value={assignmentData.description}
                      onChange={(e) => setAssignmentData({ ...assignmentData, description: e.target.value })}
                      placeholder="Additional details..."
                      rows={3}
                      className="form-textarea"
                    />
                  </div>
                </>
              )}

              {contextType === 'note' && (
                <>
                  <div>
                    <label className="form-label">Note *</label>
                    <textarea
                      required
                      value={noteData.content}
                      onChange={(e) => setNoteData({ ...noteData, content: e.target.value })}
                      placeholder="e.g., I prefer vegetarian food options"
                      rows={4}
                      className="form-textarea"
                    />
                  </div>
                  <div>
                    <label className="form-label">Category</label>
                    <select
                      value={noteData.category}
                      onChange={(e) => setNoteData({ ...noteData, category: e.target.value })}
                      className="form-select"
                    >
                      <option value="general">General</option>
                      <option value="dietary">Dietary</option>
                      <option value="academic">Academic</option>
                      <option value="personal">Personal</option>
                    </select>
                  </div>
                </>
              )}

              {contextType === 'preference' && (
                <>
                  <div>
                    <label className="form-label">Preference Name *</label>
                    <input
                      type="text"
                      required
                      value={preferenceData.key}
                      onChange={(e) => setPreferenceData({ ...preferenceData, key: e.target.value })}
                      placeholder="e.g., favorite_dining_hall"
                      className="form-input"
                    />
                  </div>
                  <div>
                    <label className="form-label">Value *</label>
                    <input
                      type="text"
                      required
                      value={preferenceData.value}
                      onChange={(e) => setPreferenceData({ ...preferenceData, value: e.target.value })}
                      placeholder="e.g., Busch Dining Hall"
                      className="form-input"
                    />
                  </div>
                </>
              )}

              <div className="form-actions">
                <button type="button" onClick={handleBack} className="btn btn-secondary">
                  Back
                </button>
                <button type="submit" disabled={loading} className="btn btn-primary">
                  {loading ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
