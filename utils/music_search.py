import asyncio
import os
import shutil
import tempfile
import uuid

import yt_dlp

import config


SEARCH_CACHE = {}

# Render Secret File
COOKIES_SOURCE = "/etc/secrets/youtube_cookies.txt"


def get_writable_cookies() -> str | None:
    """
    Render'dagi Secret File read-only bo'ladi.
    Shuning uchun uni /tmp ichiga nusxalab,
    yt-dlp'ga yoziladigan nusxani beramiz.
    """

    if not os.path.exists(COOKIES_SOURCE):
        return None

    # Har bir process uchun alohida vaqtinchalik cookie fayl
    cookie_dir = os.path.join(tempfile.gettempdir(), "ustax_cookies")
    os.makedirs(cookie_dir, exist_ok=True)

    cookie_path = os.path.join(
        cookie_dir,
        "youtube_cookies.txt"
    )

    try:
        shutil.copyfile(COOKIES_SOURCE, cookie_path)
        return cookie_path
    except Exception:
        return None


def get_cookie_opts() -> dict:
    """
    yt-dlp uchun cookie konfiguratsiyasi.
    Cookie bo'lmasa ham dastur ishlashda davom etadi.
    """

    cookie_file = get_writable_cookies()

    if cookie_file:
        return {
            "cookiefile": cookie_file
        }

    return {}


def search_youtube_flat(query: str, limit: int = 10) -> list:
    """
    YouTube'dan qo'shiqlarni qidiradi.
    """

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,

        # Cookie orqali autentifikatsiya
        **get_cookie_opts(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch{limit}:{query}",
                download=False
            )

    except Exception:
        return []

    entries = info.get("entries", []) if info else []

    results = []

    for entry in entries:
        if not entry:
            continue

        video_id = entry.get("id")

        title = (
            entry.get("title")
            or "Noma'lum qo'shiq"
        )

        artist = (
            entry.get("artist")
            or entry.get("uploader")
            or entry.get("channel")
            or ""
        )

        duration = entry.get("duration") or 0

        # 15 minutdan uzunlarini chiqarib tashlaymiz
        if video_id and duration <= 900:

            results.append(
                {
                    "video_id": video_id,
                    "title": title,
                    "artist": artist,
                    "duration_str": (
                        f"{int(duration // 60):02d}:"
                        f"{int(duration % 60):02d}"
                    ),
                    "duration": duration,
                }
            )

    return results


def download_yt_audio_sync(video_id: str) -> tuple:
    """
    YouTube videosidan MP3 audio yuklab oladi.
    """

    unique_id = str(uuid.uuid4())

    download_dir = os.path.join(
        config.TEMP_DIR,
        unique_id
    )

    os.makedirs(
        download_dir,
        exist_ok=True
    )

    url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    ydl_opts = {
        "format": "bestaudio/best",

        "outtmpl": os.path.join(
            download_dir,
            "%(title).50s.%(ext)s"
        ),

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],

        "quiet": True,
        "no_warnings": True,

        # Cookie konfiguratsiyasi
        **get_cookie_opts(),
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:

        # Papkani tozalash
        try:
            shutil.rmtree(
                download_dir,
                ignore_errors=True
            )
        except Exception:
            pass

        raise e

    audio_path = None

    for filename in os.listdir(download_dir):

        if filename.lower().endswith(".mp3"):

            audio_path = os.path.join(
                download_dir,
                filename
            )

            break

    return download_dir, audio_path


async def auto_cleanup_search_cache(
    search_id: str,
    delay: int = 1800
):
    """
    Qidiruv cache'ini vaqt o'tgach o'chiradi.
    """

    await asyncio.sleep(delay)

    SEARCH_CACHE.pop(
        search_id,
        None
    )
