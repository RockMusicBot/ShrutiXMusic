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

# Global API URLs
SHRUTIBOTS_API_URL = None  # Primary API - ShrutiBots (from pastebin)
SHRUTIBOTS_FALLBACK_URL = "https://shrutibots.site"
QUICKEARN_API_URL = "https://api.video.thequickearn.xyz"
QUICKEARN_API_KEY = "30DxNexGenBots62dba1"

# Load ShrutiBots API URL from pastebin
async def load_shrutibots_api_url():
    global SHRUTIBOTS_API_URL
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    SHRUTIBOTS_API_URL = content.strip()
                    logger.info(f"ShrutiBots API URL loaded successfully: {SHRUTIBOTS_API_URL}")
                else:
                    SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
                    logger.info(f"Using fallback ShrutiBots API URL: {SHRUTIBOTS_FALLBACK_URL}")
    except Exception as e:
        SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
        logger.info(f"Using fallback ShrutiBots API URL: {e}")

# Initialize ShrutiBots API URL on startup
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_shrutibots_api_url())
    else:
        loop.run_until_complete(load_shrutibots_api_url())
except RuntimeError:
    pass

async def try_shrutibots_api(video_id: str, is_video: bool = False):
    """Try downloading from ShrutiBots API (Format 1)"""
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    # Ensure ShrutiBots API URL is loaded
    global SHRUTIBOTS_API_URL
    if not SHRUTIBOTS_API_URL:
        await load_shrutibots_api_url()
        if not SHRUTIBOTS_API_URL:
            SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
    
    try:
        endpoint = f"{SHRUTIBOTS_API_URL}/download"
        
        if is_video:
            params = {"url": video_id, "type": "video"}
        else:
            params = {"url": video_id, "type": "audio"}
        
        logger.info(f"Trying ShrutiBots API: {endpoint} with params: {params}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                logger.info(f"ShrutiBots API Response Status: {response.status}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"ShrutiBots API Response Data: {data}")
                        stream_url = data.get("stream_url")
                        
                        if stream_url:
                            logger.info(f"ShrutiBots API successful for {video_id}")
                            return stream_url, "ShrutiBots"
                        else:
                            logger.warning(f"ShrutiBots API: No stream_url in response")
                    except json.JSONDecodeError as e:
                        logger.error(f"ShrutiBots API: Invalid JSON response: {e}")
                else:
                    error_text = await response.text()
                    logger.warning(f"ShrutiBots API failed with status: {response.status}")
        
        return None, None
    except Exception as e:
        logger.error(f"ShrutiBots API error: {str(e)}")
        return None, None

