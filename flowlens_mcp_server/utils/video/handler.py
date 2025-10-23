import asyncio
import aiofiles
import cv2
import os
import shutil
import tempfile
from typing import Optional
import aiohttp
from ..settings import settings



class VideoHandlerParams:
    def __init__(self, flow_id: str, url: Optional[str] = None):
        self.url = url
        self.flow_id = flow_id


class _FrameInfo:
    def __init__(self, buffer):
        self.buffer = buffer


class VideoHandler:
    def __init__(self, params: VideoHandlerParams):
        self._params = params
        self._video_dir_path = f"{settings.flowlens_save_dir_path}/flows/{self._params.flow_id}"
        self._video_name = "video.webm"

    async def load_video(self):
        await self._download_video()

    async def save_screenshot(self, video_sec: int) -> str:
        frame_info = await asyncio.to_thread(self._extract_frame_buffer, video_sec)
        os.makedirs(self._video_dir_path, exist_ok=True)
        output_path = os.path.join(self._video_dir_path, f"screenshot_sec{video_sec}.jpg")

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(bytearray(frame_info.buffer))
        return os.path.abspath(output_path)

    def _extract_frame_buffer(self, video_sec) -> _FrameInfo:
        video_path = os.path.join(self._video_dir_path, self._video_name)
        cap = cv2.VideoCapture(video_path)
        frame = None
        ts = -1
        while True:
            ret = cap.grab()  # Fast frame grab without decoding
            if not ret:
                break
            ts = int(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0)
            if ts == video_sec:
                ret, frame = cap.read()
                break
        cap.release()
        
        if frame is None:
            raise RuntimeError(f"Failed to extract frame at (video_sec {video_sec}sec).  last frame timestamp: {ts}sec")

        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not success:
            raise RuntimeError("Failed to encode frame as JPEG")

        return _FrameInfo(buffer)

   
    async def _download_video(self):
        if not self._params.url:
            return
        dest_path = os.path.join(self._video_dir_path, self._video_name)
        if os.path.exists(dest_path):
            return
        try:
            os.makedirs(self._video_dir_path, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".webm")
            os.close(tmp_fd)
            timeout = aiohttp.ClientTimeout(connect=5, sock_read=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._params.url) as resp:
                    resp.raise_for_status()
                    async with aiofiles.open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            await f.write(chunk)
            shutil.move(tmp_path, dest_path)
        except Exception as exc:
            raise RuntimeError(f"failed to download video: {exc}") from exc
