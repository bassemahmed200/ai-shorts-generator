import json
import re
from typing import List, Dict, Any, Literal
import google.generativeai as genai
from groq import Groq
from pydantic import BaseModel

class ClipSuggestion(BaseModel):
    start_time: float
    end_time: float
    title: str
    score: float
    reason: str

class ViralAnalysisResponse(BaseModel):
    clips: List[ClipSuggestion]

def parse_json_response(text: str) -> dict:
    """Defensive JSON parsing."""
    try:
        # Try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON block
        match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Last resort: try finding anything that looks like JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
                
        raise ValueError("Could not parse JSON from model response.")

def analyze_transcript(
    transcript: List[Dict[str, Any]], 
    video_duration: float, 
    num_clips: int, 
    clip_duration: int, 
    provider: Literal["gemini", "groq"] = "gemini",
    api_key: str = ""
) -> List[Dict[str, Any]]:
    """
    Analyzes the transcript and returns viral clip suggestions.
    """
    
    if not api_key:
        raise ValueError(f"API key for {provider} is missing.")
        
    # Prepare transcript text for the prompt
    transcript_text = ""
    for seg in transcript:
        transcript_text += f"[{seg['start']:.1f} - {seg['end']:.1f}] {seg['text']}\n"
        
    prompt = f"""You are an expert social media manager and video editor specializing in viral TikToks, Instagram Reels, and YouTube Shorts.
I will provide you with a video transcript with timestamps.
Your task is to identify the most engaging, viral moments in the video and suggest short clips.

Requirements:
1. Suggest exactly {num_clips} clips.
2. Each clip should be approximately {clip_duration} seconds long.
3. Choose parts with high energy, strong hooks, or valuable information.
4. Provide a catchy, viral title for each clip.
5. Give a virality score from 1 to 10.
6. Give a brief reason for why this clip will go viral.

You MUST respond in valid JSON format EXACTLY matching this schema, with no additional text or markdown formatting outside the JSON:
{{
  "clips": [
    {{
      "start_time": float,
      "end_time": float,
      "title": "string",
      "score": float,
      "reason": "string"
    }}
  ]
}}

Transcript:
{transcript_text}
"""

    if provider == "gemini":
        genai.configure(api_key=api_key)
        # Using gemini-1.5-flash as it is fast and supports JSON schema
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        parsed_data = parse_json_response(response.text)
        
    elif provider == "groq":
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that always outputs valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )
        parsed_data = parse_json_response(chat_completion.choices[0].message.content)
        
    else:
        raise ValueError(f"Unknown provider: {provider}")
        
    # Validate with Pydantic
    validated = ViralAnalysisResponse(**parsed_data)
    
    # Return as list of dicts for easy serialization
    return [clip.model_dump() for clip in validated.clips]
