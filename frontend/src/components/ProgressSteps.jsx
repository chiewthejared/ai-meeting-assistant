import React from 'react';
import './ProgressSteps.css';

const ProgressSteps = ({ progress }) => {
  if (!progress || !progress.active) {
    return null;
  }

  const steps = [
    { key: 'upload', icon: '📤', label: 'Uploading' },
    { key: 'convert', icon: '🔄', label: 'Converting' },
    { key: 'transcribe', icon: '🎙️', label: 'Transcribing' },
    { key: 'diarize', icon: '👥', label: 'Identifying Speakers' },
    { key: 'summarize', icon: '🤖', label: 'Generating Insights' },
  ];

  const getStatusClass = (status) => {
    switch (status) {
      case 'completed': return 'completed';
      case 'in_progress': return 'in-progress';
      case 'skipped': return 'skipped';
      default: return 'pending';
    }
  };

  const getStepStatus = (stepKey) => {
    return progress.steps?.[stepKey]?.status || 'pending';
  };

  return (
    <div className="progress-container">
      <div className="progress-header">
        <span className="progress-title">⏳ Processing your meeting...</span>
        <span className="progress-percentage">{progress.progress_percentage}%</span>
      </div>
      
      <div className="progress-bar-track">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${progress.progress_percentage}%` }}
        />
      </div>
      
      <div className="steps-container">
        {steps.map((step, index) => {
          const status = getStepStatus(step.key);
          const statusClass = getStatusClass(status);
          const isActive = status === 'in_progress';
          const isCompleted = status === 'completed';
          
          return (
            <div key={step.key} className="step-item">
              <div className={`step-circle ${statusClass}`}>
                {isCompleted ? '✅' : step.icon}
              </div>
              <div className="step-label">
                <span className={`step-name ${isActive ? 'active' : ''}`}>
                  {step.label}
                </span>
                {isActive && <span className="step-dots">...</span>}
                {status === 'skipped' && <span className="step-skipped">(skipped)</span>}
              </div>
              {index < steps.length - 1 && (
                <div className={`step-connector ${statusClass}`} />
              )}
            </div>
          );
        })}
      </div>
      
      <div className="progress-time">
        ⏱️ {progress.elapsed_seconds}s elapsed
      </div>
    </div>
  );
};

export default ProgressSteps;