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
    try:
        video_id = match.group(1)
        api = YouTubeTranscriptApi()
        t_list = api.list(video_id)
        transcript = t_list.find_transcript(['en', 'en-US', 'en-GB'])
        snippets = transcript.fetch()
        return " ".join([s.text for s in snippets])
    except Exception as e:
        print(f"Native transcript failed: {e}")
        return ""

def process_video(url: str, video_id: str) -> dict:
    start = time.time()
    print(f"\n{'='*50}")
    print(f"Processing Video {video_id}: {url}")

    # 1. Try to fetch native subtitles directly (avoids yt-dlp bot blocks!)
    transcript = ""
    if "youtube" in url or "youtu.be" in url:
        print("Attempting to fetch native YouTube transcript...")
        transcript = get_native_youtube_transcript(url)

    # 2. Fallback to downloading + Whisper if no native transcript (e.g. Instagram)
    if transcript.strip():
        print("Successfully fetched native transcript!")
    else:
        print("Native transcript failed. Downloading audio...")
        audio_file = download_audio(url, video_id)
        
        print("Transcribing with Whisper API...")
        transcript = transcribe_audio(audio_file)

    print(f"Transcript length: {len(transcript)} chars")

    if not transcript.strip():
        raise Exception(f"Empty transcript for video {video_id}. Could not extract audio or subtitles.")

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