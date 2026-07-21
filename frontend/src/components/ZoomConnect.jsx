import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ZoomConnect.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ZoomConnect = ({ onConnected }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [userId, setUserId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    checkZoomStatus();
  }, []);

  const checkZoomStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/zoom/status`);
      if (response.data.connected) {
        setIsConnected(true);
        setUserId(response.data.user_id);
        if (onConnected) onConnected(true);
      }
    } catch (error) {
      console.error('Error checking Zoom status:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectZoom = async () => {
    setConnecting(true);
    try {
      const response = await axios.get(`${API_URL}/api/zoom/auth/start`);
      // Redirect to Zoom for authorization
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Error starting Zoom auth:', error);
      alert('Failed to connect to Zoom. Please try again.');
      setConnecting(false);
    }
  };

  const disconnectZoom = () => {
    // Note: This only clears the frontend state
    // The actual token is stored in the database
    setIsConnected(false);
    setUserId(null);
    if (onConnected) onConnected(false);
  };

  if (loading) {
    return (
      <div className="zoom-connect loading">
        <span>⏳ Checking Zoom connection...</span>
      </div>
    );
  }

  return (
    <div className="zoom-connect">
      {isConnected ? (
        <div className="zoom-connected">
          <div className="zoom-status">
            <span className="status-badge connected">✅ Connected</span>
            <span className="user-id">👤 User: {userId}</span>
          </div>
          <button 
            className="zoom-disconnect-btn"
            onClick={disconnectZoom}
          >
            Disconnect
          </button>
        </div>
      ) : (
        <button 
          className="zoom-connect-btn"
          onClick={connectZoom}
          disabled={connecting}
        >
          {connecting ? '⏳ Connecting...' : '🔗 Connect Zoom Account'}
        </button>
      )}
    </div>
  );
};

export default ZoomConnect;