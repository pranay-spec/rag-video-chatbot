import yt_dlp
import os


def download_audio(url, video_id):
    output_path = f"downloads/{video_id}.%(ext)s"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": False,
        "noplaylist": True,
        "overwrites": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        filename = ydl.prepare_filename(info)

    return filename