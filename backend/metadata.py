import re
import requests


def _get_youtube_video_id(url):
    """Extract video ID from a YouTube URL."""
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None


def _get_youtube_metadata(url):
    """Fetch YouTube metadata using the free noembed/oembed API (no auth needed)."""
    video_id = _get_youtube_video_id(url)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(oembed_url, timeout=10)
        data = resp.json() if resp.status_code == 200 else {}
    except Exception:
        data = {}

    return {
        "title": data.get("title", "YouTube Video"),
        "creator": data.get("author_name", "Unknown"),
        "views": None,
        "likes": 0,
        "comments": 0,
        "duration": 0,
        "upload_date": "",
        "hashtags": [],
        "follower_count": None,
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
        "url": url,
        "platform": "youtube",
    }


def _get_yt_dlp_metadata(url):
    """Fallback: use yt-dlp for non-YouTube platforms like Instagram."""
    import yt_dlp
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        tags = info.get("tags") or []
        hashtags = [f"#{t}" for t in tags[:10]]
        follower_count = (
            info.get("channel_follower_count")
            or info.get("uploader_follower_count")
            or None
        )
        views = info.get("view_count") or info.get("play_count") or None
        return {
            "title": info.get("title") or "Unknown",
            "creator": info.get("uploader") or info.get("channel") or "Unknown",
            "views": views,
            "likes": info.get("like_count") or 0,
            "comments": info.get("comment_count") or 0,
            "duration": info.get("duration") or 0,
            "upload_date": info.get("upload_date") or "",
            "hashtags": hashtags,
            "follower_count": follower_count,
            "thumbnail": info.get("thumbnail") or "",
            "url": url,
            "platform": _detect_platform(url),
        }


def get_video_metadata(url):
    """Route to the right metadata fetcher based on platform."""
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        return _get_youtube_metadata(url)
    else:
        return _get_yt_dlp_metadata(url)


def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "instagram.com" in url_lower:
        return "instagram"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    return "unknown"


def calculate_engagement(metadata):
    """
    Engagement rate = (likes + comments) / views × 100

    Instagram note: view_count is often unavailable without auth.
    When views is None, we fall back to a 'interaction score' = likes + comments
    and flag the rate as approximate.
    """
    views = metadata.get("views")   # None means genuinely not available
    likes = metadata.get("likes") or 0
    comments = metadata.get("comments") or 0

    if views:
        return round(((likes + comments) / views) * 100, 4)

    # Fallback: return None so the UI can display "N/A"
    return None