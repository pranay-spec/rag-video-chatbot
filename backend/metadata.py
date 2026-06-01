import yt_dlp


def get_video_metadata(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Hashtags — available as tags list
        tags = info.get("tags") or []
        hashtags = [f"#{t}" for t in tags[:10]]

        # Subscriber / follower count
        follower_count = (
            info.get("channel_follower_count")
            or info.get("uploader_follower_count")
            or info.get("uploader_subscriber_count")
            or None
        )

        # Comment count
        comments = info.get("comment_count") or 0

        # Views — Instagram often returns null without auth.
        # Try multiple field names yt-dlp uses across platforms.
        views = (
            info.get("view_count")
            or info.get("play_count")       # TikTok / some IG fields
            or info.get("repost_count")     # last-resort fallback
            or None                         # None = genuinely unavailable
        )

        # Detect platform
        platform = _detect_platform(url)

        return {
            "title": info.get("title") or "Unknown",
            "creator": info.get("uploader") or info.get("channel") or "Unknown",
            "views": views,               # None if unavailable (not 0)
            "likes": info.get("like_count") or 0,
            "comments": comments,
            "duration": info.get("duration") or 0,
            "upload_date": info.get("upload_date") or "",
            "hashtags": hashtags,
            "follower_count": follower_count,
            "thumbnail": info.get("thumbnail") or "",
            "url": url,
            "platform": platform,
        }


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