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

# Global logger and API URLs
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
                else:
                    SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
                    logger.info(f"Using fallback: {SHRUTIBOTS_FALLBACK_URL}")
                    return
    except Exception as e:
        SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
        logger.info(f"Using fallback due to error: {e}")

# Initialize API URL at startup
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_shrutibots_api_url())
    else:
        loop.run_until_complete(load_shrutibots_api_url())
except RuntimeError:
    pass

async def try_shrutibots_api(video_id: str, is_video: bool = False):
    global SHRUTIBOTS_API_URL
    if not SHRUTIBOTS_API_URL:
        await load_shrutibots_api_url()
        if not SHRUTIBOTS_API_URL:
            SHRUTIBOTS_API_URL = SHRUTIBOTS_FALLBACK_URL
    
    try:
        endpoint = f"{SHRUTIBOTS_API_URL}/download"
        params = {"url": video_id, "type": "video" if is_video else "audio"}
        
        logger.info(f"Trying ShrutiBots API: {endpoint}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                logger.info(f"ShrutiBots Response: {response.status}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"ShrutiBots Data keys: {list(data.keys())}")
                        stream_url = data.get("stream_url")
                        
                        if stream_url:
                            logger.info(f"ShrutiBots successful for {video_id}")
                            return stream_url, "ShrutiBots"
                        else:
                            logger.warning("No stream_url in response")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                else:
                    try:
                        error_text = await response.text()

logger.warning(f"ShrutiBots failed: {response.status} - {error_text[:100]}")
                    except:
                        logger.warning(f"ShrutiBots failed: {response.status}")
        
        return None, None
    except Exception as e:
        logger.error(f"ShrutiBots error: {str(e)}")
        return None, None

async def try_quickearn_api(video_id: str, is_video: bool = False):
    try:
        endpoint = f"{QUICKEARN_API_URL}/song/{video_id}?api={QUICKEARN_API_KEY}"
        if is_video:
            endpoint = f"{QUICKEARN_API_URL}/video/{video_id}?api={QUICKEARN_API_KEY}"
        
        logger.info(f"Trying QuickEarn API: {endpoint}")
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(5):  # Reduced from 10 to 5
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        logger.info(f"QuickEarn Response: {response.status} (attempt {attempt+1}/5)")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"QuickEarn Data status: {data.get('status')}")
                                
                                status = data.get("status", "").lower()
                                
                                if status == "done":
                                    download_url = data.get("link")
                                    if download_url:
                                        logger.info(f"QuickEarn successful for {video_id}")
                                        return download_url, "QuickEarn"
                                    else:
                                        logger.warning("No download link in response")
                                        break
                                
                                elif status == "downloading":
                                    wait_time = 4 if not is_video else 8
                                    logger.info(f"Status 'downloading', waiting {wait_time}s (attempt {attempt+1}/5)")
                                    await asyncio.sleep(wait_time)
                                    continue
                                
                                else:
                                    error_msg = data.get("error") or data.get("message") or f"Unknown status '{status}'"
                                    logger.warning(f"QuickEarn: {error_msg}")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON: {e}")
                                break
                        
                        else:
                            try:
                                error_text = await response.text()
                                logger.warning(f"QuickEarn failed: {response.status} - {error_text[:100]}")
                            except:
                                logger.warning(f"QuickEarn failed: {response.status}")
                            break
                
                except Exception as e:
                    logger.error(f"QuickEarn request error: {e}")
                    if attempt < 4:
                        await asyncio.sleep(2)
                        continue
                    else:
                        break
            
            logger.warning(f"QuickEarn max retries exhausted for {video_id}")
            return None, None
            
    except Exception as e:
        logger.error(f"QuickEarn general error: {str(e)}")
        return None, None

async def download_with_fallback(video_id: str, file_path: str, is_video: bool = False):
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        min_size = 1024 * 100 if is_video else 1024
        if file_size > min_size:
            logger.info(f"Using existing file: {file_path}, Size: {file_size} bytes")
            return True, "ExistingFile"
    
    download_url, api_name = await try_shrutibots_api(video_id, is_video)
    
    if not download_url:
        logger.warning(f"ShrutiBots failed, trying QuickEarn...")
        download_url, api_name = await try_quickearn_api(video_id, is_video)
    
    if not download_url:
        logger.error(f"Both APIs failed for {video_id}")
        return False, None

try:
        timeout = aiohttp.ClientTimeout(total=None, sock_read=120)  # Better timeout strategy
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=timeout) as response:
                if response.status != 200:
                    logger.error(f"Download failed: {response.status}")
                    return False, None
                
                content_length = int(response.headers.get('Content-Length', 0)) or 'Unknown'
                content_type = response.headers.get('Content-Type', 'Unknown')
                logger.info(f"Downloading: {content_length} bytes, Type: {content_type}")
                
                total_written = 0
                with open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(16384):
                        if chunk:  # Skip empty chunks
                            f.write(chunk)
                            total_written += len(chunk)
                
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    min_size = 1024 * 100 if is_video else 1024
                    logger.info(f"File saved: {file_path}, Size: {file_size} bytes")
                    
                    if file_size < min_size:
                        logger.error(f"File too small: {file_size} bytes (min: {min_size})")
                        os.remove(file_path)
                        return False, None
                    
                    return True, api_name
                else:
                    logger.error("File not created successfully")
                    return False, None
                    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return False, None

