from pydantic import BaseModel, HttpUrl
from typing import Optional, Any, Literal

class JobRequest(BaseModel):
    video_url: Optional[str] = None
    file_key: Optional[str] = None
    transcription_method: Literal["local", "groq"] = "local"
    analysis_provider: Literal["gemini", "groq"] = "gemini"
    num_clips: int = 3
    clip_duration: int = 30
    crop_style: Literal["portrait", "landscape", "square"] = "portrait"

class JobResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    result: Optional[Any] = None
    error: Optional[str] = None

class UploadUrlResponse(BaseModel):
    upload_url: str
    file_key: str
