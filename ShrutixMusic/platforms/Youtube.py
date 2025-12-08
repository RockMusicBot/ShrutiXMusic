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

# --- API Configuration ---

# Primary API (ShrutixMusic)
YOUR_API_URL = None
FALLBACK_API_URL_PRIMARY = "https://shrutibots.site"

# Secondary/Fallback API (TheQuickEarn.xyz - user's second choice)
FALLBACK_API_URL_SECONDARY = "https://api.thequickearn.xyz"
FALLBACK_API_KEY_SECONDARY = "30DxNexGenBots62dba1"

# --- Logger Setup ---
logger = LOGGER(__name__)

# --- Primary API URL Loader ---

async def load_api_url():
    """Loads the primary API URL from a pastebin link."""
    global YOUR_API_URL
    if YOUR_API_URL:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    YOUR_API_URL = content.strip()
                    logger.info("Primary API URL loaded successfully")
                else:
                    YOUR_API_URL = FALLBACK_API_URL_PRIMARY
                    logger.info("Using primary fallback API URL (status error)")
    except Exception:
        YOUR_API_URL = FALLBACK_API_URL_PRIMARY
        logger.info("Using primary fallback API URL (connection error)")

try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_api_url())
    else:
        loop.run_until_complete(load_api_url())
except RuntimeError:
    pass

# --- Primary Song Download Logic (ShrutixMusic API) ---

async def _download_song_primary(link: str) -> str:
    """Attempts to download an audio file using the primary ShrutixMusic API."""
    global YOUR_API_URL
    
    if not YOUR_API_URL:
        await load_api_url()
        
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link

    if not video_id or len(video_id) < 3:
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

    if os.path.exists(file_path):
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": "audio"}
            
            # Step 1: Get the stream URL
            async with session.get(
                f"{YOUR_API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Primary API responded with status {response.status}")

                data = await response.json()
                stream_url = data.get("stream_url")
                
                if not stream_url:
                    raise Exception("Primary API did not provide a stream URL")
                
                # Step 2: Download the file
                async with session.get(
                    stream_url,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as file_response:
                    if file_response.status != 200:
                        raise Exception(f"Primary API file download status {file_response.status}")
                        
                    with open(file_path, "wb") as f:
                        async for chunk in file_response.content.iter_chunked(16384):
                            f.write(chunk)
                    
                    return file_path

    except Exception as e:
        logger.warning(f"Primary API download failed for {link}: {e}")
        return None

# --- Secondary Song Download Logic (TheQuickEarn API) ---

async def _download_song_secondary(link: str) -> str:
    """Attempts to download an audio file using the secondary TheQuickEarn API."""
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if not video_id or len(video_id) < 3:
        return None

    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)
    
    song_url = f"{FALLBACK_API_URL_SECONDARY}/song/{video_id}?api={FALLBACK_API_KEY_SECONDARY}"
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(song_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        raise Exception(f"API request failed with status code {response.status}")
                
                    data = await response.json()
                    status = data.get("status", "").lower()

                    if status == "done":
                        download_url = data.get("link")
                        if not download_url:
                            raise Exception("API response did not provide a download URL.")
                        break
                    elif status == "downloading":
                        await asyncio.sleep(4)
                    else:
                        error_msg = data.get("error") or data.get("message") or f"Unexpected status '{status}'"
                        raise Exception(f"API error: {error_msg}")
            except Exception as e:
                logger.warning(f"[FAIL] Secondary API attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2)
        else:
            logger.error("Max retries reached on secondary song API.")
            return None

        try:
            file_format = data.get("format", "mp3")
            file_extension = file_format.lower()
            file_name = f"{video_id}.{file_extension}"
            file_path = os.path.join(download_folder, file_name)

            async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=300)) as file_response:
                with open(file_path, 'wb') as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        f.write(chunk)
                return file_path
        except Exception as e:
            logger.error(f"Error occurred while downloading song from secondary API: {e}")
            return None

# --- Unified Song Download Function with Fallback ---

