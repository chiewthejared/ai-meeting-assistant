import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ZoomCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState('Connecting to Zoom...');
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(location.search);
      const code = params.get('code');
      const state = params.get('state');
      const errorParam = params.get('error');

      if (errorParam) {
        setError(`Zoom error: ${errorParam}`);
        setStatus('❌ Connection failed');
        setTimeout(() => navigate('/'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        setStatus('❌ Connection failed');
        setTimeout(() => navigate('/'), 3000);
        return;
      }

      try {
        setStatus('Exchanging code for tokens...');
        const response = await axios.get(`${API_URL}/api/zoom/auth/callback`, {
          params: { code, state }
        });

        if (response.data.success) {
          setStatus('✅ Zoom connected successfully!');
          setTimeout(() => navigate('/'), 2000);
        } else {
          setError(response.data.message || 'Connection failed');
          setStatus('❌ Connection failed');
          setTimeout(() => navigate('/'), 3000);
        }
      } catch (error) {
        console.error('Zoom callback error:', error);
        setError(error.response?.data?.detail || 'Failed to connect to Zoom');
        setStatus('❌ Connection failed');
        setTimeout(() => navigate('/'), 3000);
      }
    };

    handleCallback();
  }, [location, navigate]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      background: '#f0f2f5'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '16px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.1)',
        maxWidth: '400px',
        width: '100%',
        textAlign: 'center'
      }}>
        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>
          {status.includes('✅') ? '🎉' : status.includes('❌') ? '😢' : '⏳'}
        </div>
        <h2 style={{ marginBottom: '8px', color: '#1f2937' }}>
          {status.includes('✅') ? 'Connected!' : 
           status.includes('❌') ? 'Connection Failed' : 
           'Connecting to Zoom...'}
        </h2>
        <p style={{ color: '#6b7280', marginBottom: '16px' }}>{status}</p>
        
        {error && (
          <div style={{
            padding: '12px',
            background: '#fee2e2',
            borderRadius: '8px',
            color: '#dc2626',
            fontSize: '0.9rem'
          }}>
            {error}
          </div>
        )}
        
        <div style={{ marginTop: '20px', fontSize: '0.85rem', color: '#9ca3af' }}>
          Redirecting back to app...
        </div>
      </div>
    </div>
  );
};

export default ZoomCallback;