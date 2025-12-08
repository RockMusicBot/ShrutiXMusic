import asyncio
import os
import re
import json
from typing import Union
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch
from ShrutixMusic.utils.formatters import time_to_seconds
import aiohttp
from ShrutixMusic import LOGGER

# Global configurations
logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
SHRUTIBOTS_API_URL = None
SHRUTIBOTS_FALLBACK_URL = "https://shrutibots.site"
QUICKEARN_API_URL = "https://api.thequickearn.xyz"
QUICKEARN_API_KEY = "30DxNexGenBots62dba1"

async def load_shrutibots_api_url():
    global SHRUTIBOTS_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    SHRUTIBOTS_API_URL = content.strip()
                    logger.info(f"ShrutiBots API URL loaded: {SHRUTIBOTS_API_URL}")
                    return
    except Exception:
        pass
    
    SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
    logger.info(f"Using fallback: {SHRUTIBOTS_FALLBACK_URL}")

# Initialize at startup
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_shrutibots_api_url())
    else:
        loop.run_until_complete(load_shrutibots_api_url())
except:
    pass

async def try_shrutibots_api(video_id: str, is_video: bool = False):
    global SHRUTIBOTS_API_URL
    if not SHRUTIBOTS_API_URL:
        await load_shrutibots_api_url()
    
    try:
        endpoint = f"{SHRUTIBOTS_API_URL}/download"
        params = {"url": video_id, "type": "video" if is_video else "audio"}
        logger.info(f"Trying ShrutiBots API")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    stream_url = data.get("stream_url")
                    if stream_url:
                        logger.info(f"ShrutiBots success: {video_id}")
                        return stream_url, "ShrutiBots"
                logger.warning(f"ShrutiBots failed: {response.status}")
        return None, None
    except Exception as e:
        logger.error(f"ShrutiBots error: {e}")
        return None, None

async def try_quickearn_api(video_id: str, is_video: bool = False):
    try:
        endpoint = f"{QUICKEARN_API_URL}/song/{video_id}?api={QUICKEARN_API_KEY}"
        if is_video:
            endpoint = f"{QUICKEARN_API_URL}/video/{video_id}?api={QUICKEARN_API_KEY}"
        
        logger.info(f"Trying QuickEarn API")
        async with aiohttp.ClientSession() as session:
            for attempt in range(5):
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status", "").lower()
                        
                        if status == "done":
                            download_url = data.get("link")
                            if download_url:
                                logger.info(f"QuickEarn success: {video_id}")
                                return download_url, "QuickEarn"
                        elif status == "downloading":
                            await asyncio.sleep(4 if not is_video else 8)
                            continue
                        else:
                            logger.warning(f"QuickEarn status: {status}")
                            break
                    logger.warning(f"QuickEarn failed: {response.status}")
                    break
        return None, None
    except Exception as e:
        logger.error(f"QuickEarn error: {e}")
        return None, None

async def download_with_fallback(video_id: str, file_path: str, is_video: bool = False):
    min_size = 1024 * 100 if is_video else 1024
    
    if os.path.exists(file_path) and os.path.getsize(file_path) > min_size:
        logger.info(f"Using cached file: {os.path.basename(file_path)}")
        return True, "Cache"
    
    download_url, api_name = await try_shrutibots_api(video_id, is_video)
    if not download_url:
        download_url, api_name = await try_quickearn_api(video_id, is_video)
    
    if not download_url:
        return False, None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=aiohttp.ClientTimeout(sock_read=120)) as response:
                if response.status != 200:
                    return False, None
                
                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(16384):
                        f.write(chunk)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > min_size:
                    logger.info(f"Downloaded: {os.path.basename(file_path)} via {api_name}")
                    return True, api_name
                    
    except Exception as e:
        logger.error(f"Download failed: {e}")
    
    if os.path.exists(file_path):
        os.remove(file_path)
    return False, None

async def download_song(link: str) -> str:
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if len(video_id) < 3:
        return None
    
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video_id}.mp3"
    
    success, _ = await download_with_fallback(video_id, file_path, False)
    return file_path if success and os.path.exists(file_path) else None

async def download_video(link: str) -> str:
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if len(video_id) < 3:
        return None
    
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video_id}.mp4"
    
    success, _ = await download_with_fallback(video_id, file_path, True)
    return file_path if success and os.path.exists(file_path) else None

async def shell_cmd(cmd):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return out.decode() if out else err.decode()
    except:
        return ""

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube.com|youtu.be)"

    async def exists(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> str:
        for msg in [message, getattr(message, 'reply_to_message', None)]:
            if not msg:
                continue
            for entity in (msg.entities or []) + (msg.caption_entities or []):
                if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                    return entity.url or (msg.text or msg.caption)[entity.offset:entity.offset + entity.length]
        return None

    async def details(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            duration_sec = int(time_to_seconds(result["duration"])) if result["duration"] else 0
            return (result["title"], result["duration"], duration_sec, 
                   result["thumbnails"][0]["url"].split("?")[0], result["id"])
        except:
            return None, None, None, None, None

    async def title(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["title"]
        except:
            return None

    async def duration(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["duration"]
        except:
            return None

    async def thumbnail(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["thumbnails"][0]["url"].split("?")[0]
        except:
            return None

    async def video(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            file = await download_video(link)
            return 1, file if file else ("0", "Download failed")
        except Exception as e:
            return 0, f"Error: {e}"

    async def playlist(self, link, limit, user_id, videoid=None):
        if videoid:
            link = f"https://youtube.com/playlist?list={videoid}"
        link = link.split("&")[0]
        playlist = await shell_cmd(f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}")
        return [vid.strip() for vid in playlist.split("
") if vid.strip()]

    async def track(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            result = (await VideosSearch(link, limit=1).next())["result"][0]
            return ({
                "title": result["title"],
                "link": result["link"],
                "vidid": result["id"],
                "duration_min": result["duration"],
                "thumb": result["thumbnails"][0]["url"].split("?")[0]
            }, result["id"])
        except:
            return {}, None

    async def formats(self, link: str, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            ydl_opts = {"quiet": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                return ([{
                    "format": f.get("format", ""),
                    "filesize": f.get("filesize"),
                    "format_id": f["format_id"],
                    "ext": f["ext"],
                    "format_note": f.get("format_note", ""),
                    "yturl": link
                } for f in info["formats"] if "dash" not in str(f.get("format_id", "")).lower()], link)
        except:
            return [], link

    async def slider(self, link: str, query_type: int, videoid=None):
        if videoid:
            link = self.base + videoid
        link = link.split("&")[0]
        try:
            results = (await VideosSearch(link, limit=10).next())["result"]
            if query_type < len(results):
                item = results[query_type]
                return (item["title"], item["duration"], 
                       item["thumbnails"][0]["url"].split("?")[0], item["id"])
        except:
            pass
        return None, None, None, None

    async def download(self, link: str, mystic, video=False, videoid=None, **kwargs) -> tuple:
        if videoid:
            link = self.base + videoid
        
        try:
            file_path = await download_video(link) if video else await download_song(link)
            if file_path and os.path.exists(file_path):
                size = os.path.getsize(file_path)
                min_size = 1024 * 100 if video else 1024
                if size >= min_size:
                    return file_path, True
                os.remove(file_path)
            return None, False
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, False
