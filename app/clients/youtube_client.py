"""YouTube search and video URL extraction client using yt-dlp."""

from __future__ import annotations

import asyncio
import functools
from typing import Any

from app.core.config import get_settings

YouTubeSearchResult = dict[str, Any]


class YouTubeClient:
    """Search YouTube and extract direct video URLs using yt-dlp."""

    def __init__(self) -> None:
        """Check whether YouTube is enabled via config."""
        self._enabled = get_settings().youtube_enabled

    async def search(self, query: str, limit: int = 3) -> dict[str, Any]:
        """Search YouTube and return video metadata."""
        if not self._enabled:
            return {
                "configured": False,
                "query": query,
                "results": [],
                "message": "YouTube integration is not enabled. Set YOUTUBE_ENABLED=true in your .env file.",
            }

        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "skip_download": True,
                "default_search": "ytsearch",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await _run_ytdl(ydl, f"ytsearch{limit}:{query}")
                entries = info.get("entries", [])
                results = []
                for entry in entries[:limit]:
                    results.append({
                        "title": entry.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        "id": entry.get("id", ""),
                        "duration": entry.get("duration", 0),
                        "channel": entry.get("channel", "") or entry.get("uploader", ""),
                        "thumbnail": entry.get("thumbnail", ""),
                    })
                return {
                    "configured": True,
                    "query": query,
                    "results": results,
                    "message": "",
                }
        except Exception as exc:
            return {
                "configured": True,
                "query": query,
                "results": [],
                "message": f"YouTube search failed: {exc}",
            }

    async def get_video_url(self, video_id: str) -> str | None:
        """Extract a direct playable video URL for the given YouTube video ID."""
        if not self._enabled:
            return None
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "best[height<=720]",
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await _run_ytdl(ydl, f"https://www.youtube.com/watch?v={video_id}")
                url = info.get("url")
                if url:
                    return str(url)
                for fmt in info.get("formats", []):
                    height = fmt.get("height")
                    url = fmt.get("url")
                    if height and height <= 720 and url:
                        return str(url)
                return None
        except Exception:
            return None


async def _run_ytdl(ydl: Any, query: str) -> dict[str, Any]:
    """Run yt-dlp extraction in a thread pool to avoid blocking the event loop."""
    return await asyncio.get_running_loop().run_in_executor(
        None, functools.partial(ydl.extract_info, query, download=False)
    )


def get_youtube_client() -> YouTubeClient:
    """Return a YouTube client instance."""
    return YouTubeClient()
