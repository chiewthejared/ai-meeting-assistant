from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.services.zoom_service import ZoomService
from app.database import get_db, ZoomToken
import os
import uuid
import tempfile
from datetime import datetime

router = APIRouter()
zoom_service = ZoomService()

@router.get("/zoom/auth/start")
async def zoom_auth_start():
    """Start Zoom OAuth flow"""
    state = str(uuid.uuid4())
    auth_url = zoom_service.get_authorization_url(state)
    
    return {
        "auth_url": auth_url,
        "state": state
    }

@router.get("/zoom/auth/callback")
async def zoom_auth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    """Handle Zoom OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"Zoom auth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    try:
        tokens = zoom_service.exchange_code_for_tokens(code)
        
        # Save tokens to database
        zoom_service.save_tokens(db, tokens["user_id"], tokens)
        
        return {
            "success": True,
            "user_id": tokens["user_id"],
            "message": "Zoom connected successfully!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to exchange code: {str(e)}")

@router.get("/zoom/recordings")
async def zoom_list_recordings(
    db: Session = Depends(get_db),
    from_date: str = None,
    to_date: str = None
):
    """List Zoom recordings for authenticated user"""
    # For now, get the first user in the database (simplified)
    token_record = db.query(ZoomToken).first()
    if not token_record:
        raise HTTPException(status_code=401, detail="No Zoom account connected")
    
    recordings = zoom_service.list_recordings(
        db,
        token_record.user_id,
        from_date,
        to_date
    )
    
    return {"recordings": recordings}

@router.post("/zoom/process/{meeting_id}")
async def zoom_process_recording(
    meeting_id: str,
    db: Session = Depends(get_db)
):
    """Download and process a Zoom recording"""
    token_record = db.query(ZoomToken).first()
    if not token_record:
        raise HTTPException(status_code=401, detail="No Zoom account connected")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Download recording
        file_path = zoom_service.download_recording(
            db,
            token_record.user_id,
            meeting_id,
            temp_dir
        )
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Recording not found or could not be downloaded")
        
        # Import transcription service (circular import handled by importing inside)
        from app.services.transcription import TranscriptionService
        from app.services.llm_service import LLMService
        
        transcription_service = TranscriptionService()
        llm_service = LLMService()
        
        # Process the recording
        print(f"🔄 Processing Zoom recording: {file_path}")
        transcription = transcription_service.transcribe_audio(file_path)
        insights = llm_service.generate_summary(transcription["text"])
        
        # Save to database
        from app.database import Meeting
        meeting = Meeting(
            filename=os.path.basename(file_path),
            transcript=transcription["text"],
            summary=insights["summary"],
            action_items=insights["action_items"],
            decisions=insights["decisions"]
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        
        return meeting.to_dict()
        
    except Exception as e:
        import shutil
        shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Failed to process recording: {str(e)}")

@router.get("/zoom/status")
async def zoom_status(db: Session = Depends(get_db)):
    """Check Zoom connection status"""
    token_record = db.query(ZoomToken).first()
    
    if token_record:
        return {
            "connected": True,
            "user_id": token_record.user_id,
            "expires_at": token_record.expires_at.isoformat() if token_record.expires_at else None
        }
    else:
        return {"connected": False}