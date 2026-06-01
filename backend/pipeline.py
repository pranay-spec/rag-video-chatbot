from downloader import download_audio
from transcriber import transcribe_audio
from vector_store import store_transcript
from metadata import get_video_metadata, calculate_engagement

import time


import re
from youtube_transcript_api import YouTubeTranscriptApi

def get_native_youtube_transcript(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([0-9A-Za-z_-]{11})", url)
    if not match:
        return ""
    vid = match.group(1)
    try:
        api = YouTubeTranscriptApi()
        t_list = api.list(vid)
        # Try manually created first, then auto-generated
        try:
            transcript = t_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            transcript = t_list.find_generated_transcript(['en'])
        snippets = transcript.fetch()
        return " ".join([s.text for s in snippets])
    except Exception as e:
        print(f"Native transcript failed: {e}")
        return ""

def _is_youtube(url: str) -> bool:
    u = url.lower()
    return "youtube.com" in u or "youtu.be" in u

def process_video(url: str, video_id: str) -> dict:
    start = time.time()
    print(f"\n{'='*50}")
    print(f"Processing Video {video_id}: {url}")

    transcript = ""

    if _is_youtube(url):
        # YouTube: try native transcript API first (fastest, always works on cloud)
        print("Fetching YouTube transcript via native API...")
        
        # Verify it's a valid 11-character YouTube ID
        match = re.search(r"(?:v=|youtu\.be/|shorts/)([0-9A-Za-z_-]{11})", url)
        if not match:
            raise Exception("Invalid YouTube URL. Please check for typos (the video ID must be 11 characters long).")
            
        vid = match.group(1)
        transcript = get_native_youtube_transcript(url)

        if not transcript.strip():
            # Check if it's genuinely a deleted/private video by making a quick oembed check
            import requests
            r = requests.get(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json', timeout=5)
            if r.status_code == 404:
                raise Exception("This video is deleted, private, or the URL is incorrect (404 Not Found).")
                
            # Fallback: download audio with yt-dlp + transcribe with Whisper
            print("No native captions found. Trying audio download + Whisper...")
            try:
                audio_file = download_audio(url, video_id)
                print("Transcribing with Whisper API...")
                transcript = transcribe_audio(audio_file)
            except Exception as e:
                error_msg = str(e)
                print(f"Audio download fallback also failed: {error_msg}")
                if "404" in error_msg:
                    raise Exception("This video is deleted, private, or the URL is incorrect (404 Not Found).")
                else:
                    raise Exception(
                        f"This video lacks captions. Attempting to download the raw audio failed because YouTube blocks traffic from free cloud server IPs (Render.com) to prevent bots. "
                        f"In a production environment, this is solved using residential proxies. Please test with a video that has captions!"
                    )
    else:
        # Non-YouTube (Instagram, etc): use yt-dlp + Whisper
        print("Downloading audio...")
        audio_file = download_audio(url, video_id)
        print("Transcribing with Whisper API...")
        transcript = transcribe_audio(audio_file)

    print(f"Transcript length: {len(transcript)} chars")

    if not transcript.strip():
        raise Exception(f"Empty transcript for video {video_id}.")

    print("Chunking + embedding into ChromaDB...")
    num_chunks = store_transcript(transcript, video_id)

    print("Fetching metadata...")
    metadata = get_video_metadata(url)

    engagement_rate = calculate_engagement(metadata)

    elapsed = round(time.time() - start, 2)
    print(f"Done in {elapsed}s — {num_chunks} chunks stored")

    likes = metadata.get("likes") or 0
    comments = metadata.get("comments") or 0
    interaction_score = likes + comments 
    return {
        "video_id": video_id,
        "chunks": num_chunks,
        "engagement_rate": engagement_rate,       # None for Instagram (no views)
        "interaction_score": interaction_score,   # always available
        "views_available": metadata.get("views") is not None,
        "metadata": metadata,
        "transcript_preview": transcript[:300],
    }