async def try_quickearn_api(video_id: str, is_video: bool = False):
    """Try downloading from QuickEarn API"""
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    try:
        # Try Format 1: /download endpoint with api_key parameter
        endpoint_format1 = f"{QUICKEARN_API_URL}/download"
        params_format1 = {
            "url": video_id, 
            "type": "video" if is_video else "audio",
            "api_key": QUICKEARN_API_KEY
        }
        
        logger.info(f"Trying QuickEarn API Format 1: {endpoint_format1} with params: {params_format1}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint_format1,
                params=params_format1,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                logger.info(f"QuickEarn Format 1 Response Status: {response.status}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"QuickEarn Format 1 Response Data: {data}")
                        
                        # Check response format
                        if "stream_url" in data:
                            stream_url = data.get("stream_url")
                            if stream_url:
                                logger.info(f"QuickEarn API (Format 1) successful for {video_id}")
                                return stream_url, "QuickEarn"
                        
                        # If "link" in data (Format 2 style)
                        elif "link" in data:
                            stream_url = data.get("link")
                            if stream_url:
                                logger.info(f"QuickEarn API (Format 1 with link) successful for {video_id}")
                                return stream_url, "QuickEarn"
                    except json.JSONDecodeError as e:
                        logger.error(f"QuickEarn Format 1: Invalid JSON response: {e}")
        
        # If Format 1 fails, try Format 2: Direct download endpoint
        logger.info(f"QuickEarn Format 1 failed, trying direct endpoint...")
        
        # Try direct download endpoints
        if is_video:
            endpoints_to_try = [
                f"{QUICKEARN_API_URL}/video/{video_id}",
                f"{QUICKEARN_API_URL}/download/video/{video_id}",
                f"{QUICKEARN_API_URL}/api/video/{video_id}"
            ]
        else:
            endpoints_to_try = [
                f"{QUICKEARN_API_URL}/song/{video_id}",
                f"{QUICKEARN_API_URL}/download/song/{video_id}",
                f"{QUICKEARN_API_URL}/api/song/{video_id}"
            ]
        
        # Also try with API key parameter
        endpoints_with_key = []
        for endpoint in endpoints_to_try:
            endpoints_with_key.append(f"{endpoint}?api={QUICKEARN_API_KEY}")
            endpoints_with_key.append(f"{endpoint}?api_key={QUICKEARN_API_KEY}")
            endpoints_with_key.append(f"{endpoint}?key={QUICKEARN_API_KEY}")
        
        all_endpoints = endpoints_to_try + endpoints_with_key
        
        for endpoint in all_endpoints:
            logger.info(f"Trying QuickEarn endpoint: {endpoint}")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        endpoint,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        logger.info(f"QuickEarn endpoint {endpoint} Status: {response.status}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"QuickEarn endpoint {endpoint} Response: {data}")
                                
                                # Check various response formats
                                if "stream_url" in data:
                                    stream_url = data.get("stream_url")
                                    if stream_url:
                                        logger.info(f"QuickEarn API successful for {video_id} via {endpoint}")
                                        return stream_url, "QuickEarn"
                                
                                elif "link" in data:
                                    stream_url = data.get("link")
                                    if stream_url:
                                        logger.info(f"QuickEarn API successful for {video_id} via {endpoint}")
                                        return stream_url, "QuickEarn"
                                
                                elif "url" in data:
                                    stream_url = data.get("url")
                                    if stream_url:
                                        logger.info(f"QuickEarn API successful for {video_id} via {endpoint}")
                                        return stream_url, "QuickEarn"
                                
                                elif "download_url" in data:
                                    stream_url = data.get("download_url")
                                    if stream_url:
                                        logger.info(f"QuickEarn API successful for {video_id} via {endpoint}")
                                        return stream_url, "QuickEarn"
                            except json.JSONDecodeError:
                                # Maybe it's a direct download URL
                                content_type = response.headers.get('Content-Type', '')
                                if 'audio' in content_type or 'video' in content_type or 'application/octet-stream' in content_type:
                                    # It might be a direct file
                                    logger.info(f"QuickEarn API returned direct content for {video_id}")
                                    # Return a placeholder to indicate success
                                    return endpoint, "QuickEarn-Direct"
            except Exception as e:
                logger.warning(f"QuickEarn endpoint {endpoint} error: {e}")
                continue
        
        logger.warning(f"QuickEarn API all endpoints failed for {video_id}")
        return None, None
        
    except Exception as e:
        logger.error(f"QuickEarn API error: {str(e)}")
        return None, None

async def download_with_fallback(video_id: str, file_path: str, is_video: bool = False):
    """Download file with fallback mechanism"""
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    # Try SHRUTIBOTS API first (Primary)
    download_url, api_name = await try_shrutibots_api(video_id, is_video)
    
    # If SHRUTIBOTS fails, try QUICKEARN API (Secondary)
    if not download_url:
        logger.warning(f"ShrutiBots API failed for {video_id}, trying QuickEarn API...")
        download_url, api_name = await try_quickearn_api(video_id, is_video)
    
    if not download_url:
        logger.error(f"Both APIs failed for {video_id}")
        return False, None
    
    # Download the actual file
    try:
        timeout = aiohttp.ClientTimeout(total=600 if is_video else 300)
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=timeout) as response:
                if response.status != 200:
                    logger.error(f"Download failed with status: {response.status}")
                    return False, None
                
                # Get file extension from Content-Type or URL
                content_type = response.headers.get('Content-Type', '')
                if is_video:
                    default_ext = '.mp4'
                    if 'mp4' in content_type:
                        file_path = file_path.replace('.mp4', '.mp4')
                    elif 'webm' in content_type:
                        file_path = file_path.replace('.mp4', '.webm')
                else:
                    default_ext = '.mp3'
                    if 'mpeg' in content_type or 'mp3' in content_type:
                        file_path = file_path.replace('.mp3', '.mp3')
                    elif 'm4a' in content_type:
                        file_path = file_path.replace('.mp3', '.m4a')
                    elif 'webm' in content_type:
                        file_path = file_path.replace('.mp3', '.webm')
                
                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(16384):
                        f.write(chunk)
                
                logger.info(f"Downloaded {video_id} using {api_name}")
                return True, api_name
    except Exception as e:
        logger.error(f"Download error for {video_id}: {e}")
        return False, None

async def download_song(link: str) -> str:
    """Download audio from YouTube"""
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        return None
    
    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Check for existing file first
    for ext in ["mp3", "m4a", "webm"]:
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(file_path):
            return file_path
    
    # If not exists, create new file path
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    
    # Try download using APIs with fallback
    success, api_used = await download_with_fallback(video_id, file_path, is_video=False)
    
    if success and os.path.exists(file_path):
        logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
        logger.info(f"Audio downloaded successfully for {video_id} using {api_used}")
        return file_path
    
    return None

async def download_video(link: str) -> str:
    """Download video from YouTube"""
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        return None
    
    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Check for existing file first
    for ext in ["mp4", "webm", "mkv"]:
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(file_path):
            return file_path
    
    # If not exists, create new file path
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
    
    # Try download using APIs with fallback
    success, api_used = await download_with_fallback(video_id, file_path, is_video=True)
    
    if success and os.path.exists(file_path):
        logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
        logger.info(f"Video downloaded successfully for {video_id} using {api_used}")
        return file_path
    
    return None

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            downloaded_file = await download_video(link)
            if downloaded_file:
                return 1, downloaded_file
            else:
                return 0, "Video download failed from both APIs"
        except Exception as e:
            return 0, f"Video download error: {e}"

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = [key for key in playlist.split("\n") if key]
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    if "dash" not in str(format["format"]).lower():
                        formats_available.append(
                            {
                                "format": format["format"],
                                "filesize": format.get("filesize"),
                                "format_id": format["format_id"],
                                "ext": format["ext"],
                                "format_note": format["format_note"],
                                "yturl": link,
                            }
                        )
                except:
                    continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link

        try:
            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)
            
            if downloaded_file:
                return downloaded_file, True
            else:
                return None, False
        except Exception as e:
            logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
            logger.error(f"Download error in YouTubeAPI.download: {e}")
            return None, False
    
