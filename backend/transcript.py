from youtube_transcript_api import YouTubeTranscriptApi
import re


def get_video_id(url):
    match = re.search(r"v=([^&]+)", url)

    if match:
        return match.group(1)

    match = re.search(r"youtu\.be/([^?]+)", url)

    if match:
        return match.group(1)

    return None


def get_youtube_transcript(url):

    video_id = get_video_id(url)

    print("URL:", url)
    print("VIDEO ID:", video_id)

    api = YouTubeTranscriptApi()

    transcript = api.fetch(video_id)

    text = " ".join(
        [chunk.text for chunk in transcript]
    )

    return text