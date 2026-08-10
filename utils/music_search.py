import asyncio
import os
import uuid
import shutil
import yt_dlp

import config

SEARCH_CACHE = {}

YOUTUBE_COOKIES = "/etc/secrets/youtube_cookies.txt"
PO_TOKEN_SERVER = "/app/bgutil-ytdlp-pot-provider/server"

def get_writable_cookies():
    source = "/etc/secrets/youtube_cookies.txt"
    target = os.path.join(config.TEMP_DIR, "youtube_cookies_runtime.txt")

    if not os.path.exists(source):
        raise FileNotFoundError(
            "YouTube cookie fayli topilmadi: /etc/secrets/youtube_cookies.txt"
        )

    shutil.copyfile(source, target)
    return target
def get_writable_cookies():
    source = "/etc/secrets/youtube_cookies.txt"
    target = os.path.join(config.TEMP_DIR, "youtube_cookies_runtime.txt")

    if not os.path.exists(source):
        raise FileNotFoundError(
            "YouTube cookie fayli topilmadi: /etc/secrets/youtube_cookies.txt"
        )

    shutil.copyfile(source, target)
    return target


def _youtube_opts():
    writable_cookies = get_writable_cookies()

    return {
        "quiet": True,
        "no_warnings": True,
        "cookiefile": writable_cookies,

        "extractor_args": {
            "youtubepot-bgutilscript": {
                "server_home": PO_TOKEN_SERVER,
            }
        },
    }

def search_youtube_flat(query: str, limit: int = 10) -> list:
    ydl_opts = _youtube_opts()

    ydl_opts.update({
        "extract_flat": True,
        "skip_download": True,
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"ytsearch{limit}:{query}",
            download=False
        )

    entries = info.get("entries", []) if info else []
    results = []

    for entry in entries:
        if not entry:
            continue

        video_id = entry.get("id")
        title = entry.get("title") or "Noma'lum qo'shiq"
        artist = (
            entry.get("artist")
            or entry.get("uploader")
            or entry.get("channel")
            or ""
        )
        duration = entry.get("duration") or 0

        if video_id and duration <= 900:
            results.append({
                "video_id": video_id,
                "title": title,
                "artist": artist,
                "duration_str": (
                    f"{int(duration // 60):02d}:"
                    f"{int(duration % 60):02d}"
                ),
                "duration": duration,
            })

    return results


def download_yt_audio_sync(video_id: str) -> tuple:
    unique_id = str(uuid.uuid4())
    download_dir = os.path.join(
        config.TEMP_DIR,
        unique_id
    )
    os.makedirs(download_dir, exist_ok=True)

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = _youtube_opts()

    ydl_opts.update({
        "format": "bestaudio/best",

        "outtmpl": os.path.join(
            download_dir,
            "%(title).50s.%(ext)s"
        ),

        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    audio_path = next(
        (
            os.path.join(download_dir, f)
            for f in os.listdir(download_dir)
            if f.endswith(".mp3")
        ),
        None,
    )

    return download_dir, audio_path


async def auto_cleanup_search_cache(
    search_id: str,
    delay: int = 1800
):
    await asyncio.sleep(delay)
    SEARCH_CACHE.pop(search_id, None)
