import asyncio
import contextlib
import json
import os
import re
import time
import random
import aiohttp
import shutil
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch

from ShrutixMusic.utils.cookie_handler import COOKIE_PATH
from ShrutixMusic.utils.database import is_on_off
from ShrutixMusic.utils.downloader import download_audio_concurrent, yt_dlp_download
from ShrutixMusic.utils.errors import capture_internal_err
from ShrutixMusic.utils.formatters import time_to_seconds
from ShrutixMusic.utils.tuning import (
    YTDLP_TIMEOUT,
    YOUTUBE_META_MAX,
    YOUTUBE_META_TTL,
)

_cache: Dict[str, Tuple[float, List[Dict]]] = {}
_cache_lock = asyncio.Lock()
_formats_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_formats_lock = asyncio.Lock()

# API URL System
YOUR_API_URL = None

# Rate limiting protection
_request_timestamps = []
_RATE_LIMIT_WINDOW = 60  # 60 seconds window
_MAX_REQUESTS_PER_WINDOW = 10  # Max 10 requests per minute

async def load_api_url():
    global YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa") as response:
                if response.status == 200:
                    content = await response.text()
                    YOUR_API_URL = content.strip()
                    print(f"✅ API URL loaded successfully: {YOUR_API_URL}")
                else:
                    print(f"❌ Failed to fetch API URL. HTTP Status: {response.status}")
    except Exception as e:
        print(f"❌ Error loading API URL: {e}")

# Initialize API URL on startup
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_api_url())
    else:
        loop.run_until_complete(load_api_url())
except RuntimeError:
    pass

def _cookiefile_path() -> Optional[str]:
    path = str(COOKIE_PATH)
    try:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception:
        pass
    return None

def _cookies_args() -> List[str]:
    p = _cookiefile_path()
    return ["--cookies", p] if p else []

async def _exec_proc(*args: str) -> Tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return b"", b"timeout"

# Rate limiting check
def _check_rate_limit():
    global _request_timestamps
    now = time.time()
    
    # Remove timestamps older than our window
    _request_timestamps = [ts for ts in _request_timestamps if now - ts < _RATE_LIMIT_WINDOW]
    
    # Check if we've exceeded the limit
    if len(_request_timestamps) >= _MAX_REQUESTS_PER_WINDOW:
        sleep_time = _RATE_LIMIT_WINDOW - (now - _request_timestamps[0])
        print(f"⚠️ [RATE LIMIT] Too many requests, sleeping for {sleep_time:.1f}s")
        time.sleep(sleep_time)
        _request_timestamps = []  # Reset after sleep
    
    # Add current timestamp
    _request_timestamps.append(now)

# Helper function for stream download
async def _download_from_stream(session: aiohttp.ClientSession, stream_url: str, file_path: str, video_id: str) -> Optional[str]:
    """Download from stream URL with enhanced timeout"""
    try:
        async with session.get(
            stream_url,
            timeout=aiohttp.ClientTimeout(total=60)  # 1 minute for audio
        ) as file_response:
            if file_response.status != 200:
                return None
            
            with open(file_path, "wb") as f:
                async for chunk in file_response.content.iter_chunked(16384):  # 16KB chunks for audio
                    f.write(chunk)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path
            else:
                return None
    except Exception:
        return None

