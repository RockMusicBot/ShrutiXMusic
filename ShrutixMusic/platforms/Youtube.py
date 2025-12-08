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
QUICKEARN_API_URL = "https://api.thequickearn.xyz"  # FIXED: Removed 'video.'
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
    """Try downloading from ShrutiBots API"""
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
    """Try downloading from QuickEarn API with retry logic"""
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    try:
        # Single correct endpoint - logs se pata chala
        endpoint = f"{QUICKEARN_API_URL}/song/{video_id}?api={QUICKEARN_API_KEY}"
        if is_video:
            endpoint = f"{QUICKEARN_API_URL}/video/{video_id}?api={QUICKEARN_API_KEY}"
        
        logger.info(f"Trying QuickEarn API: {endpoint}")
        
        async with aiohttp.ClientSession() as session:
            # "downloading" status ke liye retry logic
            for attempt in range(10):  # Max 10 attempts
                try:
                    async with session.get(
                        endpoint,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        logger.info(f"QuickEarn API Response Status: {response.status}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"QuickEarn API Response: {data}")
                                
                                status = data.get("status", "").lower()
                                
                                if status == "done":
                                    download_url = data.get("link")
                                    if download_url:
                                        logger.info(f"QuickEarn API successful for {video_id}")
                                        return download_url, "QuickEarn"
                                    else:
                                        logger.warning(f"QuickEarn API: No download link in response")
                                        break
                                
                                elif status == "downloading":
                                    # Wait and retry
                                    wait_time = 4 if not is_video else 8
                                    logger.info(f"QuickEarn API: Status 'downloading', waiting {wait_time}s (attempt {attempt+1}/10)")
                                    await asyncio.sleep(wait_time)
                                    continue
                                
                                else:
                                    # Agar 'error' ya koi aur status ho
                                    error_msg = data.get("error") or data.get("message") or f"Unknown status '{status}'"
                                    logger.warning(f"QuickEarn API: {error_msg}")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"QuickEarn API: Invalid JSON response: {e}")
                                break
                        
                        else:
                            error_text = await response.text()
                            logger.warning(f"QuickEarn API failed with status: {response.status}, Error: {error_text}")
                            break
                
                except Exception as e:
                    logger.error(f"QuickEarn API request error: {e}")
                    if attempt < 9:  # Last attempt se pehle
                        await asyncio.sleep(2)
                        continue
                    else:
                        break
            
            logger.warning(f"QuickEarn API max retries reached or failed for {video_id}")
            return None, None
            
    except Exception as e:
        logger.error(f"QuickEarn API error: {str(e)}")
        return None, None

async def download_with_fallback(video_id: str, file_path: str, is_video: bool = False):
    """Download file with fallback mechanism"""
    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
    
    # DEBUG: Pehle check if file already exists
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 1024:  # At least 1KB
            logger.info(f"File already exists: {file_path}, Size: {file_size} bytes")
            return True, "ExistingFile"
    
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
                
                # DEBUG: Content info
                content_length = response.headers.get('Content-Length', 'Unknown')
                content_type = response.headers.get('Content-Type', 'Unknown')
                logger.info(f"Download Content-Length: {content_length}, Content-Type: {content_type}")
                
                # File download karein
                total_written = 0
                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(16384):
                        f.write(chunk)
                        total_written += len(chunk)
                
                # DEBUG: File size check
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    logger.info(f"File saved successfully: {file_path}, Size: {file_size} bytes")
                    
                    if file_size < 1024:  # Less than 1KB
                        logger.error(f"File too small ({file_size} bytes), likely corrupt")
                        os.remove(file_path)
                        return False, None
                    
                    return True, api_name
                else:
                    logger.error(f"File not created after download")
                    return False, None
                    
    except Exception as e:
        logger.error(f"Download error for {video_id}: {e}")
        # Agar file bani hai to delete karein
        if os.path.exists(file_path):
            os.remove(file_path)
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
            file_size = os.path.getsize(file_path)
            if file_size > 1024:  # Valid file check
                logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
                logger.info(f"Using existing file: {file_path}, Size: {file_size} bytes")
                return file_path
    
    # If not exists, create new file path
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    
    # Try download using APIs with fallback
    success, api_used = await download_with_fallback(video_id, file_path, is_video=False)
    
    if success and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
        if file_size > 1024:
            logger.info(f"Audio downloaded successfully for {video_id} using {api_used}, Size: {file_size} bytes")
            return file_path
        else:
            logger.error(f"Downloaded file too small: {file_size} bytes")
            os.remove(file_path)
            return None
    
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
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 100:  # At least 100KB for video
                logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
                logger.info(f"Using existing video file: {file_path}, Size: {file_size} bytes")
                return file_path
    
    # If not exists, create new file path
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
    
    # Try download using APIs with fallback
    success, api_used = await download_with_fallback(video_id, file_path, is_video=True)
    
    if success and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
        if file_size > 1024 * 100:  # At least 100KB for video
            logger.info(f"Video downloaded successfully for {video_id} using {api_used}, Size: {file_size} bytes")
            return file_path
        else:
            logger.error(f"Downloaded video file too small: {file_size} bytes")
            os.remove(file_path)
            return None
    
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
                # Final validation check
                if os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file)
                    logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
                    
                    if video and file_size < 1024 * 100:  # Video: at least 100KB
                        logger.error(f"Video file too small: {file_size} bytes")
                        os.remove(downloaded_file)
                        return None, False
                    elif not video and file_size < 1024:  # Audio: at least 1KB
                        logger.error(f"Audio file too small: {file_size} bytes")
                        os.remove(downloaded_file)
                        return None, False
                    
                    logger.info(f"File validated: {downloaded_file}, Size: {file_size} bytes")
                    return downloaded_file, True
                else:
                    logger.error(f"Downloaded file not found: {downloaded_file}")
                    return None, False
            else:
                return None, False
                
        except Exception as e:
            logger = LOGGER("ShrutiMusic.platforms.Youtube.py")
            logger.error(f"Download error in YouTubeAPI.download: {e}")
            return None, False
