import os
import time
import subprocess
import hashlib
import json
from typing import Dict
from datetime import datetime

class TranscriptionService:
    def __init__(self):
        print("🔊 Initializing Transcription Service...")
        self.use_mock = False
        self.whisper_available = False
        self.diarize_available = False
        self.ffmpeg_path = None
        
        # Load environment variables for configuration
        self.model_name = os.getenv("WHISPER_MODEL", "tiny")
        self.enable_diarization = os.getenv("ENABLE_DIARIZATION", "true").lower() == "true"
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.cache_dir = os.getenv("CACHE_DIR", "cache")
        
        print(f"⚙️ Configuration:")
        print(f"   - Whisper Model: {self.model_name}")
        print(f"   - Diarization: {'Enabled' if self.enable_diarization else 'Disabled'}")
        print(f"   - Caching: {'Enabled' if self.enable_caching else 'Disabled'}")
        
        # Create cache directory if enabled
        if self.enable_caching:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # Check for FFmpeg
        possible_paths = [
            "C:\\ffmpeg\\ffmpeg-8.1.2-full_build\\bin\\ffmpeg.exe",
            "C:\\Program Files\\FFmpeg\\bin\\ffmpeg.exe",
            "ffmpeg"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '-version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.ffmpeg_path = path
                    print(f"✅ FFmpeg found at: {path}")
                    break
            except:
                continue
        
        # Load Whisper
        try:
            import whisper
            print(f"✅ Whisper found, attempting to load {self.model_name} model...")
            try:
                self.model = whisper.load_model(self.model_name)
                print(f"✅ Whisper {self.model_name} model loaded successfully!")
                self.whisper_available = True
                self.use_mock = False
            except Exception as e:
                print(f"⚠️ Could not load Whisper model: {e}")
                self.use_mock = True
        except ImportError:
            print("⚠️ Whisper not installed. Using mock mode.")
            self.use_mock = True
        
        # Load Diarize (only if enabled)
        if self.enable_diarization and not self.use_mock:
            try:
                from diarize import diarize
                self.diarize = diarize
                self.diarize_available = True
                print("✅ Diarize loaded successfully (speaker diarization available)")
            except ImportError:
                print("⚠️ Diarize not installed. Speaker diarization disabled.")
                print("   Install with: pip install diarize")
                self.diarize_available = False
        else:
            print("ℹ️ Speaker diarization disabled by configuration")
            self.diarize_available = False
    
    def _get_cache_key(self, file_path: str) -> str:
        """Generate a cache key based on file content"""
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    
    def _get_cached_result(self, file_path: str) -> Dict:
        """Get cached transcription result if available"""
        if not self.enable_caching:
            return None
        
        key = self._get_cache_key(file_path)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                # Check if cache is still valid (less than 7 days old)
                cache_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
                age = (datetime.now() - cache_time).days
                if age < 7:
                    print("✅ Using cached transcription result")
                    # Remove cache timestamp before returning
                    data.pop('cached_at', None)
                    return data
                else:
                    print("⚠️ Cache expired, reprocessing...")
                    os.remove(cache_file)
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")
        return None
    
    def _save_to_cache(self, file_path: str, result: Dict):
        """Save transcription result to cache"""
        if not self.enable_caching:
            return
        
        try:
            key = self._get_cache_key(file_path)
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            
            # Add cache timestamp
            cache_data = result.copy()
            cache_data['cached_at'] = datetime.now().isoformat()
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            print("💾 Result cached for future use")
        except Exception as e:
            print(f"⚠️ Cache write error: {e}")
    
    def _convert_to_wav(self, file_path: str) -> str:
        """Convert audio file to WAV for better compatibility"""
        if file_path.lower().endswith('.wav'):
            return file_path
        
        if not self.ffmpeg_path:
            return file_path
        
        wav_path = file_path.rsplit('.', 1)[0] + '_converted.wav'
        try:
            print(f"🔄 Converting to WAV using FFmpeg...")
            cmd = f'"{self.ffmpeg_path}" -i "{file_path}" -ar 16000 -ac 1 -acodec pcm_s16le "{wav_path}" -y'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                print(f"✅ Conversion complete")
                return wav_path
            else:
                return file_path
        except Exception as e:
            print(f"⚠️ Conversion failed: {e}")
            return file_path
    
    def _format_with_speakers(self, segments) -> str:
        """Format diarize segments into readable transcript with speaker labels"""
        if not segments:
            return "No speaker segments available"
        
        formatted = []
        current_speaker = None
        current_text = []
        
        for seg in segments:
            speaker = seg.get('speaker', 'Unknown')
            text = seg.get('text', '').strip()
            
            if not text:
                continue
            
            # Convert SPEAKER_00 to Speaker 1, SPEAKER_01 to Speaker 2, etc.
            if speaker.startswith('SPEAKER_'):
                try:
                    # Extract the number from SPEAKER_XX
                    num = int(speaker.split('_')[1])
                    speaker = f"Speaker {num + 1}"  # Convert 00→1, 01→2, etc.
                except (IndexError, ValueError):
                    # If parsing fails, keep original
                    pass
            
            if speaker != current_speaker:
                if current_text:
                    formatted.append(f"{current_speaker}: {' '.join(current_text)}")
                current_speaker = speaker
                current_text = [text]
            else:
                current_text.append(text)
        
        # Add the last speaker
        if current_text and current_speaker:
            formatted.append(f"{current_speaker}: {' '.join(current_text)}")
        
        return '\n\n'.join(formatted)
    
    def transcribe_audio(self, file_path: str) -> Dict:
        """Transcribe audio file with optional speaker diarization and caching"""
        print(f"📝 Processing: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check cache first
        cached_result = self._get_cached_result(file_path)
        if cached_result:
            return cached_result
        
        # Convert to WAV for better compatibility
        wav_path = self._convert_to_wav(file_path)
        
        # Try real transcription if available
        if self.whisper_available and not self.use_mock:
            try:
                # Get transcription from Whisper
                print("🔄 Transcribing with Whisper...")
                result = self.model.transcribe(wav_path)
                print(f"✅ Whisper transcription complete ({len(result['text'])} chars)")
                
                # Try speaker diarization if available and enabled
                segments_with_speakers = []
                if self.enable_diarization and self.diarize_available:
                    try:
                        print("🔄 Running speaker diarization with Diarize...")
                        start_time = time.time()
                        diarization_result = self.diarize(wav_path)
                        diarize_time = time.time() - start_time
                        print(f"⏱️ Diarization took {diarize_time:.1f}s")
                        
                        # Map speaker labels to Whisper segments
                        if diarization_result and hasattr(diarization_result, 'segments'):
                            speaker_segments = diarization_result.segments
                            
                            # For each Whisper segment, find the speaker
                            for whisper_seg in result.get('segments', []):
                                seg_start = whisper_seg.get('start', 0)
                                seg_end = whisper_seg.get('end', 0)
                                seg_mid = (seg_start + seg_end) / 2
                                
                                # Find which speaker was active at this time
                                speaker = "Unknown"
                                for spk_seg in speaker_segments:
                                    if spk_seg.start <= seg_mid <= spk_seg.end:
                                        speaker = spk_seg.speaker
                                        break
                                
                                segments_with_speakers.append({
                                    'speaker': speaker,
                                    'text': whisper_seg.get('text', ''),
                                    'start': seg_start,
                                    'end': seg_end
                                })
                            
                            print(f"✅ Speaker diarization complete")
                            print(f"👥 Found {diarization_result.num_speakers if hasattr(diarization_result, 'num_speakers') else '?'} speakers")
                        else:
                            # Fallback - use regular segments
                            print("⚠️ No speaker segments from diarize, using plain transcription")
                            for seg in result.get('segments', []):
                                segments_with_speakers.append({
                                    'speaker': 'Unknown',
                                    'text': seg.get('text', ''),
                                    'start': seg.get('start', 0),
                                    'end': seg.get('end', 0)
                                })
                            
                    except Exception as e:
                        print(f"⚠️ Diarization failed: {e}")
                        # Fallback to plain transcription
                        for seg in result.get('segments', []):
                            segments_with_speakers.append({
                                'speaker': 'Unknown',
                                'text': seg.get('text', ''),
                                'start': seg.get('start', 0),
                                'end': seg.get('end', 0)
                            })
                else:
                    print("ℹ️ Speaker diarization skipped (disabled or not available)")
                
                # Format the transcript with speakers
                if segments_with_speakers:
                    formatted_text = self._format_with_speakers(segments_with_speakers)
                else:
                    formatted_text = result['text']
                
                # Clean up converted file
                if wav_path != file_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                        print("🧹 Cleaned up converted WAV file")
                    except:
                        pass
                
                # Prepare result
                final_result = {
                    "text": formatted_text,
                    "segments": segments_with_speakers,
                    "language": result.get("language", "en"),
                    "has_speakers": bool(segments_with_speakers)
                }
                
                # Cache the result
                self._save_to_cache(file_path, final_result)
                
                return final_result
                
            except Exception as e:
                print(f"⚠️ Transcription failed: {e}")
                self.use_mock = True
        
        # Fallback to mock
        print("🔄 Using mock transcription...")
        time.sleep(2)
        
        file_size = os.path.getsize(file_path)
        mock_text = f"""This is a mock transcription of {os.path.basename(file_path)}.
File size: {file_size / (1024*1024):.2f} MB.
To use real transcription with speaker diarization:
1. Install diarize: pip install diarize
2. Make sure ffmpeg is installed
3. Restart the server"""
        
        return {
            "text": mock_text,
            "segments": [],
            "language": "en",
            "has_speakers": False
        }