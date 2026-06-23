import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, Literal

from .schemas import JobResponse, JobStatusResponse, UploadUrlResponse
from . import job_manager
from clip_engine.workflow import run_workflow
from clip_engine.r2_storage import generate_upload_url, download_from_s3
from config import settings

router = APIRouter(prefix="/api")


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query("video/mp4", description="MIME type"),
):
    """Get a presigned URL for direct upload to Cloudflare R2."""
    try:
        result = generate_upload_url(filename, content_type)
        return UploadUrlResponse(
            upload_url=result["upload_url"],
            file_key=result["file_key"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    video_url: Optional[str] = Form(None),
    file_key: Optional[str] = Form(None),
    transcription_method: Literal["local", "groq"] = Form("groq"),
    analysis_provider: Literal["gemini", "groq"] = Form("groq"),
    num_clips: int = Form(3),
    clip_duration: int = Form(30),
    crop_style: Literal["portrait", "landscape", "square"] = Form("portrait")
):
    if not video_url and not file_key:
        raise HTTPException(status_code=400, detail="Must provide either video_url or upload a file first.")
        
    job_id = str(uuid.uuid4())
    job_manager.create_job(job_id)
    
    is_r2 = False
    is_local = False
    video_input = video_url
    
    if file_key:
        # File was uploaded to R2, download it locally
        is_r2 = True
        file_ext = os.path.splitext(file_key)[1] or ".mp4"
        video_input = os.path.join(settings.storage_dir, "downloads", f"{job_id}{file_ext}")
        
        # Download in background thread
        def download_progress(p):
            job_manager.update_job(job_id, "downloading", p * 0.5, None)
        
        try:
            download_from_s3(file_key, video_input)
            job_manager.update_job(job_id, "downloading", 50.0, None)
        except Exception as e:
            job_manager.update_job(job_id, "failed", 0.0, f"Failed to download from storage: {str(e)}")
            return JobResponse(job_id=job_id)
        
        is_local = True
    
    if not is_local and not video_url:
        raise HTTPException(status_code=400, detail="Must provide either video_url or file_key.")
    
    # Submit to thread pool (runs in background, non-blocking)
    job_manager.submit_job(
        job_id,
        run_workflow,
        video_input=video_input,
        is_local=is_local,
        transcription_method=transcription_method,
        analysis_provider=analysis_provider,
        num_clips=num_clips,
        clip_duration=clip_duration,
        crop_style=crop_style,
        update_status=job_manager.update_job
    )
    
    return JobResponse(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job["result"],
        error=job["error"]
    )


@router.get("/jobs/{job_id}/clips")
async def get_job_clips(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    return {"clips": job["result"]}


@router.get("/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    clip_path = os.path.join(settings.storage_dir, "clips", f"{clip_id}.mp4")
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip not found")
        
    return FileResponse(
        path=clip_path,
        media_type="video/mp4",
        filename=f"{clip_id}.mp4"
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_manager.delete_job(job_id)
    return {"detail": "Job deleted"}
