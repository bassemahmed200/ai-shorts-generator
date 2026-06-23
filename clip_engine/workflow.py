import os
import traceback
from typing import Callable, Dict, Any, List

from config import settings
from .fetcher import download_video, register_local_upload
from .utils import extract_audio, cleanup_files
from .offline_audio import transcribe_locally
from .audio_to_text import transcribe_via_groq
from .viral_analyzer import analyze_transcript
from .video_editor import crop_video, RESOLUTIONS
from .captions import generate_captions, burn_captions
from .hook_generator import generate_hooks, add_hook_overlay

def run_workflow(
    video_input: str,
    is_local: bool,
    transcription_method: str,
    analysis_provider: str,
    num_clips: int,
    clip_duration: int,
    crop_style: str,
    job_id: str,
    update_status: Callable[[str, str, float, Any], None]
):
    """
    Orchestrates the entire short generation pipeline.
    update_status signature: (job_id: str, status: str, progress: float, result: Any)
    """
    temp_files = []
    
    try:
        print(f"[Workflow] crop_style: {crop_style}", flush=True)
        
        # Step 1: Fetch/Load Video
        update_status(job_id, "downloading", 0.0, None)
        
        if is_local:
            video_info = register_local_upload(video_input)
            update_status(job_id, "downloading", 100.0, None)
        else:
            def dl_progress(p):
                update_status(job_id, "downloading", p, None)
            
            video_info = download_video(
                url=video_input, 
                output_dir=os.path.join(settings.storage_dir, "downloads"),
                progress_callback=dl_progress
            )
            
        video_path = video_info["file_path"]
        video_duration = video_info["duration"]
        temp_files.append(video_path)
        
        # Step 2: Extract Audio
        update_status(job_id, "extracting_audio", 0.0, None)
        audio_path_wav = os.path.join(settings.storage_dir, "audio", f"{job_id}.wav")
        audio_path = extract_audio(video_path, audio_path_wav)
        temp_files.append(audio_path)
        update_status(job_id, "extracting_audio", 100.0, None)
        
        # Step 3: Transcription
        update_status(job_id, "transcribing", 0.0, None)
        print(f"[Workflow] Starting transcription with method: {transcription_method}", flush=True)
        if transcription_method == "groq":
            transcript = transcribe_via_groq(audio_path, settings.groq_api_key)
        else:
            def tr_progress(p):
                update_status(job_id, "transcribing", p, None)
            transcript = transcribe_locally(
                audio_path, 
                settings.whisper_model_size,
                progress_callback=tr_progress
            )
        update_status(job_id, "transcribing", 100.0, None)
        print(f"[Workflow] Transcription complete. {len(transcript)} segments.", flush=True)
        
        # Step 4: Analysis
        update_status(job_id, "analyzing", 0.0, None)
        api_key = settings.groq_api_key if analysis_provider == "groq" else settings.gemini_api_key
        suggested_clips = analyze_transcript(
            transcript=transcript,
            video_duration=video_duration,
            num_clips=num_clips,
            clip_duration=clip_duration,
            provider=analysis_provider,
            api_key=api_key
        )
        update_status(job_id, "analyzing", 100.0, None)
        
        # Step 5: Generate Hooks
        update_status(job_id, "generating_hooks", 0.0, None)
        all_hooks = []
        for clip in suggested_clips:
            hooks = generate_hooks(
                topic=clip["title"],
                num_hooks=3,
                content_context=clip.get("reason", ""),
                api_key=settings.groq_api_key
            )
            all_hooks.append({
                "clip_title": clip["title"],
                "hooks": hooks
            })
        update_status(job_id, "generating_hooks", 100.0, None)
        print(f"[Workflow] Generated hooks for {len(all_hooks)} clips.", flush=True)
        
        # Step 6: Cutting Clips
        update_status(job_id, "cutting", 0.0, None)
        final_clips = []
        
        for i, clip in enumerate(suggested_clips):
            # Update progress based on clip index
            progress = (i / len(suggested_clips)) * 100
            update_status(job_id, "cutting", progress, None)
            
            clip_id = f"{job_id}_clip_{i+1}"
            temp_clip_path = os.path.join(settings.storage_dir, "clips", f"{clip_id}_temp.mp4")
            hooked_clip_path = os.path.join(settings.storage_dir, "clips", f"{clip_id}_hooked.mp4")
            output_clip_path = os.path.join(settings.storage_dir, "clips", f"{clip_id}.mp4")
            ass_path = os.path.join(settings.storage_dir, "subtitles", f"{clip_id}.ass")
            
            # Step 1: Crop video
            crop_video(
                input_path=video_path,
                start=clip["start_time"],
                end=clip["end_time"],
                output_path=temp_clip_path,
                crop_style=crop_style
            )
            temp_files.append(temp_clip_path)
            
            # Step 2: Generate word-by-word captions
            target_w, target_h = RESOLUTIONS.get(crop_style, (1080, 1920))
            generate_captions(
                transcript_segments=transcript,
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                output_path=ass_path,
                style="hormozi",
                video_width=target_w,
                video_height=target_h
            )
            temp_files.append(ass_path)
            
            # Step 3: Burn captions into video
            burn_captions(
                input_path=temp_clip_path,
                ass_path=ass_path,
                output_path=output_clip_path
            )
            
            # Save results with hooks
            clip_hooks = all_hooks[i]["hooks"] if i < len(all_hooks) else []
            final_clips.append({
                "clip_path": output_clip_path,
                "title": clip["title"],
                "score": clip["score"],
                "reason": clip["reason"],
                "hooks": clip_hooks,
                "download_url": f"/api/clips/{clip_id}/download"
            })
            
        update_status(job_id, "done", 100.0, final_clips)

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Job {job_id} failed: {error_msg}")
        update_status(job_id, "failed", 0.0, error_msg)
        
    finally:
        # Cleanup temp files (keep final clips)
        cleanup_files(temp_files)
