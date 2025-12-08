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
                    SHRUTIBOTS_API_URL = (await response.text()).strip()
                    logger.info(f"ShrutiBots API loaded")
                    return
    except:
        pass
    SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
    logger.info("Using ShrutiBots fallback")

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
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SHRUTIBOTS_API_URL}/download",
                params={"url": video_id, "type": "video" if is_video else "audio"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("stream_url"):
                        return data["stream_url"], "ShrutiBots"
    except:
        pass
    return None, None

async def try_quickearn_api(video_id: str, is_video: bool = False):
    try:
        endpoint = f"{QUICKEARN_API_URL}/song/{video_id}?api={QUICKEARN_API_KEY}"
        if is_video:
            endpoint = f"{QUICKEARN_API_URL}/video/{video_id}?api={QUICKEARN_API_KEY}"
        async with aiohttp.ClientSession() as session:
            for _ in range(5):
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status", "").lower()
                        if status == "done" and data.get("link"):
                            return data["link"], "QuickEarn"
                        if status == "downloading":
                            await asyncio.sleep(5)
                            continue
                        break
                await asyncio.sleep(2)
    except:
        pass
    return None, None

async def download_with_fallback(video_id: str, file_path: str, is_video: bool = False):
    min_size = 1024 * 100 if is_video else 1024
    if os.path.exists(file_path) and os.path.getsize(file_path) > min_size:
        return True, "Cache"
    
    url, api = await try_shrutibots_api(video_id, is_video)
    if not url:
        url, api = await try_quickearn_api(video_id, is_video)
    
    if not url:
        return False, None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(sock_read=120)) as resp:
                if resp.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(16384):
                            f.write(chunk)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > min_size:
                        return True, api
    except:
        pass
    
    if os.path.exists(file_path):
        os.remove(file_path)
    return False, None

async def download_song(link: str) -> str:
    vid = link.split("v=")[-1].split("&")[0] if "v=" in link else link
    if len(vid) < 3:
        return None
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{vid}.mp3"
    success, _ = await download_with_fallback(vid, path, False)
    return path if success else None

async def download_video(link: str) -> str:
    vid = link.split("v=")[-1].split("&")[0] if "v=" in link else link
    if len(vid) < 3:
        return None
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{vid}.mp4"
    success, _ = await download_with_fallback(vid, path, True)
    return path if success else None

async def shell_cmd(cmd):
    try:
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
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
            if not msg: continue
            entities = (msg.entities or []) + (msg.caption_entities or [])
            for entity in entities:
                if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                    return entity.url or (msg.text or msg.caption or "")[entity.offset:entity.offset+entity.length]
        return None

    async def details(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            res = (await VideosSearch(link, limit=1).next())["result"][0]
            dur_sec = int(time_to_seconds(res["duration"])) if res["duration"] else 0
            return res["title"], res["duration"], dur_sec, res["thumbnails"][0]["url"].split("?")[0], res["id"]
        except:
            return None, None, None, None, None

    async def title(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["title"]
        except: return None

    async def duration(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["duration"]
        except: return None

    async def thumbnail(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            return (await VideosSearch(link, limit=1).next())["result"][0]["thumbnails"][0]["url"].split("?")[0]
        except: return None

    async def video(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            file = await download_video(link)
            return (1, file) if file else (0, "Download failed")
        except Exception as e:
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid=None):
        if videoid: link = f"https://youtube.com/playlist?list={videoid}"
        link = link.split("&")[0]
        playlist = await shell_cmd(f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}")
        return [vid.strip() for vid in playlist.split("
") if vid.strip()]

    async def track(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            res = (await VideosSearch(link, limit=1).next())["result"][0]
            return ({
                "title": res["title"],
                "link": res["link"],
                "vidid": res["id"],
                "duration_min": res["duration"],
                "thumb": res["thumbnails"][0]["url"].split("?")[0]
            }, res["id"])
        except:
            return {}, None

    async def formats(self, link: str, videoid=None):
        if videoid: link = self.base + videoid
        link = link.split("&")[0]
        try:
            ydl_opts = {"quiet": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                formats = []
                for f in info["formats"]:
                    if "dash" not in str(f.get("format_id", "")).lower():
                        formats.append({
                            "format": f.get("format", ""),
                            "filesize": f.get("filesize"),
                            "format_id": f["format_id"],
                            "ext": f["ext"],
                            "format_note": f.get("format_note", ""),
                            "yturl": link
                        })
                return formats, link
        except:
            return [], link

    async def slider(self, link: str, query_type: int, videoid=None):
        if videoid: link = self.base + videoid
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

    async def download(self, link: str, mystic=None, video=False, videoid=None, **kwargs):
        if videoid: link = self.base + videoid
        try:
            path = await download_video(link) if video else await download_song(link)
            if path and os.path.exists(path):
                size = os.path.getsize(path)
                min_size = 1024 * 100 if video else 1024
                if size >= min_size:
                    return path, True
                os.remove(path)
            return None, False
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, False
