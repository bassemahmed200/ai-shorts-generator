# AI Shorts & Reels Generator

An automated AI-powered tool that takes long videos (via YouTube URL or local file upload) and turns them into highly engaging, viral short-form content (TikToks, Instagram Reels, YouTube Shorts). 

## 🚀 Features
- **Video Fetching**: Automatically download videos using `yt-dlp` or process local uploads.
- **AI Transcription**: High-accuracy transcription using either local `faster-whisper` or cloud-based Groq (`whisper-large-v3-turbo`).
- **Viral Analysis**: Uses Gemini 1.5 or Groq LLaMA 3.3 to analyze the transcript and pinpoint the most viral-worthy moments.
- **Auto-Editing**: Utilizes `ffmpeg` to crop videos to a 9:16 vertical aspect ratio and burns subtitles directly onto the video.
- **Modern UI**: A sleek, dark-themed dashboard built with Tailwind CSS.

---

## 📋 Prerequisites

Before running the application, ensure you have the following installed on your system:
- **Python 3.10+**
- **FFmpeg**: Must be installed and available in your system's `PATH`. 
  - Mac: `brew install ffmpeg`
  - Windows: Download from the official site or use `winget install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **GPU (Optional)**: If you intend to use `faster-whisper` for local transcription, having an NVIDIA GPU with CUDA installed will drastically improve performance. Otherwise, it will fallback to CPU.

---

## ⚙️ Installation & Setup

1. **Clone or Download the Repository**
2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**
   Copy `.env.example` to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your API keys:
   - `GEMINI_API_KEY`: Get it from [Google AI Studio](https://aistudio.google.com/)
   - `GROQ_API_KEY`: Get it from [Groq Console](https://console.groq.com/)

---

## 🏃‍♂️ Running the Server

Start the FastAPI application using uvicorn:

```bash
uvicorn app.main:app --reload
```

Then, open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

---

## 🏗️ Project Architecture (Workflow)

The project separates the web layer (`app/`) from the core processing logic (`clip_engine/`).

### `clip_engine/` (Core Logic)
- **`fetcher.py`**: Handles downloading videos via `yt-dlp` and processing local uploads.
- **`offline_audio.py`**: Local AI transcription using `faster-whisper`.
- **`audio_to_text.py`**: Cloud AI transcription using Groq API.
- **`viral_analyzer.py`**: The intelligence layer. It feeds the transcript to Gemini or Groq LLaMA models, prompting them to find the most viral moments and return precise timestamps and scores in JSON.
- **`video_editor.py`**: Uses `ffmpeg` to trim the original video, apply a 9:16 center crop, and burn the newly generated SRT subtitles.
- **`utils.py`**: Helper functions for time formatting, audio extraction, and temp file cleanup.
- **`workflow.py`**: The Orchestrator. Ties all the above modules together sequentially and reports progress back to the Job Manager.

### `app/` (Web API)
- **`main.py`**: FastAPI entry point.
- **`routes.py`**: API endpoints for starting jobs, polling status, and downloading clips.
- **`job_manager.py`**: In-memory store that tracks the status and progress of background jobs.
- **`schemas.py`**: Pydantic models for request validation.

---

## 🔮 Future Enhancements
- **Smart Cropping**: Implementing face detection/tracking instead of simple center-cropping.
- **Persistent Storage**: Migrating from in-memory job management to Redis/Celery and a Database for production scale.
- **Audio Chunking**: Supporting massive files for the Groq transcription API by chunking audio locally before sending.
