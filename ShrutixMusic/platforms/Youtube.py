import asyncio
import os
import re
import json
import logging
import random
import glob
from typing import Union, Optional, Tuple, Any
import yt_dlp
import aiohttp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch
# NOTE: Ensure these external utilities are available in your project structure
from ShrutixMusic.utils.formatters import time_to_seconds 

# ---------------------------------------------------------------------------------
#                            UTILITY & CONFIGURATION
# ---------------------------------------------------------------------------------

# --- Custom Logger Setup (Adapt this if your LOGGER implementation is different) ---
def LOGGER(name):
    # Basic configuration for demonstration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(name)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
logger = LOGGER("ShrutixMusic.platforms.Youtube")

# 1. Shrutibots/ShrutiMusic API (Primary 1)
FALLBACK_API_URL = "https://shrutibots.site"
SHRUTI_API_URL: Optional[str] = None 

# 2. Inflex API (Primary 2)
INFLEX_API_URL = "https://teaminflex.xyz"
# !!! REPLACE THIS WITH YOUR ACTUAL INFLEX API KEY !!!
INFLEX_API_KEY = "INFLEX66417728D" 

# 3. xBit Music API (New Primary 3)
YTPROXY_URL = "https://tgapi.xbitcode.com" ## xBit Music Endpoint
YT_API_KEY = "xbit_vXeUavHk2nhb12AGpMwKhbrEHoaMrJam"

# 4. TheQuickEarn/AviaxMusic API (Fallback 1)
THEQUICKEARN_API_URL = "https://api.thequickearn.xyz"
THEQUICKEARN_API_KEY = "30DxNexGenBots62dba1"

# 5. Fallen API (Fallback 2)
FALLEN_API_URL = "https://tgmusic.fallenapi.fun"
FALLEN_API_KEY = "1627ff_iQZYYZxE5tpMrXDMAT9JfikIzWxLS7dq"


# --- API URL Initialization (Shrutibots) ---

async def load_shruti_api_url():
    """Loads the dynamic Shrutibots API URL from Pastebin."""
    global SHRUTI_API_URL
    if SHRUTI_API_URL:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    SHRUTI_API_URL = content.strip()
                    logger.info("Shruti API URL loaded successfully")
                else:
                    SHRUTI_API_URL = FALLBACK_API_URL
                    logger.info("Using fallback Shruti API URL")
    except Exception:
        SHRUTI_API_URL = FALLBACK_API_URL
        logger.info("Using fallback Shruti API URL")

# Run API loading on import
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_shruti_api_url())
    else:
        loop.run_until_complete(load_shruti_api_url())
except RuntimeError:
    pass

# --- Cookie Utility (For yt-dlp fallback) ---

def cookie_txt_file():
    """Finds a random cookie file for yt-dlp authentication."""
    cookie_dir = f"{os.getcwd()}/cookies"
    if not os.path.exists(cookie_dir):
        return None
    cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
    if not cookies_files:
        return None
    cookie_file = os.path.join(cookie_dir, random.choice(cookies_files))
    return cookie_file

# --- Shell Command Utility (For playlist) ---

async def shell_cmd(cmd):
    """Executes a shell command asynchronously (used for yt-dlp calls)."""
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


# ---------------------------------------------------------------------------------
#                          INDIVIDUAL API DOWNLOADERS
# ---------------------------------------------------------------------------------

