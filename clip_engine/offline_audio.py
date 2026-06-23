import sys
from typing import List, Dict, Any, Callable, Optional

def transcribe_locally(
    audio_path: str, 
    model_size: str = "base",
    progress_callback: Optional[Callable[[float], None]] = None
) -> List[Dict[str, Any]]:
    """
    Transcribes audio locally using faster-whisper.
    Returns a list of segments: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
    """
    # Lazy import - only load faster-whisper when actually needed
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is not installed. "
            "Please use transcription_method='groq' or install it: "
            "pip install faster-whisper"
        )
    
    print(f"[Transcription] Loading whisper model: {model_size}...", flush=True)
    sys.stdout.flush()
    
    model = WhisperModel(model_size, device="auto", compute_type="default")
    
    print(f"[Transcription] Model loaded. Starting transcription of: {audio_path}", flush=True)
    sys.stdout.flush()
    
    segments_generator, info = model.transcribe(audio_path, beam_size=5)
    
    print(f"[Transcription] Detected language: {info.language} (probability: {info.language_probability:.2f})", flush=True)
    print(f"[Transcription] Audio duration: {info.duration:.1f}s - processing...", flush=True)
    sys.stdout.flush()
    
    transcript = []
    for segment in segments_generator:
        transcript.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })
        # Report progress based on audio duration
        if info.duration > 0 and progress_callback:
            progress = min(99.0, (segment.end / info.duration) * 100)
            progress_callback(progress)
    
    print(f"[Transcription] Done! Got {len(transcript)} segments.", flush=True)
    sys.stdout.flush()
        
    return transcript
