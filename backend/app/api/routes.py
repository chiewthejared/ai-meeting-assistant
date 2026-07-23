from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text  # <-- ADD THIS IMPORT
from app.services.transcription import TranscriptionService
from app.services.llm_service import LLMService
from app.services.progress import progress_tracker
from app.database import get_db, Meeting
import os
import shutil
import json
from datetime import datetime
import uuid

router = APIRouter()
transcription_service = TranscriptionService()
llm_service = LLMService()

@router.post("/process-meeting")
async def process_meeting(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"temp_{timestamp}_{file_id}_{file.filename}"
    
    # Start progress tracking
    progress_tracker.start()
    progress_tracker.update_step("upload", "in_progress")
    
    try:
        print(f"📥 Received file: {file.filename}")
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        progress_tracker.update_step("upload", "completed")
        print(f"💾 File saved to: {file_path}")
        
        # Convert to WAV
        progress_tracker.update_step("convert", "in_progress")
        print("🔄 Starting conversion...")
        
        # Transcribe
        progress_tracker.update_step("convert", "completed")
        progress_tracker.update_step("transcribe", "in_progress")
        print("🔄 Starting transcription...")
        
        transcription = transcription_service.transcribe_audio(file_path)
        
        progress_tracker.update_step("transcribe", "completed")
        print(f"✅ Transcription complete ({len(transcription['text'])} chars)")
        
        # Check if diarization was performed
        if transcription.get("has_speakers"):
            progress_tracker.update_step("diarize", "completed")
        else:
            progress_tracker.update_step("diarize", "skipped")
        
        # Generate insights
        progress_tracker.update_step("summarize", "in_progress")
        print("🤖 Generating insights with LLM...")
        insights = llm_service.generate_summary(transcription["text"])
        
        progress_tracker.update_step("summarize", "completed")
        print("✅ Insights generated")
        
        # Save to database
        meeting = Meeting(
            filename=file.filename,
            transcript=transcription["text"],
            summary=insights["summary"],
            action_items=insights["action_items"],
            decisions=insights["decisions"]
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        progress_tracker.update_step("complete", "completed")
        progress_tracker.complete()
        
        print(f"✅ Meeting saved to database (ID: {meeting.id})")
        
        result = meeting.to_dict()
        result["progress"] = progress_tracker.get_progress()
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        progress_tracker.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🧹 Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not delete temp file: {e}")

@router.get("/progress/{meeting_id}")
async def get_progress(meeting_id: str):
    """Get progress for a specific meeting"""
    # This would normally query a database or cache
    # For now, return the global progress
    return progress_tracker.get_progress()

@router.get("/meetings")
async def get_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all meetings with pagination"""
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).offset(skip).limit(limit).all()
    return [meeting.to_dict() for meeting in meetings]

@router.get("/meetings/{meeting_id}")
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific meeting by ID"""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.to_dict()

@router.delete("/meetings/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    """Delete a meeting"""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(meeting)
    db.commit()
    return {"message": "Meeting deleted successfully"}

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection using text() to avoid SQL injection warnings
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "meetings_count": db.query(Meeting).count()
    }