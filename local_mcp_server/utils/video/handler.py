import asyncio
import aiofiles
import base64
import cv2
import os
import shutil
import tempfile
from typing import Optional
import aiohttp
from ..settings import settings


# Module-level cache: {video_path: [(frame_index, timestamp), ...]}
_FRAME_TIMESTAMP_CACHE = {}


class VideoHandlerParams:
    def __init__(self, flow_id: int, url: Optional[str] = None):
        self.url = url
        self.flow_id = flow_id


class _FrameInfo:
    def __init__(self, index: int, buffer):
        self.index = index
        self.buffer = buffer


class VideoHandler:
    def __init__(self, params: VideoHandlerParams):
        self._params = params
        self._video_dir_path = f"{settings.save_dir_path}/flows/{self._params.flow_id}"
        self._video_name = "video.webm"

    async def load_video(self):
        await self._download_video()

    async def save_screenshot(self, video_sec: int) -> str:
        frame_info = await self._extract_frame_async(video_sec)
        os.makedirs(self._video_dir_path, exist_ok=True)

        output_path = os.path.join(self._video_dir_path, f"screenshot_sec{video_sec}.jpg")

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(bytearray(frame_info.buffer))

        return os.path.abspath(output_path)

    async def _extract_frame_async(self, video_sec):
        return await asyncio.to_thread(self._extract_frame_buffer, video_sec)

    def _extract_frame_buffer(self, video_sec) -> _FrameInfo:
        video_path = os.path.join(self._video_dir_path, self._video_name)

        # Load frame timestamps if not cached
        if video_path not in _FRAME_TIMESTAMP_CACHE:
            _FRAME_TIMESTAMP_CACHE[video_path] = self._load_frame_timestamps(video_path)

        # Find the best matching frame for the requested timestamp
        best_frame_index = self._find_closest_frame(video_sec, _FRAME_TIMESTAMP_CACHE[video_path])

        # Extract that specific frame
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, best_frame_index)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise RuntimeError(f"Failed to extract frame at index {best_frame_index} (video_sec {video_sec}s)")

        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not success:
            raise RuntimeError("Failed to encode frame as JPEG")

        return _FrameInfo(best_frame_index, buffer)

    def _load_frame_timestamps(self, video_path: str) -> list[tuple[int, float]]:
        """Load all frame timestamps by iterating through video. Returns list of (frame_index, timestamp)."""
        try:
            cap = cv2.VideoCapture(video_path)
            timestamps = []
            frame_idx = 0

            while True:
                ret = cap.grab()  # Fast frame grab without decoding
                if not ret:
                    break
                ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                timestamps.append((frame_idx, ts))
                frame_idx += 1

            cap.release()

            if not timestamps:
                raise RuntimeError("No frames found in video")

            return timestamps
        except Exception as e:
            raise RuntimeError(f"Failed to load frame timestamps: {e}")

    def _find_closest_frame(self, target_timestamp: float, frame_timestamps: list) -> int:
        """Find the frame index closest to the target timestamp."""
        if not frame_timestamps:
            raise RuntimeError("Frame timestamps not loaded")

        # Validate timestamp is within video duration
        last_timestamp = frame_timestamps[-1][1]
        if target_timestamp > last_timestamp + 1:
            raise ValueError(f"Requested timestamp {target_timestamp:.3f}s exceeds video duration {last_timestamp:.3f}s")

        # Binary search for closest timestamp
        best_idx = 0
        min_diff = abs(frame_timestamps[0][1] - target_timestamp)

        for frame_idx, ts in frame_timestamps:
            diff = abs(ts - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                best_idx = frame_idx
            elif diff > min_diff:
                # Timestamps are sorted, so we can stop early
                break

        return best_idx


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
