import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import ProgressSteps from './components/ProgressSteps';
import ZoomConnect from './components/ZoomConnect';
import ZoomRecordingPicker from './components/ZoomRecordingPicker';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(null);
  const [isZoomConnected, setIsZoomConnected] = useState(false);

  // Fetch meetings on load
  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/meetings`);
      setMeetings(response.data);
    } catch (err) {
      console.error('Error fetching meetings:', err);
    }
  };

  const { getRootProps, getInputProps } = useDropzone({
    accept: { 'audio/*': ['.mp3', '.wav', '.m4a', '.mpeg', '.mp4'] },
    maxSize: 100 * 1024 * 1024, // 100MB
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0]);
        setResult(null);
        setError(null);
        setProgress(null);
      }
    }
  });

  const handleProcess = async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    setProgress(null);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_URL}/api/process-meeting`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000 // 5 minutes (for diarization)
      });
      
      if (response.data.progress) {
        setProgress(response.data.progress);
      }
      
      setResult(response.data);
      await fetchMeetings();
      setFile(null);
    } catch (error) {
      console.error('Error:', error);
      setError(error.response?.data?.detail || 'Failed to process meeting. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleZoomProcessing = (meetingData) => {
    setResult(meetingData);
    fetchMeetings();
  };

  const loadMeeting = (meeting) => {
    setSelectedMeeting(meeting);
    setResult(meeting);
    setProgress(null);
  };

  const deleteMeeting = async (id, event) => {
    event.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this meeting?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/meetings/${id}`);
      await fetchMeetings();
      if (selectedMeeting?.id === id) {
        setSelectedMeeting(null);
        setResult(null);
      }
    } catch (error) {
      console.error('Error deleting meeting:', error);
      alert('Failed to delete meeting');
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🎙️ AI Meeting Assistant</h1>
        <p>Upload your meeting recording and get instant AI-powered insights</p>
      </header>

      <div className="container">
        <div className="main-content">
          {/* Zoom Connect Section */}
          <div className="upload-section">
            <h3 style={{ marginBottom: '12px', fontSize: '1rem', color: '#4b5563' }}>
              Connect Zoom Account
            </h3>
            <ZoomConnect onConnected={setIsZoomConnected} />
          </div>

          {/* Zoom Recording Picker */}
          {isZoomConnected && (
            <div className="upload-section">
              <ZoomRecordingPicker 
                onSelect={handleZoomProcessing}
                isConnected={isZoomConnected}
              />
            </div>
          )}

          {/* Upload Section */}
          <div className="upload-section">
            <h3 style={{ marginBottom: '12px', fontSize: '1rem', color: '#4b5563' }}>
              Or Upload a Recording
            </h3>
            <div {...getRootProps()} className={`dropzone ${file ? 'has-file' : ''}`}>
              <input {...getInputProps()} />
              {file ? (
                <div className="file-info">
                  <span className="file-icon">📁</span>
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
              ) : (
                <div>
                  <div className="upload-icon">📤</div>
                  <p>Drag & drop audio/video file here</p>
                  <p className="sub-text">or click to browse (MP3, WAV, M4A, MP4)</p>
                </div>
              )}
            </div>

            <button 
              className="process-btn" 
              onClick={handleProcess}
              disabled={!file || loading}
            >
              {loading ? (
                <span className="loading-spinner">⚡ Processing...</span>
              ) : (
                '🚀 Process Meeting'
              )}
            </button>

            {error && (
              <div className="error-message">
                ❌ {error}
              </div>
            )}
          </div>

          {/* Progress Steps */}
          {loading && progress && (
            <ProgressSteps progress={progress} />
          )}

          {/* Results Section */}
          {(result || selectedMeeting) && (
            <div className="results">
              <div className="result-header">
                <h2>📋 Meeting Insights</h2>
                <button 
                  className="close-btn"
                  onClick={() => {
                    setResult(null);
                    setSelectedMeeting(null);
                    setProgress(null);
                  }}
                >
                  ✕
                </button>
              </div>
              
              <div className="result-meta">
                <span className="filename">📄 {result?.filename || selectedMeeting?.filename}</span>
                <span className="date">
                  {new Date(result?.created_at || selectedMeeting?.created_at).toLocaleString()}
                </span>
              </div>
              
              <div className="result-grid">
                <div className="result-card summary-card">
                  <h3>📝 Summary</h3>
                  <p>{result?.summary || selectedMeeting?.summary}</p>
                </div>

                <div className="result-card actions-card">
                  <h3>✅ Action Items</h3>
                  <ul>
                    {(result?.action_items || selectedMeeting?.action_items || []).map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="result-card decisions-card">
                  <h3>🎯 Decisions Made</h3>
                  <ul>
                    {(result?.decisions || selectedMeeting?.decisions || []).map((decision, idx) => (
                      <li key={idx}>{decision}</li>
                    ))}
                  </ul>
                </div>

                <div className="result-card transcript-card">
                  <h3>📄 Full Transcript</h3>
                  <pre>
                    {(result?.transcript || selectedMeeting?.transcript || 'No transcript available')
                      .split('\n')
                      .map((line, i) => {
                        if (!line.trim()) return null;
                        
                        const speakerMatch = line.match(/^(Speaker\s*[\d]+):\s*/i);
                        if (speakerMatch) {
                          const speaker = speakerMatch[1];
                          const text = line.substring(speakerMatch[0].length);
                          const speakerNum = parseInt(speaker.match(/\d+/)?.[0] || '0');
                          const colors = ['#667eea', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899'];
                          const color = colors[speakerNum % colors.length];
                          return (
                            <div key={i} style={{ 
                              marginBottom: '6px', 
                              padding: '6px 10px',
                              borderLeft: `4px solid ${color}`,
                              backgroundColor: i % 2 === 0 ? '#f9fafb' : 'transparent',
                              borderRadius: '4px'
                            }}>
                              <strong style={{ color: color, fontSize: '0.95rem' }}>{speaker}:</strong>
                              <span style={{ marginLeft: '6px', fontSize: '0.95rem' }}>{text}</span>
                            </div>
                          );
                        }
                        return (
                          <div key={i} style={{ padding: '4px 0', fontSize: '0.95rem' }}>
                            {line}
                          </div>
                        );
                      })}
                  </pre>
                  {result?.has_speakers && (
                    <div style={{ 
                      marginTop: '12px', 
                      padding: '8px 12px', 
                      backgroundColor: '#eef2ff', 
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      color: '#4b5563'
                    }}>
                      🎤 Speaker diarization enabled - {result.segments?.length || 0} segments
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar - Meeting History */}
        <div className="sidebar">
          <h3>📚 Meeting History</h3>
          <div className="meeting-list">
            {meetings.length === 0 ? (
              <p className="empty-message">No meetings processed yet</p>
            ) : (
              meetings.map((meeting) => (
                <div 
                  key={meeting.id} 
                  className={`meeting-item ${selectedMeeting?.id === meeting.id ? 'active' : ''}`}
                  onClick={() => loadMeeting(meeting)}
                >
                  <div className="meeting-header">
                    <span className="meeting-filename">{meeting.filename}</span>
                    <button 
                      className="delete-btn"
                      onClick={(e) => deleteMeeting(meeting.id, e)}
                    >
                      🗑️
                    </button>
                  </div>
                  <span className="meeting-date">
                    {new Date(meeting.created_at).toLocaleDateString()}
                  </span>
                  <p className="meeting-preview">
                    {meeting.summary?.substring(0, 100)}...
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;