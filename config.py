import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    
    default_transcription_method: Literal["local", "groq"] = "local"
    default_analysis_provider: Literal["gemini", "groq"] = "gemini"
    whisper_model_size: str = "base"
    
    max_upload_size_mb: int = 500
    storage_dir: str = "./storage"
    ffmpeg_path: str = "ffmpeg"
    
    # S3-Compatible Storage Settings (Storj, R2, MinIO, etc.)
    s3_endpoint: str = ""  # e.g., https://gateway.storjshare.io
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""
    s3_region: str = "us-east-1"
    s3_public_url: str = ""  # e.g., https://your-bucket.storjshare.io

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.storage_dir, exist_ok=True)
os.makedirs(os.path.join(settings.storage_dir, "downloads"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_dir, "audio"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_dir, "transcripts"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_dir, "clips"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_dir, "subtitles"), exist_ok=True)
