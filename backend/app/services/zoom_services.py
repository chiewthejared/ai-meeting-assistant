import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.database import ZoomToken

class ZoomService:
    def __init__(self):
        self.client_id = os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = os.getenv("ZOOM_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ZOOM_REDIRECT_URI")
        self.token_url = "https://zoom.us/oauth/token"
        self.api_base = "https://api.zoom.us/v2"
        
        if not self.client_id or not self.client_secret:
            print("⚠️ Zoom credentials not configured. Zoom features disabled.")
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Zoom OAuth authorization URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        if state:
            params["state"] = state
        
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://zoom.us/oauth/authorize?{query}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to exchange code: {response.text}")
        
        data = response.json()
        
        # Calculate expiration time
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": expires_at,
            "user_id": self._get_user_id(data["access_token"]),
        }
    
    def _get_user_id(self, access_token: str) -> str:
        """Get the Zoom user ID from the access token"""
        response = requests.get(
            f"{self.api_base}/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json().get("id")
        return "unknown"
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh an expired access token"""
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response.text}")
        
        data = response.json()
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": expires_at,
        }
    
    def get_valid_token(self, db: Session, user_id: str) -> Optional[str]:
        """Get a valid access token, refreshing if expired"""
        token_record = db.query(ZoomToken).filter(ZoomToken.user_id == user_id).first()
        
        if not token_record:
            return None
        
        # Check if token is expired
        if datetime.now() >= token_record.expires_at:
            try:
                new_tokens = self.refresh_access_token(token_record.refresh_token)
                token_record.access_token = new_tokens["access_token"]
                token_record.refresh_token = new_tokens["refresh_token"]
                token_record.expires_at = new_tokens["expires_at"]
                db.commit()
                db.refresh(token_record)
                print(f"✅ Refreshed Zoom token for user: {user_id}")
            except Exception as e:
                print(f"⚠️ Failed to refresh Zoom token: {e}")
                return None
        
        return token_record.access_token
    
    def list_recordings(
        self,
        db: Session,
        user_id: str,
        from_date: str = None,
        to_date: str = None
    ) -> List[Dict]:
        """List recordings for a user"""
        token = self.get_valid_token(db, user_id)
        if not token:
            return []
        
        params = {"page_size": 100}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        response = requests.get(
            f"{self.api_base}/users/me/recordings",
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )
        
        if response.status_code != 200:
            print(f"⚠️ Failed to list recordings: {response.text}")
            return []
        
        data = response.json()
        return data.get("meetings", [])
    
    def download_recording(
        self,
        db: Session,
        user_id: str,
        meeting_id: str,
        download_path: str
    ) -> Optional[str]:
        """Download a recording file"""
        token = self.get_valid_token(db, user_id)
        if not token:
            return None
        
        # Get recording details
        response = requests.get(
            f"{self.api_base}/meetings/{meeting_id}/recordings",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"⚠️ Failed to get recording details: {response.text}")
            return None
        
        data = response.json()
        
        # Find the audio or video file
        recording_files = data.get("recording_files", [])
        audio_file = None
        
        for file in recording_files:
            file_type = file.get("file_type", "")
            if file_type in ["MP4", "M4A", "AUDIO"]:
                audio_file = file
                break
        
        if not audio_file:
            print("⚠️ No audio/video file found in recording")
            return None
        
        # Download the file
        download_url = audio_file.get("download_url")
        if not download_url:
            print("⚠️ No download URL found")
            return None
        
        print(f"📥 Downloading recording: {audio_file.get('file_name', 'unknown')}")
        
        response = requests.get(
            download_url,
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )
        
        if response.status_code != 200:
            print(f"⚠️ Failed to download: {response.text}")
            return None
        
        # Save the file
        file_name = audio_file.get("file_name", f"recording_{meeting_id}.mp4")
        file_path = os.path.join(download_path, file_name)
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Recording downloaded: {file_path}")
        return file_path
    
    def save_tokens(self, db: Session, user_id: str, tokens: Dict) -> ZoomToken:
        """Save or update Zoom tokens for a user"""
        token_record = db.query(ZoomToken).filter(ZoomToken.user_id == user_id).first()
        
        if token_record:
            token_record.access_token = tokens["access_token"]
            token_record.refresh_token = tokens["refresh_token"]
            token_record.expires_at = tokens["expires_at"]
        else:
            token_record = ZoomToken(
                user_id=user_id,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=tokens["expires_at"]
            )
            db.add(token_record)
        
        db.commit()
        db.refresh(token_record)
        return token_record