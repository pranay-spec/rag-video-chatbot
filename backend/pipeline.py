from downloader import download_audio
from transcriber import transcribe_audio
from vector_store import store_transcript
from metadata import get_video_metadata, calculate_engagement

import time


def process_video(url: str, video_id: str) -> dict:
    start = time.time()
    print(f"\n{'='*50}")
    print(f"Processing Video {video_id}: {url}")

    print("Downloading audio...")
    audio_file = download_audio(url, video_id)

    print("Transcribing with Whisper...")
    transcript = transcribe_audio(audio_file)
    print(f"Transcript length: {len(transcript)} chars")

    if not transcript.strip():
        raise Exception(f"Empty transcript for video {video_id}")

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