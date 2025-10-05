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
              <button onClick={handleViewContext} className="type-option" style={{background: '#f0f9ff', borderColor: '#3b82f6'}}>
                <div className="type-icon" style={{background: '#3b82f6'}}>👁️</div>
                <div className="type-info">
                  <h3>View Current Context</h3>
                  <p>See all saved information</p>
                </div>
              </button>
              
              <button onClick={() => handleSelectType('schedule')} className="type-option">
                <div className="type-icon blue">📅</div>
                <div className="type-info">
                  <h3>Class Schedule</h3>
                  <p>Add your class times and locations</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('assignment')} className="type-option">
                <div className="type-icon purple">📝</div>
                <div className="type-info">
                  <h3>Assignment</h3>
                  <p>Track deadlines and coursework</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('note')} className="type-option">
                <div className="type-icon green">📌</div>
                <div className="type-info">
                  <h3>Personal Note</h3>
                  <p>Save reminders and preferences</p>
                </div>
              </button>

              <button onClick={() => handleSelectType('preference')} className="type-option">
                <div className="type-icon orange">⚙️</div>
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
                    <div style={{marginBottom: '24px'}}>
                      <h3 style={{fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#1f2937'}}>📅 Class Schedule ({currentContext.schedule.length})</h3>
                      <div style={{background: '#f9fafb', borderRadius: '8px', padding: '12px'}}>
                        {currentContext.schedule.map((item: any, index: number) => (
                          <div key={index} style={{padding: '8px', borderBottom: index < currentContext.schedule.length - 1 ? '1px solid #e5e7eb' : 'none'}}>
                            <div style={{fontWeight: '600', color: '#1f2937'}}>{item.course}</div>
                            <div style={{fontSize: '14px', color: '#6b7280'}}>{item.day} • {item.time}</div>
                            {item.location && <div style={{fontSize: '14px', color: '#6b7280'}}>📍 {item.location}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Assignments */}
                  {currentContext.assignments && currentContext.assignments.length > 0 && (
                    <div style={{marginBottom: '24px'}}>
                      <h3 style={{fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#1f2937'}}>📝 Assignments ({currentContext.assignments.length})</h3>
                      <div style={{background: '#f9fafb', borderRadius: '8px', padding: '12px'}}>
                        {currentContext.assignments.map((item: any, index: number) => (
                          <div key={index} style={{padding: '8px', borderBottom: index < currentContext.assignments.length - 1 ? '1px solid #e5e7eb' : 'none'}}>
                            <div style={{fontWeight: '600', color: '#1f2937'}}>{item.title}</div>
                            <div style={{fontSize: '14px', color: '#6b7280'}}>Due: {item.due_date}</div>
                            {item.course && <div style={{fontSize: '14px', color: '#6b7280'}}>Course: {item.course}</div>}
                            {item.description && <div style={{fontSize: '14px', color: '#6b7280', marginTop: '4px'}}>{item.description}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {currentContext.notes && currentContext.notes.length > 0 && (
                    <div style={{marginBottom: '24px'}}>
                      <h3 style={{fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#1f2937'}}>📌 Notes ({currentContext.notes.length})</h3>
                      <div style={{background: '#f9fafb', borderRadius: '8px', padding: '12px'}}>
                        {currentContext.notes.map((item: any, index: number) => (
                          <div key={index} style={{padding: '8px', borderBottom: index < currentContext.notes.length - 1 ? '1px solid #e5e7eb' : 'none'}}>
                            <div style={{fontSize: '12px', color: '#6b7280', marginBottom: '4px'}}>[{item.category}]</div>
                            <div style={{color: '#1f2937'}}>{item.content}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Preferences */}
                  {currentContext.preferences && Object.keys(currentContext.preferences).length > 0 && (
                    <div style={{marginBottom: '24px'}}>
                      <h3 style={{fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#1f2937'}}>⚙️ Preferences ({Object.keys(currentContext.preferences).length})</h3>
                      <div style={{background: '#f9fafb', borderRadius: '8px', padding: '12px'}}>
                        {Object.entries(currentContext.preferences).map(([key, value]: [string, any], index: number) => (
                          <div key={index} style={{padding: '8px', borderBottom: index < Object.keys(currentContext.preferences).length - 1 ? '1px solid #e5e7eb' : 'none'}}>
                            <div style={{fontWeight: '600', color: '#1f2937'}}>{key}</div>
                            <div style={{fontSize: '14px', color: '#6b7280'}}>{value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(!currentContext.schedule || currentContext.schedule.length === 0) && 
                   (!currentContext.assignments || currentContext.assignments.length === 0) &&
                   (!currentContext.notes || currentContext.notes.length === 0) &&
                   (!currentContext.preferences || Object.keys(currentContext.preferences).length === 0) && (
                    <div style={{textAlign: 'center', padding: '40px', color: '#6b7280'}}>
                      No personal context added yet. Add your schedule, assignments, or preferences to get started!
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
                      <div style={{ marginBottom: '16px' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                          Review & Edit Your Classes ({parsedSchedules.length})
                        </h3>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                            <thead>
                              <tr style={{ background: '#f3f4f6', borderBottom: '2px solid #e5e7eb' }}>
                                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600' }}>Course</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600' }}>Day</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600' }}>Time</th>
                                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: '600' }}>Location</th>
                                <th style={{ padding: '12px 8px', textAlign: 'center', fontWeight: '600', width: '60px' }}>Remove</th>
                              </tr>
                            </thead>
                            <tbody>
                              {parsedSchedules.map((schedule, index) => (
                                <tr key={index} style={{ borderBottom: '1px solid #e5e7eb' }}>
                                  <td style={{ padding: '8px' }}>
                                    <input
                                      type="text"
                                      value={schedule.course}
                                      onChange={(e) => handleScheduleEdit(index, 'course', e.target.value)}
                                      style={{ width: '100%', padding: '6px', border: '1px solid #e5e7eb', borderRadius: '4px', fontSize: '14px' }}
                                    />
                                  </td>
                                  <td style={{ padding: '8px' }}>
                                    <select
                                      value={schedule.day}
                                      onChange={(e) => handleScheduleEdit(index, 'day', e.target.value)}
                                      style={{ width: '100%', padding: '6px', border: '1px solid #e5e7eb', borderRadius: '4px', fontSize: '14px' }}
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
                                  <td style={{ padding: '8px' }}>
                                    <input
                                      type="text"
                                      value={schedule.time}
                                      onChange={(e) => handleScheduleEdit(index, 'time', e.target.value)}
                                      placeholder="10:00 AM - 11:20 AM"
                                      style={{ width: '100%', padding: '6px', border: '1px solid #e5e7eb', borderRadius: '4px', fontSize: '14px' }}
                                    />
                                  </td>
                                  <td style={{ padding: '8px' }}>
                                    <input
                                      type="text"
                                      value={schedule.location}
                                      onChange={(e) => handleScheduleEdit(index, 'location', e.target.value)}
                                      placeholder="Hill Center 114"
                                      style={{ width: '100%', padding: '6px', border: '1px solid #e5e7eb', borderRadius: '4px', fontSize: '14px' }}
                                    />
                                  </td>
                                  <td style={{ padding: '8px', textAlign: 'center' }}>
                                    <button
                                      type="button"
                                      onClick={() => handleRemoveSchedule(index)}
                                      style={{ padding: '4px 8px', background: '#fee', color: '#dc2626', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                                    >
                                      ✕
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
                      <div style={{ textAlign: 'center', padding: '20px', background: '#f9fafb', borderRadius: '8px', marginBottom: '20px' }}>
                        <p style={{ marginBottom: '12px', color: '#6b7280' }}>Upload a screenshot of your schedule</p>
                        <label className="btn btn-primary" style={{ display: 'inline-block', cursor: 'pointer' }}>
                          {parsing ? '📤 Parsing...' : '📸 Upload Schedule Screenshot'}
                          <input
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            disabled={parsing}
                            style={{ display: 'none' }}
                          />
                        </label>
                        <p style={{ marginTop: '12px', fontSize: '14px', color: '#9ca3af' }}>or</p>
                        <button
                          type="button"
                          onClick={() => setUploadMode(true)}
                          className="btn btn-secondary"
                          style={{ marginTop: '8px' }}
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
