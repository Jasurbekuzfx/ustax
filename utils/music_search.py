import asyncio
import os
import shutil
import tempfile
import uuid

import yt_dlp

import config


SEARCH_CACHE = {}

COOKIES_SOURCE = "/etc/secrets/youtube_cookies.txt"

COOKIE_DIR = os.path.join(
    tempfile.gettempdir(),
    "ustax_cookies"
)

PO_TOKEN_SERVER = "/app/bgutil-ytdlp-pot-provider/server"


def get_writable_cookies():
    """
    Render Secret File read-only.
    Cookie faylini /tmp ichiga ko'chiramiz.
    """

    if not os.path.isfile(COOKIES_SOURCE):
        return None

    os.makedirs(
        COOKIE_DIR,
        exist_ok=True
    )

    cookie_path = os.path.join(
        COOKIE_DIR,
        "youtube_cookies.txt"
    )

    try:
        shutil.copyfile(
            COOKIES_SOURCE,
            cookie_path
        )

        return cookie_path

    except Exception as e:
        print(
            f"Cookie nusxalashda xatolik: {e}"
        )
        return None


def build_youtube_options():
    """
    YouTube uchun umumiy yt-dlp sozlamalari.
    """

    opts = {
        "quiet": True,
        "no_warnings": True,

        "extractor_args": {
            "youtubepot-bgutilscript": {
                "server_home": PO_TOKEN_SERVER
            }
        }
    }

    cookie_path = get_writable_cookies()

    if cookie_path:
        opts["cookiefile"] = cookie_path

    return opts


def search_youtube_flat(
    query: str,
    limit: int = 10
) -> list:

    ydl_opts = build_youtube_options()

    ydl_opts.update({
        "extract_flat": True,
        "skip_download": True,
    })

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                f"ytsearch{limit}:{query}",
                download=False
            )

    except Exception as e:

        print(
            f"YouTube qidiruv xatosi: {e}"
        )

        raise

    entries = (
        info.get("entries", [])
        if info
        else []
    )

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

        duration = (
            entry.get("duration")
            or 0
        )

        if (
            video_id
            and duration <= 900
        ):

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


def download_yt_audio_sync(
    video_id: str
) -> tuple:

    unique_id = str(
        uuid.uuid4()
    )

    download_dir = os.path.join(
        config.TEMP_DIR,
        unique_id
    )

    os.makedirs(
        download_dir,
        exist_ok=True
    )

    url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    ydl_opts = build_youtube_options()

    ydl_opts.update({

        "format": (
            "bestaudio/best"
        ),

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
    })

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])

    except Exception:

        shutil.rmtree(
            download_dir,
            ignore_errors=True
        )

        raise

    audio_path = None

    for filename in os.listdir(
        download_dir
    ):

        if filename.lower().endswith(
            ".mp3"
        ):

            audio_path = os.path.join(
                download_dir,
                filename
            )

            break

    return (
        download_dir,
        audio_path
    )


async def auto_cleanup_search_cache(
    search_id: str,
    delay: int = 1800
):

    await asyncio.sleep(
        delay
    )

    SEARCH_CACHE.pop(
        search_id,
        None
    )
