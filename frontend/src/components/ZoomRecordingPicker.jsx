import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ZoomRecordingPicker.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ZoomRecordingPicker = ({ onSelect, isConnected }) => {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);

  const fetchRecordings = async () => {
    if (!isConnected) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_URL}/api/zoom/recordings`);
      setRecordings(response.data.recordings || []);
    } catch (error) {
      console.error('Error fetching recordings:', error);
      setError('Failed to fetch Zoom recordings');
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!selectedId) return;
    
    setProcessing(true);
    setError(null);
    try {
      const response = await axios.post(`${API_URL}/api/zoom/process/${selectedId}`);
      if (onSelect) onSelect(response.data);
    } catch (error) {
      console.error('Error processing recording:', error);
      setError('Failed to process recording');
    } finally {
      setProcessing(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  if (!isConnected) {
    return (
      <div className="zoom-recording-picker">
        <p className="zoom-not-connected">Connect your Zoom account to fetch recordings</p>
      </div>
    );
  }

  return (
    <div className="zoom-recording-picker">
      <div className="zoom-recording-header">
        <h4>📹 Your Zoom Recordings</h4>
        <button 
          className="zoom-refresh-btn"
          onClick={fetchRecordings}
          disabled={loading}
        >
          {loading ? '⏳ Loading...' : '🔄 Refresh'}
        </button>
      </div>

      {error && (
        <div className="zoom-error">{error}</div>
      )}

      {loading ? (
        <div className="zoom-loading">Loading recordings...</div>
      ) : recordings.length === 0 ? (
        <p className="zoom-empty">No recordings found. Make sure you have cloud recordings in your Zoom account.</p>
      ) : (
        <div className="zoom-recording-list">
          {recordings.map((recording) => (
            <div 
              key={recording.uuid} 
              className={`zoom-recording-item ${selectedId === recording.uuid ? 'selected' : ''}`}
              onClick={() => setSelectedId(recording.uuid)}
            >
              <div className="recording-info">
                <span className="recording-topic">{recording.topic}</span>
                <span className="recording-date">{formatDate(recording.start_time)}</span>
              </div>
              <div className="recording-meta">
                <span className="recording-duration">
                  {recording.duration ? `${Math.round(recording.duration / 60)} min` : ''}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedId && (
        <button 
          className="zoom-process-btn"
          onClick={handleProcess}
          disabled={processing}
        >
          {processing ? '⏳ Processing...' : '🎯 Process Selected Recording'}
        </button>
      )}
    </div>
  );
};

export default ZoomRecordingPicker;