# TELEGRAM DOWNLOAD - FAST TIMEOUTS ✅
async def get_telegram_file(telegram_link: str, video_id: str, file_type: str) -> str:
    """
    TELEGRAM DOWNLOAD - FAST TIMEOUTS
    """
    try:
        extension = ".webm" if file_type == "audio" else ".mkv"
        file_path = os.path.join("downloads", f"{video_id}{extension}")
        
        # LOCAL FILE CHECK
        if os.path.exists(file_path) and os.path.getsize(file_path) > 10240:
            print(f"✅ Telegram - Using existing file")
            return file_path
        
        parsed = urlparse(telegram_link)
        parts = parsed.path.strip("/").split("/")
        
        if len(parts) < 2:
            return None
            
        channel_name = parts[0]
        message_id = int(parts[1])
        
        print(f"📥 Telegram Download: {video_id}")
        
        from ShrutixMusic import nand
        
        # ✅ SIRF 1 ATTEMPT - FAST TIMEOUTS
        max_retries = 1
        for attempt in range(max_retries):
            try:
                # ✅ FAST TIMEOUTS - Kam time
                timeout_msg = 6.0  # 10s → 6s ✅
                timeout_download = 12.0  # 20s → 12s ✅
                
                # GET MESSAGE
                msg = await asyncio.wait_for(
                    app.get_messages(channel_name, message_id), 
                    timeout=timeout_msg
                )
                
                if not msg or not msg.document and not msg.video and not msg.audio:
                    print(f"❌ Telegram message not found")
                    return None
                
                os.makedirs("downloads", exist_ok=True)
                
                # DOWNLOAD WITH FAST TIMEOUT
                await asyncio.wait_for(
                    msg.download(file_name=file_path),
                    timeout=timeout_download
                )
                
                # FILE VERIFICATION
                if os.path.exists(file_path) and os.path.getsize(file_path) > 10240:
                    print(f"✅ Telegram Download Successful")
                    return file_path  # SUCCESS
                else:
                    print(f"❌ Telegram download failed - file too small")
                    return None
                    
            except asyncio.TimeoutError:
                print(f"❌ Telegram timeout after {timeout_msg}s")
                return None
            except Exception as e:
                print(f"❌ Telegram error: {e}")
                return None
        
        return None
        
    except Exception as e:
        print(f"❌ Telegram overall error: {e}")
        return None

# TELEGRAM FIRST - FAST TIMEOUTS ✅
async def download_via_api(link: str, download_type: str = "audio") -> Optional[str]:
    """TELEGRAM FIRST - FAST TIMEOUTS"""
    
    # VIDEO KE LIYE DIRECT yt-dlp
    if download_type == "video":
        return None
    
    global YOUR_API_URL
    
    if not YOUR_API_URL:
        await load_api_url()
        if not YOUR_API_URL:
            return None
    
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    extension = ".webm" if download_type == "audio" else ".mkv"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}{extension}")

    # LOCAL FILE CHECK
    if os.path.exists(file_path) and os.path.getsize(file_path) > 10240:
        print(f"✅ Telegram - Using existing file")
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": download_type}
            
            # ✅ SIRF 1 ATTEMPT - FAST TIMEOUT
            max_api_attempts = 1
            for api_attempt in range(max_api_attempts):
                try:
                    # ✅ FAST TIMEOUT - Kam time
                    async with session.get(
                        f"{YOUR_API_URL}/download",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=15)  # 25s → 15s ✅
                    ) as response:
                        if response.status != 200:
                            print(f"❌ Telegram API failed with status: {response.status}")
                            return None
                            
                        data = await response.json()
                        
                        # TELEGRAM LINK - HIGHEST PRIORITY
                        if data.get("link") and "t.me" in str(data.get("link")):
                            telegram_link = data["link"]
                            print(f"📱 Telegram Link Received")
                            
                            # TELEGRAM DOWNLOAD - SIRF 1 ATTEMPT
                            downloaded_file = await get_telegram_file(telegram_link, video_id, download_type)
                            if downloaded_file:
                                return downloaded_file  # TELEGRAM SUCCESS
                            else:
                                print(f"❌ Telegram download failed")
                                return None
                        
                        # STREAM URL
                        elif data.get("status") == "success" and data.get("stream_url"):
                            return None
                        
                        else:
                            print(f"❌ No Telegram link in API response")
                            return None
                            
                except asyncio.TimeoutError:
                    print(f"⏰ Telegram API TIMEOUT after 15 seconds")
                    return None
                except Exception as e:
                    print(f"❌ Telegram API ERROR: {str(e)}")
                    return None

            return None

    except Exception as e:
        print(f"❌ Telegram overall error: {e}")
        return None

@capture_internal_err
async def cached_youtube_search(query: str) -> List[Dict]:
    key = f"q:{query}"
    now = time.time()
    async with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if now - ts < YOUTUBE_META_TTL:
                return val
            _cache.pop(key, None)
        if len(_cache) > YOUTUBE_META_MAX:
            _cache.clear()
    try:
        data = await VideosSearch(query, limit=1).next()
        result = data.get("result", [])
    except Exception:
        result = []
    if result:
        async with _cache_lock:
            _cache[key] = (now, result)
    return result


