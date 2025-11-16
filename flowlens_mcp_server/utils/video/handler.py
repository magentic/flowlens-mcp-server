import asyncio
import aiofiles
import cv2
import os
import shutil
import tempfile
from typing import Optional, Union
import aiohttp
from ..settings import settings
from ...dto import dto

class _FrameInfo:
    def __init__(self, buffer):
        self.buffer = buffer


class VideoHandler:
    def __init__(self, flow: Union[dto.FlowlensFlow, dto.FullFlow]):
        self._flow = flow
        if self._flow.is_local:
            self._video_dir_path = self._flow.local_files_data.extracted_dir_path
        else:
            self._video_dir_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.uuid}"
        self._video_name = "video.webm"

    async def load_video(self):
        await self._download_video()

    async def save_screenshot(self, video_sec: int) -> str:
        if self._flow.recording_type == dto.enums.RecordingType.RRWEB:
            return self._refer_rrweb_screenshot(video_sec)
        else:
            video_path = os.path.join(self._video_dir_path, self._video_name)
        if not os.path.exists(video_path):
            rrweb_message = "Wait for 20 seconds and try again as the video is still being processed."
            message = rrweb_message if self._flow.recording_type == dto.enums.RecordingType.RRWEB else "RRWEB video not found, we cannot extract screenshot."
            raise RuntimeError(f"Video file not found at {video_path}. {message}")
        frame_info = await asyncio.to_thread(self._extract_frame_buffer, video_path, video_sec)
        os.makedirs(self._video_dir_path, exist_ok=True)
        output_path = os.path.join(self._video_dir_path, f"screenshot_sec{video_sec}.jpg")

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(bytearray(frame_info.buffer))
        return os.path.abspath(output_path)
    
    def _refer_rrweb_screenshot(self, video_sec:int) -> str:
        if self._flow.is_rendering_finished:
            file_path = f"{self._video_dir_path}/screenshots/screenshot_sec{video_sec}.jpg"
            if os.path.exists(file_path):
                return os.path.abspath(file_path)
            msg = f"Failed to. render this second {video_sec} from RRWEB video. Please try take_flow_snapshot_at_second() instead."
            raise RuntimeError(msg)
        raise RuntimeError("RRWEB video is still being processed, cannot extract screenshot yet. Please try again in 20 seconds.")
        
    def _extract_frame_buffer(self, video_path:str, video_sec:int) -> _FrameInfo:
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
        return self._extract_frame_image(video_sec, frame)

    def _extract_frame_image(self, video_sec, frame):
        if frame is None:
            raise RuntimeError(f"Failed to extract frame at (video_sec {video_sec}sec).")

        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not success:
            raise RuntimeError("Failed to encode frame as JPEG")

        return _FrameInfo(buffer)
   
    async def _download_video(self):
        if not self._flow.video_url:
            return
        if self._flow.recording_type == dto.enums.RecordingType.WEBM:
            video_name = "video.webm"
        else:
            video_name = "rrweb_video.json"
            
        dest_path = os.path.join(self._video_dir_path, video_name)
        if os.path.exists(dest_path):
            return
        try:
            os.makedirs(self._video_dir_path, exist_ok=True)
            extension = ".webm" if self._flow.recording_type == dto.enums.RecordingType.WEBM else ".json"
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=extension)
            os.close(tmp_fd)
            timeout = aiohttp.ClientTimeout(connect=5, sock_read=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._flow.video_url) as resp:
                    resp.raise_for_status()
                    async with aiofiles.open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            await f.write(chunk)
            shutil.move(tmp_path, dest_path)
        except Exception as exc:
            raise RuntimeError(f"failed to download video: {exc}") from exc