# --- Primary API 1: Shrutibots ---
async def shruti_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using Shrutibots API (Token-based streaming)."""
    await load_shruti_api_url()
    if not SHRUTI_API_URL: return None
    
    file_type = "video" if is_video else "audio"
    extension = "mp4" if is_video else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    logger.info(f"{log_prefix} [Shruti] Attempting download for ID: {video_id}")

    try:
        # Check local cache for the expected extension before starting the long download
        if os.path.exists(file_path):
             logger.info(f"{log_prefix} [Shruti] Found existing file during API check.")
             return file_path
             
        async with aiohttp.ClientSession() as session:
            # 1. Get download token
            params = {"url": video_id, "type": file_type}
            async with session.get(f"{SHRUTI_API_URL}/download", params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200: return None
                data = await response.json()
                download_token = data.get("download_token")
                if not download_token: return None
                
            # 2. Stream the file
            stream_url = f"{SHRUTI_API_URL}/stream/{video_id}?type={file_type}"
            async with session.get(
                stream_url, headers={"X-Download-Token": download_token},
                timeout=aiohttp.ClientTimeout(total=600 if is_video else 300)
            ) as file_response:
                if file_response.status != 200: return None
                    
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(16384):
                        f.write(chunk)
                
                logger.info(f"{log_prefix} [Shruti] Download completed successfully.")
                return file_path
    except Exception as e:
        logger.error(f"{log_prefix} [Shruti] Exception for ID: {video_id} - {e}")
        return None

# --- Primary API 2: Inflex ---
async def inflex_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using Inflex API (POST to trigger, GET the link)."""
    
    file_type = "video" if is_video else "audio"
    extension = "mkv" if is_video else "webm"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    if INFLEX_API_KEY == "YOUR_INFLEX_API_KEY_HERE": 
        logger.warning(f"{log_prefix} [Inflex] API Key not set.")
        return None

    logger.info(f"{log_prefix} [Inflex] Attempting download for ID: {video_id}")
    
    # Check local cache for the expected extension
    if os.path.exists(file_path):
         logger.info(f"{log_prefix} [Inflex] Found existing file during API check.")
         return file_path

    try:
        async with aiohttp.ClientSession() as session:
            payload = {"url": video_id, "type": file_type}
            headers = {"Content-Type": "application/json", "X-API-KEY": INFLEX_API_KEY}

            # 1. Trigger API and get download link
            async with session.post(f"{INFLEX_API_URL}/download", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                data = await response.json(content_type=None)

                if response.status != 200 or data.get("status") != "success" or not data.get("download_url"):
                    detail = data.get("detail", data.get("error", "Unknown error"))
                    logger.error(f"{log_prefix} [Inflex] API failed: {detail}")
                    return None

                download_link = f"{INFLEX_API_URL}{data['download_url']}"

            # 2. Download the ready file
            async with session.get(download_link, timeout=aiohttp.ClientTimeout(total=600)) as file_response:
                if file_response.status != 200: return None
                
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        f.write(chunk)

        logger.info(f"{log_prefix} [Inflex] Download completed successfully.")
        return file_path

    except Exception as e:
        logger.error(f"{log_prefix} [Inflex] Exception for ID: {video_id} - {e}")
        return None

# --- Primary API 3: xBit Music ---
async def xbit_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using xBit Music API (Proxy-based)."""
    
    file_type = "video" if is_video else "audio"
    extension = "mp4" if is_video else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    if not YT_API_KEY or not YTPROXY_URL:
        logger.warning(f"{log_prefix} [xBit] API Key or URL not set.")
        return None

    logger.info(f"{log_prefix} [xBit] Attempting download for ID: {video_id}")
    
    if os.path.exists(file_path):
         logger.info(f"{log_prefix} [xBit] Found existing file during API check.")
         return file_path

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"x-api-key": YT_API_KEY}
            endpoint = "video" if is_video else "audio"
            
            # 1. Get info/download link
            async with session.get(f"{YTPROXY_URL}/info/{video_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"{log_prefix} [xBit] Info fetch failed with status {response.status}")
                    return None
                    
                data = await response.json()
                
                if data.get("status") != "success":
                    logger.error(f"{log_prefix} [xBit] API error: {data.get('message', 'Unknown error')}")
                    return None
                
                # Check for video_url or audio_url based on request type
                download_url = data.get(f"{endpoint}_url") 
                if not download_url:
                    logger.error(f"{log_prefix} [xBit] Missing download URL in response.")
                    return None
            
            # 2. Stream the file
            # Re-using headers for download stream if authentication is required
            async with session.get(download_url, headers=headers, timeout=aiohttp.ClientTimeout(total=600 if is_video else 300)) as file_response:
                if file_response.status != 200:
                    logger.error(f"{log_prefix} [xBit] Final stream failed with status {file_response.status}")
                    return None
                        
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(16384):
                        f.write(chunk)
                
                logger.info(f"{log_prefix} [xBit] Download completed successfully.")
                return file_path

    except Exception as e:
        logger.error(f"{log_prefix} [xBit] Exception for ID: {video_id} - {e}")
        return None

# --- Fallback API 1 (Parallel): TheQuickEarn ---
async def quickearn_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using TheQuickEarn API (Polling-based)."""
    
    file_type = "video" if is_video else "song"
    log_prefix = "🎥" if is_video else "🎵"

    logger.info(f"{log_prefix} [QuickEarn] Attempting download for ID: {video_id}")

    download_url = None
    file_extension = None
    endpoint = "video" if is_video else "song"
    url_to_poll = f"{THEQUICKEARN_API_URL}/{endpoint}/{video_id}?api={THEQUICKEARN_API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Poll API for download link
        # Polling attempts reduced to 3
        for attempt in range(3): 
            try:
                async with session.get(url_to_poll, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200: raise Exception(f"API request failed with status code {response.status}")
                
                    data = await response.json()
                    status = data.get("status", "").lower()

                    if status == "done":
                        download_url = data.get("link")
                        file_extension = data.get("format", "mp4" if is_video else "mp3").lower()
                        if not download_url: raise Exception("No download URL.")
                        break
                    elif status == "downloading":
                        await asyncio.sleep(8)
                    else:
                        error_msg = data.get("error") or data.get("message") or f"Unexpected status '{status}'"
                        raise Exception(f"API error: {error_msg}")
            except Exception as e:
                logger.error(f"{log_prefix} [QuickEarn] Polling attempt {attempt+1} failed: {e}")
                if attempt == 2: return None # Fail after 3rd attempt
        else:
            return None
    
        # 2. Download the ready file
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{file_extension}")
        try:
            async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=600)) as file_response:
                if file_response.status != 200: return None
                
                with open(file_path, 'wb') as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        f.write(chunk)
                
                logger.info(f"{log_prefix} [QuickEarn] Download completed successfully.")
                return file_path
        except Exception as e:
            logger.error(f"{log_prefix} [QuickEarn] Final download error: {e}")
            return None

