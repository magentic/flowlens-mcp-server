

import asyncio
import json
import aiofiles
import base64
import subprocess
import tempfile
import os
from typing import List
from playwright.async_api import async_playwright

from ...utils.settings import settings
from ...dto import dto

class RrwebRenderer:
    def __init__(self, flow: dto.FullFlow):
        self._flow = flow
        self._video_width = 1280
        self._video_height = 720
        self._selector_timeout_ms = 5000 # 5 seconds
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._video_path = self._flow.local_files_data.video_file_path
        else:
            self._rrweb_file_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/rrweb_video.json"
            self._video_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/video.webm"
    
    def render_rrweb(self):
        asyncio.create_task(self._render_rrweb())
        
    async def _render_rrweb(self):
        rrweb_events = await self._extract_events()
        if not rrweb_events:
            raise ValueError("No rrweb events found for the specified time range.")
        html_content = self._generate_html_with_embedded_events(rrweb_events)
        await self._record_rrweb_to_video(html_content)
        
    async def _extract_events(self):
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events

    async def _encode_frames_to_video(self, frames: List[bytes], frame_metadata: List[dict]) -> None:
        """
        Encode captured screencast frames to video using ffmpeg.
        Frames are JPEG images captured via CDP screencast.
        """
        if not frames:
            raise ValueError("No frames to encode")

        # Calculate frame rate from metadata timestamps
        if len(frame_metadata) > 1:
            # Calculate average time between frames
            total_duration = frame_metadata[-1]["timestamp"] - frame_metadata[0]["timestamp"]
            fps = len(frames) / total_duration if total_duration > 0 else 30
            fps = min(max(fps, 15), 60)  # Clamp between 15-60 fps
        else:
            fps = 30  # Default fallback

        print(f"🎬 Calculated FPS: {fps:.2f}")

        # Create temporary directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save frames as individual JPEG files
            for i, frame_data in enumerate(frames):
                frame_path = os.path.join(temp_dir, f"frame_{i:06d}.jpg")
                with open(frame_path, "wb") as f:
                    f.write(frame_data)

            # Use ffmpeg to encode frames to video
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-framerate", str(fps),
                "-i", os.path.join(temp_dir, "frame_%06d.jpg"),
                "-c:v", "libvpx-vp9",  # VP9 codec for .webm
                "-pix_fmt", "yuv420p",
                "-b:v", "2M",  # Bitrate
                "-deadline", "good",  # Encoding speed/quality tradeoff
                self._video_path
            ]

            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"ffmpeg encoding failed: {error_msg}")

            print(f"✓ Video saved to: {self._video_path}")

    async def _record_rrweb_to_video(self, html_content: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": self._video_width, "height": self._video_height}
            )
            page = await context.new_page()

            # Create events to signal recording milestones
            player_started = asyncio.Event()
            replay_finished = asyncio.Event()

            # List to store screencast frames
            frames = []
            frame_metadata = []

            # Navigate to blank page first
            await page.goto("about:blank")

            # Create CDP session for screencast
            cdp = await page.context.new_cdp_session(page)

            # Expose callback functions to the page BEFORE setting content
            async def on_player_started():
                player_started.set()
                print("🎬 Player started - beginning screencast recording")
                # Start screencast recording when player starts (perfect alignment!)
                await cdp.send("Page.startScreencast", {
                    "format": "jpeg",
                    "quality": 90,
                    "maxWidth": self._video_width,
                    "maxHeight": self._video_height,
                    "everyNthFrame": 1
                })

            await page.expose_function("onPlayerStarted", on_player_started)
            await page.expose_function("onReplayFinish", lambda: replay_finished.set())
            await page.expose_function(
                "onReplayProgressUpdate",
                lambda payload: print(f"⏳ Replay progress: {payload.get('payload', 0) if isinstance(payload, dict) else payload}")
            )

            # Set up CDP event listener for screencast frames
            def on_screencast_frame(params):
                frames.append(base64.b64decode(params["data"]))
                frame_metadata.append(params["metadata"])
                # Acknowledge frame to get the next one
                asyncio.create_task(cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]}))

            cdp.on("Page.screencastFrame", on_screencast_frame)

            # Set HTML content (matching rrvideo approach)
            await page.set_content(html_content, wait_until="networkidle")

            # Wait for player to start
            print("⏳ Waiting for player to start...")
            await player_started.wait()

            # Wait for the replay to finish (event-driven instead of fixed duration)
            print("⏳ Waiting for replay to finish...")
            await replay_finished.wait()
            print("✓ Replay finished")

            # Stop screencast
            await cdp.send("Page.stopScreencast")

            # Add a small buffer to ensure all frames are captured
            await page.wait_for_timeout(500)

            # Close browser
            await page.close()
            await context.close()
            await browser.close()

            # Encode frames to video
            print(f"🎞️  Encoding {len(frames)} frames to video...")
            await self._encode_frames_to_video(frames, frame_metadata)
        
        
    def _generate_html_with_embedded_events(self, events: List) -> str:
        """
        Generate HTML content with rrweb events embedded directly.
        HTML structure matches rrvideo reference implementation.
        Returns the HTML string (not a file path).
        """
        # Escape </script> tags in JSON to prevent premature script closing
        events_json = json.dumps(events).replace('</script>', '<\\/script>')

        html_content = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/style.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/index.js"></script>
    <style>html, body {{padding: 0; border: none; margin: 0;}}</style>
  </head>
  <body>
    <script>
      /*<!--*/
      const events = {events_json};
      /*-->*/
      const userConfig = {{width: {self._video_width}, height: {self._video_height}}};
      window.replayer = new rrwebPlayer({{
        events,
        target: document.body,
        width: userConfig.width,
        height: userConfig.height,
        props: {{
          ...userConfig,
          events,
          showController: false,
          autoPlay: true
        }}
      }});
      window.replayer.addEventListener('start', () => window.onPlayerStarted());
      window.replayer.addEventListener('finish', () => window.onReplayFinish());
      window.replayer.addEventListener('ui-update-progress', (payload) => window.onReplayProgressUpdate(payload));
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay")
        return html_content