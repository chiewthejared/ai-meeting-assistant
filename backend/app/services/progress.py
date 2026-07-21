import time
from typing import Dict, List
from datetime import datetime

class ProgressTracker:
    """Track progress of meeting processing steps"""
    
    def __init__(self):
        self.steps = {
            "upload": {"name": "📤 Uploading file", "status": "pending"},
            "convert": {"name": "🔄 Converting to WAV", "status": "pending"},
            "transcribe": {"name": "🎙️ Transcribing with Whisper", "status": "pending"},
            "diarize": {"name": "👥 Identifying speakers", "status": "pending"},
            "summarize": {"name": "🤖 Generating insights", "status": "pending"},
            "complete": {"name": "✅ Processing complete", "status": "pending"}
        }
        self.current_step = None
        self.progress_percentage = 0
        self.start_time = None
        self.active = False
    
    def start(self):
        """Start tracking progress"""
        self.active = True
        self.start_time = datetime.now()
        self.progress_percentage = 0
        for step in self.steps:
            self.steps[step]["status"] = "pending"
        self.current_step = None
    
    def update_step(self, step_key: str, status: str = "in_progress"):
        """Update a step's status"""
        if step_key in self.steps:
            self.steps[step_key]["status"] = status
            self.current_step = step_key
        
        # Calculate percentage
        step_order = ["upload", "convert", "transcribe", "diarize", "summarize", "complete"]
        if step_key in step_order:
            idx = step_order.index(step_key)
            if status == "in_progress":
                self.progress_percentage = (idx / len(step_order)) * 100
            elif status == "completed":
                self.progress_percentage = ((idx + 1) / len(step_order)) * 100
        
        self.progress_percentage = min(max(self.progress_percentage, 0), 100)
    
    def get_progress(self) -> Dict:
        """Get current progress"""
        elapsed = None
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "steps": self.steps,
            "current_step": self.current_step,
            "progress_percentage": round(self.progress_percentage, 1),
            "elapsed_seconds": round(elapsed, 1) if elapsed else 0,
            "active": self.active
        }
    
    def complete(self):
        """Mark all steps as complete"""
        for step in self.steps:
            self.steps[step]["status"] = "completed"
        self.progress_percentage = 100
        self.active = False
    
    def error(self, error_message: str):
        """Mark as error"""
        self.active = False
        return {
            "status": "error",
            "message": error_message,
            "progress": self.get_progress()
        }

# Global progress tracker instance
progress_tracker = ProgressTracker()