# --- Fallback API 2 (Parallel): Fallen API ---
async def fallen_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using Fallen API (Two-step fetch and stream)."""
    
    file_type = "video" if is_video else "audio"
    extension = "mp4" if is_video else "mp3" 
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    logger.info(f"{log_prefix} [Fallen] Attempting download for ID: {video_id}")
    
    link_fetch_url = f"{FALLEN_API_URL}/track" # Endpoint as per your usage

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Fetch download link/details
            params = {"api_key": FALLEN_API_KEY, "url": video_id}
            
            async with session.get(link_fetch_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"{log_prefix} [Fallen] Link fetch failed with status {response.status}")
                    return None
                    
                data = await response.json()
                
                # FIX: Check for download_link, link, OR cdnurl (to support direct CDN streams)
                download_link = data.get("download_link") or data.get("link") or data.get("cdnurl")
                
                if not download_link:
                    logger.error(f"{log_prefix} [Fallen] Response missing download link. Data: {data}")
                    return None
                    
            # 2. Stream the file
            async with session.get(download_link, timeout=aiohttp.ClientTimeout(total=600)) as file_response:
                if file_response.status != 200:
                    logger.error(f"{log_prefix} [Fallen] Final stream failed with status {file_response.status}")
                    return None
                        
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(16384):
                        f.write(chunk)
                
                logger.info(f"{log_prefix} [Fallen] Download completed successfully.")
                return file_path

        except Exception as e:
            logger.error(f"{log_prefix} [Fallen] Exception for ID: {video_id} - {e}")
            return None

# --- Final Failsafe: yt-dlp Direct Download (Slow/Reliable) ---
def yt_dlp_sync_download(link: str, is_video: bool) -> Optional[str]:
    """Synchronous function for yt-dlp download (to be run in executor)."""
    
    log_prefix = "🎥" if is_video else "🎵"
    cookie_file = cookie_txt_file()
    if not cookie_file: 
        logger.error(f"{log_prefix} [YTDLP] No cookies found. Cannot proceed.")
        return None
        
    try:
        ydl_optssx = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "geo_bypass": True, "nocheckcertificate": True, "quiet": True,
            "cookiefile" : cookie_file, "no_warnings": True,
        }
        
        if is_video:
            ydl_optssx["format"] = "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])"
            ydl_optssx["merge_output_format"] = "mp4"
        else:
            ydl_optssx["format"] = "bestaudio/best"
            ydl_optssx["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]
        
        logger.info(f"{log_prefix} [YTDLP] Starting final failsafe download...")
        x = yt_dlp.YoutubeDL(ydl_optssx)
        info = x.extract_info(link, download=True)
        
        # Get the actual file path after download and processing
        downloaded_file = glob.glob(os.path.join(DOWNLOAD_DIR, f"{info['id']}.*"))
        if downloaded_file:
             xyz = downloaded_file[0]
        else:
             xyz = os.path.join(DOWNLOAD_DIR, f"{info['id']}.{info.get('ext', 'mp3')}")
        
        logger.info(f"{log_prefix} [YTDLP] Download completed successfully.")
        return xyz
    except Exception as e:
        logger.error(f"{log_prefix} [YTDLP] Exception: {e}")
        return None

async def yt_dlp_fallback_download(link: str, is_video: bool) -> Optional[str]:
    """Async wrapper for the synchronous yt-dlp function."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, yt_dlp_sync_download, link, is_video
    )

# ---------------------------------------------------------------------------------
#                            MASTER DOWNLOAD MANAGER
# ---------------------------------------------------------------------------------

