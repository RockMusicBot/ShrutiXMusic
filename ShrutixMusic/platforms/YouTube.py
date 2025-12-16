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
# NOTE: Ensure this external utility is available in your project structure
from ShrutiMusic.utils.formatters import time_to_seconds 

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

# 2. xBit Music API (Primary 2)
YTPROXY_URL = "https://tgapi.xbitcode.com" ## xBit Music Endpoint
YT_API_KEY = "xbit_vXeUavHk2nhb12AGpMwKhbrEHoaMrJam"

# 3. TheQuickEarn/AviaxMusic API (Fallback 1)
THEQUICKEARN_API_URL = "https://api.thequickearn.xyz"
THEQUICKEARN_API_KEY = "30DxNexGenBots62dba1"

# --- API URL Initialization (Shrutibots) ---

async def load_shruti_api_url():
    """Loads the dynamic Shrutibots API URL from Pastebin."""
    global SHRUTI_API_URL
    if SHRUTI_API_URL:
        return

    pastebin_ids = ["rLsBhAQa", "FwwmTRED", "nfsHqXH2"]
    
    try:
        async with aiohttp.ClientSession() as session:
            for pb_id in pastebin_ids:
                try:
                    async with session.get(f"https://pastebin.com/raw/{pb_id}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            content = await response.text()
                            url = content.strip()
                            if url:
                                SHRUTI_API_URL = url
                                logger.info(f"Shruti API URL loaded successfully from {pb_id}")
                                return
                        
                except Exception:
                    continue # Try the next one

        SHRUTI_API_URL = FALLBACK_API_URL
        logger.info("Using fallback Shruti API URL")
    except Exception:
        SHRUTI_API_URL = FALLBACK_API_URL
        logger.info("Using fallback Shruti API URL due to network error.")

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
        error_msg = errorz.decode("utf-8")
        if "unavailable videos are hidden" in error_msg.lower():
            return out.decode("utf-8")
        else:
            return error_msg
    return out.decode("utf-8")


# ---------------------------------------------------------------------------------
#                          INDIVIDUAL API DOWNLOADERS
# ---------------------------------------------------------------------------------

# --- Primary API 1: Shrutibots (Token-based streaming) ---
async def shruti_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using Shrutibots API."""
    await load_shruti_api_url()
    global SHRUTI_API_URL
    if not SHRUTI_API_URL: return None
    
    file_type = "video" if is_video else "audio"
    extension = "mp4" if is_video else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    logger.info(f"{log_prefix} [Shruti] Attempting download for ID: {video_id}")

    # Local cache check (handled by manager, but good for quick exit)
    if os.path.exists(file_path):
         return file_path
             
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Get download token
            params = {"url": video_id, "type": file_type}
            async with session.get(f"{SHRUTI_API_URL}/download", params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200: 
                    logger.error(f"{log_prefix} [Shruti] Token fetch failed with status {response.status}")
                    return None
                
                data = await response.json()
                
                # *** FIX 1: Ensure we check status and extract token correctly (Addresses your log error) ***
                if data.get("status") != "success":
                    # If status is not 'success', it's an API error message
                    logger.error(f"{log_prefix} [Shruti] API reported error: {data.get('message', 'Unknown API Error')}")
                    return None
                    
                download_token = data.get("download_token")
                if not download_token: 
                    logger.error(f"{log_prefix} [Shruti] Missing download token.")
                    return None
                
                logger.info(f"{log_prefix} [Shruti] Token received. Starting stream.")
                
            # 2. Stream the file
            stream_url = f"{SHRUTI_API_URL}/stream/{video_id}?type={file_type}"
            async with session.get(
                stream_url, 
                # Use the token in the specified header
                headers={"X-Download-Token": download_token}, 
                timeout=aiohttp.ClientTimeout(total=600 if is_video else 300)
            ) as file_response:
                if file_response.status != 200: 
                    logger.error(f"{log_prefix} [Shruti] Stream failed with status {file_response.status} or invalid token.")
                    return None
                    
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(16384):
                        f.write(chunk)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    logger.info(f"{log_prefix} [Shruti] Download completed successfully.")
                    return file_path
                else:
                    logger.error(f"{log_prefix} [Shruti] Downloaded file is empty.")
                    if os.path.exists(file_path): os.remove(file_path)
                    return None
                    
    except Exception as e:
        logger.error(f"{log_prefix} [Shruti] Exception for ID: {video_id} - {e}")
        if os.path.exists(file_path): os.remove(file_path)
        return None

# --- Primary API 2: xBit Music (Proxy-based) ---
async def xbit_api_download(video_id: str, is_video: bool) -> Optional[str]:
    """Downloads file using xBit Music API."""
    
    file_type = "video" if is_video else "audio"
    extension = "mp4" if is_video else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")
    log_prefix = "🎥" if is_video else "🎵"

    if not YT_API_KEY or not YTPROXY_URL:
        logger.warning(f"{log_prefix} [xBit] API Key or URL not set.")
        return None

    logger.info(f"{log_prefix} [xBit] Attempting download for ID: {video_id}")
    
    # Local cache check
    if os.path.exists(file_path):
         return file_path

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"x-api-key": YT_API_KEY}
            
            # 1. Get info/download link
            async with session.get(f"{YTPROXY_URL}/info/{video_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"{log_prefix} [xBit] Info fetch failed with status {response.status}")
                    return None
                    
                data = await response.json()
                
                if data.get("status") != "success":
                    logger.error(f"{log_prefix} [xBit] API error: {data.get('message', 'Unknown error')}")
                    return None
                
                # *** FIX 2: Ensure correct key is extracted from the response ***
                key = "video_url" if is_video else "audio_url"
                download_url = data.get(key)
                
                if not download_url:
                    logger.error(f"{log_prefix} [xBit] Missing download URL ({key}) in response.")
                    return None
            
            # 2. Stream the file
            async with session.get(download_url, headers=headers, timeout=aiohttp.ClientTimeout(total=600 if is_video else 300)) as file_response:
                if file_response.status != 200:
                    logger.error(f"{log_prefix} [xBit] Final stream failed with status {file_response.status}")
                    return None
                        
                with open(file_path, "wb") as f:
                    async for chunk in file_response.content.iter_chunked(16384):
                        f.write(chunk)

                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    logger.info(f"{log_prefix} [xBit] Download completed successfully.")
                    return file_path
                else:
                    logger.error(f"{log_prefix} [xBit] Downloaded file is empty.")
                    if os.path.exists(file_path): os.remove(file_path)
                    return None

    except Exception as e:
        logger.error(f"{log_prefix} [xBit] Exception for ID: {video_id} - {e}")
        if os.path.exists(file_path): os.remove(file_path)
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
    
    # Using the final file path for cleanup check, assuming we know the ID
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{'mp4' if is_video else 'mp3'}") 

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Poll API for download link
            for attempt in range(3): 
                try:
                    async with session.get(url_to_poll, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status != 200: raise Exception(f"API request failed with status code {response.status}")
                    
                        data = await response.json(content_type=None) 
                        status = data.get("status", "").lower()

                        if status == "done":
                            download_url = data.get("link")
                            file_extension = data.get("format", "mp4" if is_video else "mp3").lower()
                            if not download_url: raise Exception("No download URL.")
                            break
                        elif status == "downloading":
                            logger.info(f"{log_prefix} [QuickEarn] Polling attempt {attempt+1}: File still downloading on server.")
                            await asyncio.sleep(8)
                        else:
                            error_msg = data.get("error") or data.get("message") or f"Unexpected status '{status}'"
                            raise Exception(f"API error: {error_msg}")
                except Exception as e:
                    logger.error(f"{log_prefix} [QuickEarn] Polling attempt {attempt+1} failed: {e}")
                    if attempt == 2: return None 
            else:
                return None
        
            # 2. Download the ready file
            file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{file_extension}")
            async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=600)) as file_response:
                if file_response.status != 200: 
                    logger.error(f"{log_prefix} [QuickEarn] Final stream failed with status {file_response.status}")
                    return None
                
                with open(file_path, 'wb') as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        f.write(chunk)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                logger.info(f"{log_prefix} [QuickEarn] Download completed successfully.")
                return file_path
            else:
                logger.error(f"{log_prefix} [QuickEarn] Downloaded file is empty.")
                if os.path.exists(file_path): os.remove(file_path)
                return None
                
    except Exception as e:
        logger.error(f"{log_prefix} [QuickEarn] Overall Exception for ID: {video_id} - {e}")
        if os.path.exists(file_path): os.remove(file_path)
        return None


# --- Final Failsafe: yt-dlp Direct Download (Slow/Reliable) ---
def yt_dlp_sync_download(link: str, is_video: bool) -> Optional[str]:
    """Synchronous function for yt-dlp download (to be run in executor)."""
    
    log_prefix = "🎥" if is_video else "🎵"
    cookie_file = cookie_txt_file()
    
    # Clean up any potential failed files before starting
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if video_id:
        for ext in ["mp3", "m4a", "webm", "mp4"]:
            temp_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
            if os.path.exists(temp_path):
                 os.remove(temp_path)
        
    try:
        ydl_optssx = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "geo_bypass": True, "nocheckcertificate": True, "quiet": True,
            "no_warnings": True,
        }
        
        if cookie_file:
            ydl_optssx["cookiefile"] = cookie_file
            
        if is_video:
            # High quality video up to 720p with best audio
            ydl_optssx["format"] = "(bestvideo[height<=?720][ext=mp4])+(bestaudio[ext=m4a])"
            ydl_optssx["merge_output_format"] = "mp4"
            target_ext = "mp4"
        else:
            # Best audio quality, converted to mp3
            ydl_optssx["format"] = "bestaudio/best"
            ydl_optssx["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]
            target_ext = "mp3"
        
        logger.info(f"{log_prefix} [YTDLP] Starting final failsafe download...")
        x = yt_dlp.YoutubeDL(ydl_optssx)
        info = x.extract_info(link, download=True)
        
        # Get the actual file path after download and processing
        # This glob is the most reliable way to find the final file name
        downloaded_file = glob.glob(os.path.join(DOWNLOAD_DIR, f"{info['id']}.*"))
        
        if downloaded_file:
             xyz = downloaded_file[0]
        else:
             # Fallback guess based on expected target extension
             xyz = os.path.join(DOWNLOAD_DIR, f"{info['id']}.{target_ext}")
        
        if os.path.exists(xyz) and os.path.getsize(xyz) > 0:
            logger.info(f"{log_prefix} [YTDLP] Download completed successfully: {xyz}")
            return xyz
        else:
            logger.error(f"{log_prefix} [YTDLP] Downloaded file is empty or missing.")
            # *** FIX 3: Ensure returning None if file is not found, which prevents FileNotFoundError upstream ***
            if os.path.exists(xyz): os.remove(xyz)
            return None
            
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
    Phase 1: Primary APIs (Shrutibots, xBit Music) in parallel.
    Phase 2: Fallback APIs (QuickEarn, YTDLP) in parallel.
    """
    # Use a robust way to get the video ID
    match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|&v=)([^&]+)', link)
    if match:
        video_id = match.group(1)
    else:
        video_id = link
    
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
            
    # 2. Phase 1: Primary Parallel Stage (Shrutibots & xBit)
    logger.info(f"[Manager] Starting Phase 1 (Primary: Shruti, xBit) for {video_id}")
    
    
    primary_tasks = [
        asyncio.create_task(shruti_api_download(video_id, is_video), name="P1_Shruti"),
        asyncio.create_task(xbit_api_download(video_id, is_video), name="P1_xBit"),
    ]

    done, pending = await asyncio.wait(
        primary_tasks,
        return_when=asyncio.FIRST_COMPLETED,
        timeout=60 # Wait max 60 seconds for primary API response
    )

    # Check for success in completed primary tasks
    for task in done:
        if task.exception() is None:
            result = task.result()
            if result:
                logger.info(f"[Manager] Phase 1 success from {task.get_name()}.")
                for p in pending: p.cancel()
                return result, True
            
    # Wait for remaining primary tasks to finish if the first one failed quickly
    if pending:
        logger.info("[Manager] Phase 1 waiting for remaining primary tasks.")
        done_remaining, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
        for task in done_remaining:
            if task.exception() is None:
                result = task.result()
                if result:
                    logger.info(f"[Manager] Phase 1 success from {task.get_name()} (late).")
                    return result, True

    logger.warning(f"[Manager] Phase 1 failed for {video_id}. Moving to Phase 2.")
    
    # 3. Phase 2: Fallback Parallel Stage (QuickEarn & yt-dlp)
    logger.info(f"[Manager] Starting Phase 2 (Fallback: QuickEarn, YTDLP) for {video_id}")
    
    fallback_tasks = [
        asyncio.create_task(quickearn_api_download(video_id, is_video), name="P2_QuickEarn"),
        asyncio.create_task(yt_dlp_fallback_download(link, is_video), name="P2_YTDLP"), 
    ]

    done, pending = await asyncio.wait(
        fallback_tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Check for success in completed fallback tasks
    for task in done:
        if task.exception() is None:
            result = task.result()
            if result:
                logger.info(f"[Manager] Phase 2 success from {task.get_name()}.")
                for p in pending: p.cancel()
                return result, True
            
    # Wait for the remaining fallback task
    if pending:
        logger.info("[Manager] Phase 2 waiting for remaining fallback tasks.")
        done_remaining, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
        for task in done_remaining:
            if task.exception() is None:
                result = task.result()
                if result:
                    logger.info(f"[Manager] Phase 2 success from {task.get_name()} (late).")
                    return result, True

    # 4. Final Failsafe Log (All attempts exhausted)
    logger.error(f"[Manager] All download attempts failed for {video_id}")
    # *** FIX 4: Explicitly return None, False when all attempts fail. ***
    return None, False

# ---------------------------------------------------------------------------------
#                            YOUTUBE API CLASS (Remains safe and standard)
# ---------------------------------------------------------------------------------

class YouTubeAPI:
    # ... (Most methods remain unchanged, rely on download_manager) ...
    # Placeholder for the unchanged class structure for completeness
    
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
        
        # Using shell_cmd with cookie_file (from yt-dlp fallback logic)
        cookie_file = cookie_txt_file()
        cookie_arg = f"--cookies {cookie_file}" if cookie_file else ""
            
        playlist_cmd = f"yt-dlp -i --get-id --flat-playlist {cookie_arg} --playlist-end {limit} --skip-download {link}"
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
        cookie_arg = {"cookiefile" : cookie_file} if cookie_file else {}
            
        ytdl_opts = {"quiet": True, **cookie_arg}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        
        formats_available = []
        try:
            with ydl:
                r = ydl.extract_info(link, download=False)
                for format in r.get("formats", []):
                    # Filter out DASH formats for simpler streaming if possible
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
        