async def download_song(link: str) -> str:
    """
    Attempts to download an audio file, first via primary API, then via secondary fallback API.
    """
    logger.info(f"Attempting song download with primary API for: {link}")
    # 1. Primary API (ShrutixMusic)
    downloaded_file = await _download_song_primary(link)
    
    if downloaded_file:
        logger.info(f"Song downloaded successfully via primary API: {downloaded_file}")
        return downloaded_file
    
    logger.warning("Primary song API failed. Falling back to secondary API.")
    # 2. Secondary API (TheQuickEarn)
    downloaded_file = await _download_song_secondary(link)
    
    if downloaded_file:
        logger.info(f"Song downloaded successfully via secondary API: {downloaded_file}")
        return downloaded_file
        
    logger.error("Both song APIs failed.")
    return None


# --- Video Download Logic (Updated with Fallback for completeness) ---

async def _download_video_secondary(link: str) -> str:
    """Attempts to download a video file using the secondary TheQuickEarn API."""
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if not video_id or len(video_id) < 3:
        return None

    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)
        
    video_url = f"{FALLBACK_API_URL_SECONDARY}/video/{video_id}?api={FALLBACK_API_KEY_SECONDARY}"
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(video_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        raise Exception(f"API request failed with status code {response.status}")
                
                    data = await response.json()
                    status = data.get("status", "").lower()

                    if status == "done":
                        download_url = data.get("link")
                        if not download_url:
                            raise Exception("API response did not provide a download URL.")
                        break
                    elif status == "downloading":
                        await asyncio.sleep(8)
                    else:
                        error_msg = data.get("error") or data.get("message") or f"Unexpected status '{status}'"
                        raise Exception(f"API error: {error_msg}")
            except Exception as e:
                logger.warning(f"[FAIL] Secondary Video API attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2)
        else:
            return None

        try:
            file_format = data.get("format", "mp4")
            file_extension = file_format.lower()
            file_name = f"{video_id}.{file_extension}"
            file_path = os.path.join(download_folder, file_name)

            async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=600)) as file_response:
                with open(file_path, 'wb') as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        f.write(chunk)
                return file_path
        except Exception as e:
            logger.error(f"Error occurred while downloading video from secondary API: {e}")
            return None


async def download_video(link: str) -> str:
    """
    Attempts to download a video file, first via primary API, then via secondary fallback API.
    """
    global YOUR_API_URL
    
    if not YOUR_API_URL:
        await load_api_url()
        
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if not video_id or len(video_id) < 3:
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")

    if os.path.exists(file_path):
        return file_path
    
    logger.info(f"Attempting video download with primary API for: {link}")
    # 1. Primary API (ShrutixMusic)
    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": "video"}
            
            async with session.get(
                f"{YOUR_API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    stream_url = data.get("stream_url")
                    
                    if stream_url:
                        async with session.get(
                            stream_url,
                            timeout=aiohttp.ClientTimeout(total=600)
                        ) as file_response:
                            if file_response.status == 200:
                                with open(file_path, "wb") as f:
                                    async for chunk in file_response.content.iter_chunked(16384):
                                        f.write(chunk)
                                logger.info(f"Video downloaded successfully via primary API: {file_path}")
                                return file_path
    except Exception as e:
        logger.warning(f"Primary video API failed: {e}")
        pass

    logger.warning("Primary video API failed. Falling back to secondary API.")
    # 2. Secondary API (TheQuickEarn)
    downloaded_file = await _download_video_secondary(link)
    
    if downloaded_file:
        logger.info(f"Video downloaded successfully via secondary API: {downloaded_file}")
        return downloaded_file
        
    logger.error("Both video APIs failed.")
    return None

# --- Utility Functions (Kept as is) ---

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


# --- YouTubeAPI Class ---

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
        
        # Use the unified video download function
        downloaded_file = await download_video(link)
        if downloaded_file:
            return 1, downloaded_file
        else:
            return 0, "Video download failed from all APIs"

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

        downloaded_file = None
        
        # Determine if video or audio download is requested
        if video:
            downloaded_file = await download_video(link)
        else: # Covers songaudio, songvideo, and default case
            downloaded_file = await download_song(link)
        
        # The 'direct' parameter is set to True as we are using direct API downloads
        if downloaded_file:
            return downloaded_file, True 
        else:
            return None, False
      