async def download_manager(link: str, is_video: bool) -> Tuple[Optional[str], bool]:
    """
    Manages the prioritized, multi-API parallel download process.
    Returns: (file_path, is_direct) -> is_direct is always True if file is local
    """
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link

    if not video_id or len(video_id) < 3:
        logger.error("[Manager] Invalid video ID.")
        return None, False

    # 1. Local File Check (Preserve saved downloads)
    extensions = ["mp3", "m4a", "webm", "mp4", "mkv"]
    for ext in extensions:
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(file_path):
            logger.info(f"[Manager] Found existing file in local cache: {file_path}")
            return file_path, True
            
    # 2. Primary Parallel Stage (Shrutibots, Inflex & xBit)
    logger.info(f"[Manager] Starting Primary Parallel download (Shruti, Inflex, xBit) for {video_id}")
    
    task_shruti = asyncio.create_task(shruti_api_download(video_id, is_video))
    task_inflex = asyncio.create_task(inflex_api_download(video_id, is_video))
    task_xbit = asyncio.create_task(xbit_api_download(video_id, is_video)) # New Primary Task
    
    primary_tasks = [task_shruti, task_inflex, task_xbit]

    done, pending = await asyncio.wait(
        primary_tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Check for success in completed primary tasks
    for task in done:
        result = task.result()
        if result:
            logger.info(f"[Manager] Primary download successful from one source.")
            for p in pending: p.cancel()
            return result, True
            
    # Wait for the remaining primary task if not successful yet
    if pending:
        logger.info("[Manager] Primary wait: Remaining task might complete now.")
        done_remaining, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
        for task in done_remaining:
            result = task.result()
            if result:
                return result, True

    # 3. Fallback Parallel Stage (QuickEarn, Fallen & yt-dlp)
    logger.info(f"[Manager] Primary failed. Starting Fallback Parallel download (QuickEarn, Fallen, YTDLP) for {video_id}")
    
    task_quickearn = asyncio.create_task(quickearn_api_download(video_id, is_video))
    task_fallen = asyncio.create_task(fallen_api_download(video_id, is_video))
    # YTDLP added here for ultimate reliability and speed in fallback
    task_ytdlp = asyncio.create_task(yt_dlp_fallback_download(link, is_video)) 
    
    fallback_tasks = [task_quickearn, task_fallen, task_ytdlp]

    done, pending = await asyncio.wait(
        fallback_tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Check for success in completed fallback tasks
    for task in done:
        result = task.result()
        if result:
            logger.info(f"[Manager] Fallback download successful from one source.")
            for p in pending: p.cancel()
            return result, True
            
    # Wait for the remaining fallback task
    if pending:
        logger.info("[Manager] Fallback wait: Remaining task might complete now.")
        done_remaining, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
        for task in done_remaining:
            result = task.result()
            if result:
                return result, True

    # 4. Final Failsafe Log (All attempts exhausted)
    logger.error(f"[Manager] All download attempts failed for {video_id}")
    return None, False

# ---------------------------------------------------------------------------------
#                            YOUTUBE API CLASS
# ---------------------------------------------------------------------------------
# (This class uses the download_manager and remains largely the same)

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
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

    async def details(self, link: str, videoid: Union[bool, str] = None) -> Tuple[str, str, int, str, str]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        result = (await results.next())["result"][0]
        
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

    async def video(self, link: str, videoid: Union[bool, str] = None) -> Tuple[int, str]:
        """Downloads the video and returns status code (1=success) and file path/error."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        # Delegates to the updated download_manager
        file_path, success = await download_manager(link, is_video=True)
        
        if success:
            return 1, file_path
        else:
            return 0, "Video download failed via all available methods."

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None) -> list:
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        cookie_file = cookie_txt_file()
        if not cookie_file: return []
            
        playlist_cmd = f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_file} --playlist-end {limit} --skip-download {link}"
        playlist = await shell_cmd(playlist_cmd)
        
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
            "title": title, "link": yturl, "vidid": vidid, 
            "duration_min": duration_min, "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None) -> Tuple[list, str]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        cookie_file = cookie_txt_file()
        if not cookie_file: return [], link
            
        ytdl_opts = {"quiet": True, "cookiefile" : cookie_file}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        
        formats_available = []
        try:
            with ydl:
                r = ydl.extract_info(link, download=False)
                for format in r.get("formats", []):
                    if "dash" not in str(format.get("format")).lower():
                        formats_available.append({
                            "format": format.get("format"), "filesize": format.get("filesize"), 
                            "format_id": format.get("format_id"), "ext": format.get("ext"), 
                            "format_note": format.get("format_note"), "yturl": link,
                        })
        except Exception as e:
            logger.error(f"[Formats] Error fetching formats: {e}")

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
        mystic: Any,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> Tuple[Optional[str], bool]:
        """
        Master download method that delegates to the download_manager.
        It handles both audio and video requests based on parameters.
        """
        if videoid:
            link = self.base + link

        # Determine if the user requested a video or just audio
        is_video = bool(video or songvideo)
        
        # The download_manager handles all prioritized logic
        return await download_manager(link, is_video=is_video)
    