class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_pattern = re.compile(r"(?:youtube\.com|youtu\.be)")

    def _prepare_link(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # URL extraction method
    @capture_internal_err
    async def url(self, message: Message) -> Optional[str]:
        """
        Extract YouTube URL from message
        """
        msgs = [message] + (
            [message.reply_to_message] if message.reply_to_message else []
        )
        for msg in msgs:
            text = msg.text or msg.caption or ""
            entities = msg.entities or msg.caption_entities or []
            for ent in entities:
                if ent.type == MessageEntityType.URL:
                    url = text[ent.offset : ent.offset + ent.length]
                    if self._url_pattern.search(url):
                        return url
                if ent.type == MessageEntityType.TEXT_LINK:
                    url = ent.url
                    if self._url_pattern.search(url):
                        return url
        return None

    @capture_internal_err
    async def exists(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> bool:
        return bool(self._url_pattern.search(self._prepare_link(link, videoid)))

    @capture_internal_err
    async def _fetch_video_info(
        self, query: str, *, use_cache: bool = True
    ) -> Optional[Dict]:
        q = self._prepare_link(query)
        if use_cache and not q.startswith("http"):
            res = await cached_youtube_search(q)
            return res[0] if res else None
        data = await VideosSearch(q, limit=1).next()
        result = data.get("result", [])
        return result[0] if result else None

    @capture_internal_err
    async def is_live(self, link: str) -> bool:
        # Rate limiting check
        _check_rate_limit()
        
        prepared = self._prepare_link(link)
        stdout, _ = await _exec_proc(
            "yt-dlp", *(_cookies_args()), "--dump-json", prepared
        )
        if not stdout:
            return False
        try:
            info = json.loads(stdout.decode())
            return bool(info.get("is_live"))
        except json.JSONDecodeError:
            return False

    @capture_internal_err
    async def details(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], int, str, str]:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        if not info:
            raise ValueError("Video not found")
        dt = info.get("duration")
        ds = int(time_to_seconds(dt)) if dt else 0
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[0].get("url", "")
        ).split("?")[0]
        return info.get("title", ""), dt, ds, thumb, info.get("id", "")

    @capture_internal_err
    async def title(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("title", "") if info else ""

    @capture_internal_err
    async def duration(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Optional[str]:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("duration") if info else None

    @capture_internal_err
    async def thumbnail(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        if info:
            thumb = info.get("thumbnail") or info.get("thumbnails", [{}])[0].get("url", "")
            return thumb.split("?")[0] if thumb else ""
        return ""

    @capture_internal_err
    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._prepare_link(link, videoid)
        
        # Rate limiting check - IMPORTANT!
        _check_rate_limit()
        
        print(f"🚀 [VIDEO] Using direct yt-dlp with cookies: {link}")
        
        # Enhanced yt-dlp command with better error handling
        ytdlp_args = [
            "yt-dlp",
            *(_cookies_args()),
            "--no-warnings",
            "--geo-bypass",
            "--force-ipv4",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]/best",
            link,
        ]
        
        stdout, stderr = await _exec_proc(*ytdlp_args)
        
        if stdout:
            stream_url = stdout.decode().split("\n")[0]
            if stream_url and stream_url.startswith('http'):
                print(f"✅ [VIDEO] Stream URL fetched: {stream_url[:100]}...")
                return (1, stream_url)
            else:
                print(f"❌ [VIDEO] Invalid stream URL received")
                return (0, "Invalid stream URL")
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            
            # Handle specific errors
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"🚫 [RATE LIMITED] YouTube blocking requests, waiting 30 seconds...")
                await asyncio.sleep(30)
                return (0, "Rate limited, please try again later")
            elif "403" in error_msg:
                print(f"🔒 [FORBIDDEN] YouTube blocking access, trying alternative method...")
                return await self._try_alternative_format(link)
            else:
                print(f"❌ [VIDEO] yt-dlp failed: {error_msg[:200]}...")
                return (0, error_msg)

    async def _try_alternative_format(self, link: str) -> Tuple[int, str]:
        """Try alternative formats when main format fails"""
        print(f"🔄 [VIDEO] Trying alternative format for: {link}")
        
        format_options = [
            "best[height<=480]",
            "best[ext=mp4]", 
            "best",
            "worst"
        ]
        
        for fmt in format_options:
            print(f"🔄 [VIDEO] Trying format: {fmt}")
            stdout, stderr = await _exec_proc(
                "yt-dlp",
                *(_cookies_args()),
                "--no-warnings",
                "-g",
                "-f",
                fmt,
                link,
            )
            
            if stdout:
                stream_url = stdout.decode().split("\n")[0]
                if stream_url and stream_url.startswith('http'):
                    print(f"✅ [VIDEO] Alternative format success: {fmt}")
                    return (1, stream_url)
            
            await asyncio.sleep(1)
        
        return (0, "All format attempts failed")

    @capture_internal_err
    async def playlist(
        self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None
    ) -> List[str]:
        if videoid:
            link = self.playlist_url + str(videoid)
        link = link.split("&")[0]
        
        # Rate limiting check
        _check_rate_limit()
        
        stdout, _ = await _exec_proc(
            "yt-dlp",
            *(_cookies_args()),
            "-i",
            "--get-id",
            "--flat-playlist",
            "--playlist-end",
            str(limit),
            "--skip-download",
            link,
        )
        items = stdout.decode().strip().split("\n") if stdout else []
        return [i for i in items if i]

    @capture_internal_err
    async def track(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[Dict, str]:
        try:
            info = await self._fetch_video_info(self._prepare_link(link, videoid))
            if not info:
                raise ValueError("Track not found via API")
        except Exception:
            # Rate limiting check
            _check_rate_limit()
            
            prepared = self._prepare_link(link, videoid)
            stdout, _ = await _exec_proc(
                "yt-dlp", *(_cookies_args()), "--dump-json", prepared
            )
            if not stdout:
                raise ValueError("Track not found (yt-dlp fallback)")
            info = json.loads(stdout.decode())
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[0].get("url", "")
        ).split("?")[0]
        details = {
            "title": info.get("title", ""),
            "link": info.get("webpage_url", self._prepare_link(link, videoid)),
            "vidid": info.get("id", ""),
            "duration_min": info.get("duration")
            if isinstance(info.get("duration"), str)
            else None,
            "thumb": thumb,
        }
        return details, info.get("id", "")

    @capture_internal_err
    async def formats(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[List[Dict], str]:
        link = self._prepare_link(link, videoid)
        key = f"f:{link}"
        now = time.time()
        async with _formats_lock:
            cached = _formats_cache.get(key)
            if cached and now - cached[0] < YOUTUBE_META_TTL:
                return cached[1], cached[2]

        # Rate limiting check
        _check_rate_limit()
        
        opts = {"quiet": True}
        cf = _cookiefile_path()
        if cf:
            opts["cookiefile"] = cf
        out: List[Dict] = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                for fmt in info.get("formats", []):
                    # Skip dash formats
                    if "dash" in str(fmt.get("format", "")).lower():
                        continue
                    # Check for required keys
                    if not any(k in fmt for k in ("filesize", "filesize_approx")):
                        continue
                    if not all(k in fmt for k in ("format", "format_id", "ext", "format_note")):
                        continue
                    size = fmt.get("filesize") or fmt.get("filesize_approx")
                    if not size:
                        continue
                    out.append(
                        {
                            "format": fmt["format"],
                            "filesize": size,
                            "format_id": fmt["format_id"],
                            "ext": fmt["ext"],
                            "format_note": fmt["format_note"],
                            "yturl": link,
                        }
                    )
        except Exception:
            pass

        async with _formats_lock:
            if len(_formats_cache) > YOUTUBE_META_MAX:
                _formats_cache.clear()
            _formats_cache[key] = (now, out, link)

        return out, link

    @capture_internal_err
    async def slider(
        self, link: str, query_type: int, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], str, str]:
        data = await VideosSearch(self._prepare_link(link, videoid), limit=10).next()
        results = data.get("result", [])
        if not results or query_type >= len(results):
            raise IndexError(
                f"Query type index {query_type} out of range (found {len(results)} results)"
            )
        r = results[query_type]
        return (
            r.get("title", ""),
            r.get("duration"),
            r.get("thumbnails", [{}])[0].get("url", "").split("?")[0],
            r.get("id", ""),
        )

    @capture_internal_err
    async def download(
        self,
        link: str,
        mystic,
        *,
        video: Union[bool, str, None] = None,
        videoid: Union[str, bool, None] = None,
        songaudio: Union[bool, str, None] = None,
        songvideo: Union[bool, str, None] = None,
        format_id: Union[bool, str, None] = None,
        title: Union[bool, str, None] = None,
    ) -> Union[Tuple[str, Optional[bool]], Tuple[None, None]]:
        link = self._prepare_link(link, videoid)
        video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
        
        # ✅ COMMON FILE PATH CHECK - HAR BAAR PEHLE YE KARO
        extension = ".webm" if not video else ".mp4"
        common_file_path = os.path.join("downloads", f"{video_id}{extension}")
        
        if os.path.exists(common_file_path) and os.path.getsize(common_file_path) > 10240:
            print(f"✅ Common local file found: {common_file_path}")
            return common_file_path, True

        # VIDEO KE LIYE - STREAM ONLY (BEST) ✅
        if songvideo or video:
            # ✅ PEHLE LOCAL FILE CHECK (FASTEST) - Agar koi existing file hai
            if os.path.exists(common_file_path) and os.path.getsize(common_file_path) > 10240:
                print(f"✅ Video local file found: {common_file_path}")
                return common_file_path, True
            
            # ✅ DIRECT STREAM - FASTEST PLAYBACK
            print(f"🎬 Getting stream URL for video: {video_id}")
            status, stream_url = await self.video(link)
            if status == 1:
                print(f"🎬 Using stream URL (instant play)")
                return stream_url, None
            else:
                print(f"❌ Stream failed: {stream_url}")
                return None, None

        # AUDIO KE LIYE - FAST TELEGRAM TIMEOUTS ✅
        else:
            # TELEGRAM FIRST - WITH FAST TIMEOUTS
            api_result = await download_via_api(link, "audio")
            if api_result:
                print(f"✅ Telegram success")
                return api_result, True
            else:
                print(f"🔄 Telegram failed after 1 attempt, switching to yt-dlp immediately")
            
            # ✅ YT-DLP SE PEHLE DOUBLE CHECK COMMON FILE
            if os.path.exists(common_file_path) and os.path.getsize(common_file_path) > 10240:
                print(f"✅ Common file found before yt-dlp - No download needed")
                return common_file_path, True
            
            # ✅ YT-DLP FALLBACK - WITH FILE MANAGEMENT
            if await is_on_off(1):
                p = await yt_dlp_download(link, type="audio")
                if p:
                    # ✅ CHECK IF DOWNLOADED FILE IS IN COMMON LOCATION
                    if p == common_file_path:
                        print(f"✅ yt-dlp success - File already in common location")
                        return p, True
                    else:
                        # ✅ MOVE FILE TO COMMON LOCATION
                        try:
                            shutil.move(p, common_file_path)
                            print(f"✅ yt-dlp file moved to common location: {common_file_path}")
                            return common_file_path, True
                        except Exception as e:
                            print(f"⚠️ Could not move yt-dlp file: {e}, using original")
                            return p, True
                else:
                    print(f"❌ yt-dlp also failed")
            
            # ✅ CONCURRENT FALLBACK - WITH FILE MANAGEMENT
            p = await download_audio_concurrent(link)
            if p:
                # ✅ CHECK IF DOWNLOADED FILE IS IN COMMON LOCATION
                if p == common_file_path:
                    print(f"✅ yt-dlp concurrent success - File already in common location")
                    return p, True
                else:
                    # ✅ MOVE FILE TO COMMON LOCATION
                    try:
                        shutil.move(p, common_file_path)
                        print(f"✅ yt-dlp concurrent file moved to common location: {common_file_path}")
                        return common_file_path, True
                    except Exception as e:
                        print(f"⚠️ Could not move concurrent file: {e}, using original")
                        return p, True
            else:
                print(f"❌ All download methods failed")
                return None, None
