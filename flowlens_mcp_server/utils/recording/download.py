import os
from ...models.enums import RecordingType
import tempfile
import aiofiles
import aiohttp
import shutil
from ..settings import settings

async def download_recording(flow_uuid:str, flow_type:RecordingType, video_url:str ):
    """Download video from remote URL if not already present."""
    if not video_url:
        return
    
    video_dir_path = f"{settings.flowlens_save_dir_path}/flows/{flow_uuid}"
    
    if flow_type == RecordingType.RRWEB:
        video_name = "rrweb_video.json"
        suffix = ".json"
    elif flow_type == RecordingType.WEBM:
        video_name = "video.webm"
        suffix = ".webm"
        
    dest_path = os.path.join(video_dir_path, video_name)
    if os.path.exists(dest_path):
        return

    try:
        os.makedirs(video_dir_path, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(tmp_fd)

        timeout = aiohttp.ClientTimeout(connect=5, sock_read=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(video_url) as resp:
                resp.raise_for_status()
                async with aiofiles.open(tmp_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        await f.write(chunk)

        shutil.move(tmp_path, dest_path)
    except Exception as exc:
        raise RuntimeError(f"failed to download video: {exc}") from exc
