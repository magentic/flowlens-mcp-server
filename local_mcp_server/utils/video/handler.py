from typing import Optional
import aiohttp
import aiofiles
import asyncio
import base64
import cv2
import os
import shutil
import tempfile
from ..settings import settings

class VideoHandlerParams:
    def __init__(self, flow_id: int, 
                 duration_ms: Optional[float] = None,
                 url: Optional[str] = None):
        self.url = url
        self.flow_id = flow_id
        self.duration_ms = duration_ms
        print(url)

class _FrameInfo:
    def __init__(self, index: int, buffer):
        self.index = index
        self.buffer = buffer
             
class VideoHandler:
    def __init__(self, params: VideoHandlerParams):
        self._params = params
        self._video_dir_path = f"{settings.save_dir_path}/videos/{self._params.flow_id}"
        self._video_name = "video.webm"
        
    async def load_video(self):
        await self._download_video()
    
    async def take_screenshot_base64(self, timestamp: int) -> str:
        video_path = f"{self._video_dir_path}/{self._video_name}"
        if not os.path.exists(video_path):
            raise RuntimeError(f"video not found for flow id {self._params.flow_id}")
        return await asyncio.to_thread(self._extract_frame, timestamp)

    def _extract_frame(self, timestamp: float):
        frame_info = self._extract_frame_buffer(timestamp)
        return base64.b64encode(frame_info.buffer.tobytes()).decode('utf-8')

    async def save_screenshot(self, timestamp: float) -> str:
        frame_info = await self._extract_frame_async(timestamp)
        output_path = f"{self._video_dir_path}/screenshot_{frame_info.index}.jpg"
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(frame_info.buffer.tobytes())
        return os.path.abspath(output_path)
    
    async def _extract_frame_async(self, timestamp):
        return await asyncio.to_thread(self._extract_frame_buffer, timestamp)

    def _extract_frame_buffer(self, timestamp) -> _FrameInfo:
        video_path = f"{self._video_dir_path}/{self._video_name}"
        cap = cv2.VideoCapture(video_path)
        fps = self._calculate_fps(cap)
        print(f"Calculated FPS: {fps}")
        
        frame_index = int(timestamp * fps)
        print(f"Extracting frame at index: {frame_index} for timestamp: {timestamp}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise RuntimeError(f"Failed to read frame at timestamp {timestamp}")
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return _FrameInfo(frame_index, buffer)

    def _calculate_fps(self, cap):
        frames_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        print(f"Frames count: {frames_count}")
        print(f"Duration ms: {self._params.duration_ms}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            return fps
       
        duration_sec = (self._params.duration_ms or 0) / 1000
        if frames_count > 0 and duration_sec > 0:
            fps = frames_count / duration_sec
            return fps
        default_fps = 25
        return default_fps


    async def _download_video(self):
        if not self._params.url:
            return
        if os.path.exists(f"{self._video_dir_path}/{self._video_name}"):
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
            dest_path = f"{self._video_dir_path}/{self._video_name}"
            shutil.move(tmp_path, dest_path)
        except Exception as exc:
            # normalize aiohttp/client/IO errors into a RuntimeError like the original
            raise RuntimeError(f"failed to download video: {exc}") from exc