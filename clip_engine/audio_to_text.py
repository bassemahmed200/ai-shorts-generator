import os
import sys
import time
from typing import List, Dict, Any
from groq import Groq

def transcribe_via_groq(audio_path: str, api_key: str, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Transcribes audio using Groq's whisper-large-v3-turbo API.
    Retries on connection errors with exponential backoff.
    """
    print(f"[Groq Transcription] Starting... file: {audio_path}", flush=True)
    sys.stdout.flush()
    
    if not api_key:
        raise ValueError("Groq API key is missing. Set GROQ_API_KEY in .env")
        
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"[Groq Transcription] File size: {file_size_mb:.2f} MB", flush=True)
    if file_size_mb > 25:
        raise ValueError(f"Audio file size ({file_size_mb:.2f} MB) exceeds Groq's 25MB limit.")

    client = Groq(api_key=api_key, timeout=60.0)
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = 2 ** attempt
                print(f"[Groq Transcription] Retry {attempt}/{max_retries} after {wait}s...", flush=True)
                time.sleep(wait)
            
            print(f"[Groq Transcription] Calling Groq API...", flush=True)
            sys.stdout.flush()
            
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                )
            
            print(f"[Groq Transcription] API call completed!", flush=True)
            break
            
        except Exception as e:
            print(f"[Groq Transcription] Error: {e}", flush=True)
            if attempt == max_retries - 1:
                raise
    else:
        raise RuntimeError("Groq transcription failed after all retries.")
    
    transcript = []
    segments = getattr(transcription, "segments", [])
    if not segments and isinstance(transcription, dict):
        segments = transcription.get("segments", [])
        
    for segment in segments:
        if isinstance(segment, dict):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            text = segment.get("text", "").strip()
            words = segment.get("words", [])
        else:
            start = getattr(segment, "start", 0.0)
            end = getattr(segment, "end", 0.0)
            text = getattr(segment, "text", "").strip()
            words = getattr(segment, "words", [])
        
        # Normalize words format
        word_list = []
        for w in words:
            if isinstance(w, dict):
                word_list.append({
                    "word": w.get("word", "").strip(),
                    "start": w.get("start", 0.0),
                    "end": w.get("end", 0.0)
                })
            else:
                word_list.append({
                    "word": getattr(w, "word", "").strip(),
                    "start": getattr(w, "start", 0.0),
                    "end": getattr(w, "end", 0.0)
                })
            
        # If no word-level timestamps, generate proportional ones
        if not word_list:
            words_text = text.split()
            if words_text and len(words_text) > 1:
                total_chars = sum(len(w) for w in words_text)
                duration = end - start
                current_time = start
                
                for w in words_text:
                    word_duration = (len(w) / total_chars) * duration
                    word_list.append({
                        "word": w,
                        "start": current_time,
                        "end": current_time + word_duration
                    })
                    current_time += word_duration
            elif words_text:
                word_list.append({"word": words_text[0], "start": start, "end": end})
            
        transcript.append({
            "start": start,
            "end": end,
            "text": text,
            "words": word_list
        })

    print(f"[Groq Transcription] Done! Got {len(transcript)} segments.", flush=True)
    return transcript