async def download_song(link: str) -> str:
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        logger.error(f"Invalid video_id: {video_id}")
        return None
    
    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Check existing files
    for ext in ["mp3", "m4a", "webm"]:
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
            logger.info(f"Using existing audio: {file_path}")
            return file_path
    
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    
    success, api_used = await download_with_fallback(video_id, file_path, is_video=False)
    
    if success and os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
        logger.info(f"Audio downloaded successfully: {video_id} using {api_used}")
        return file_path
    
    logger.error(f"Audio download failed for {video_id}")
    return None

async def download_video(link: str) -> str:
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        logger.error(f"Invalid video_id: {video_id}")
        return None
    
    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Check existing files
    for ext in ["mp4", "webm", "mkv"]:
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024 * 100:
            logger.info(f"Using existing video: {file_path}")
            return file_path
    
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
    
    success, api_used = await download_with_fallback(video_id, file_path, is_video=True)
    
    if success and os.path.exists(file_path) and os.path.getsize(file_path) > 1024 * 100:
        logger.info(f"Video downloaded successfully: {video_id} using {api_used}")
        return file_path
    
    logger.error(f"Video download failed for {video_id}")
    return None

async def shell_cmd(cmd):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, errorz = await proc.communicate()
        if errorz:
            error_text = errorz.decode("utf-8").lower()
            if "unavailable videos are hidden" in error_text:
                return out.decode("utf-8")
            else:
                return errorz.decode("utf-8")
        return out.decode("utf-8")
    except Exception as e:
        logger.error(f"Shell command error: {e}")
        return ""

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube.com|youtu.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\u001B(?:[@-Z\\-_]|[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
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
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            video_data = (await results.next())["result"]
            if not video_data:
                return None, None, None, None, None
                
            result = video_data[0]
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
            return title, duration_min, duration_sec, thumbnail, vidid
        except Exception as e:
            logger.error(f"Details fetch error: {e}")
            return None, None, None, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            video_data = (await results.next())["result"]
            return video_data[0]["title"] if video_data else None
        except:
            return None

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            video_data = (await results.next())["result"]
            return video_data[0]["duration"] if video_data else None
        except:
            return None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            video_data = (await results.next())["result"]
            return video_data[0]["thumbnails"][0]["url"].split("?")[0] if video_data else None
        except:
            return None

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            downloaded_file = await download_video(link)
            if downloaded_file:
                return 1, downloaded_file
            else:
                return 0, "Video download failed"
        except Exception as e:
            logger.error(f"Video method error: {e}")
            return 0, f"Video download error: {str(e)}"

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            playlist = await shell_cmd(
                f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
            )
            result = [key.strip() for key in playlist.split("
") if key.strip()]
            return result
        except:
            return []
            async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            video_data = (await results.next())["result"]
            result = video_data[0]
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
        except:
            return {}, None

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            ytdl_opts = {"quiet": True, "no_warnings": True}
            ydl = yt_dlp.YoutubeDL(ytdl_opts)
            with ydl:
                formats_available = []
                r = ydl.extract_info(link, download=False)
                for format in r["formats"]:
                    try:
                        if "dash" not in str(format.get("format_id", "")).lower():
                            formats_available.append(
                                {
                                    "format": format.get("format", ""),
                                    "filesize": format.get("filesize"),
                                    "format_id": format["format_id"],
                                    "ext": format["ext"],
                                    "format_note": format.get("format_note", ""),
                                    "yturl": link,
                                }
                            )
                    except:
                        continue
                return formats_available, link
        except Exception as e:
            logger.error(f"Formats error: {e}")
            return [], link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + str(videoid)
        if "&" in link:
            link = link.split("&")[0]
        try:
            a = VideosSearch(link, limit=10)
            result = (await a.next()).get("result", [])
            if query_type < len(result):
                item = result[query_type]
                title = item["title"]
                duration_min = item["duration"]
                vidid = item["id"]
                thumbnail = item["thumbnails"][0]["url"].split("?")[0]
                return title, duration_min, thumbnail, vidid
            return None, None, None, None
        except:
            return None, None, None, None

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
    ) -> tuple:
        if videoid:
            link = self.base + str(videoid)

        try:
            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)
            
            if downloaded_file:
                if os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file)
                    min_size = 1024 * 100 if video else 1024
                    
                    if file_size < min_size:
                        logger.error(f"File too small: {file_size} bytes (min: {min_size})")
                        try:
                            os.remove(downloaded_file)
                        except:
                            pass
                        return None, False
                    
                    logger.info(f"File validated: {downloaded_file}, Size: {file_size} bytes")
                    return downloaded_file, True
                else:
                    logger.error(f"Downloaded file not found: {downloaded_file}")
                    return None, False
            else:
                logger.error("Download returned None - no file generated")
                return None, False
                
        except Exception as e:
            logger.error(f"Download method exception: {str(e)}")
            return None, False
