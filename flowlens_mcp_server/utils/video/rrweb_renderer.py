

import json
import os
import shutil
import tempfile
import aiofiles
from typing import List
from playwright.async_api import async_playwright, Page


class RrwebRenderer:
    def __init__(self, rrweb_json_path: str):
        self.rrweb_json_path = rrweb_json_path
        self._video_width = 1280
        self._video_height = 720
        self._selector_timeout_ms = 5000 # 5 seconds
    
    async def render_second(self, video_extract_events_sec: int) -> str:
        rrweb_events = await self._extract_events(video_extract_events_sec)
        if not rrweb_events:
            raise ValueError("No rrweb events found for the specified time range.")
        html_path = self._generate_html_with_embedded_events(rrweb_events)
        session_duration = self._calculate_recording_duration(rrweb_events)
        video_path = await self._record_rrweb_to_video(html_path, session_duration)
        # os.remove(html_path)
        shutil.move(html_path, "data/rrweb_temp2.html")
        return video_path
        
    
    async def _extract_events(self, video_relative_sec: int):
        async with aiofiles.open(self.rrweb_json_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        first_event_ts = rrweb_events[0]['timestamp']
        full_snapshot_index = None
        end_event_index = None
        for i, event in enumerate(rrweb_events):
            if event['type'] == 2 and event_relative_sec <= video_relative_sec:  # Full snapshot
                full_snapshot_index = i
            event_relative_sec = (event['timestamp'] - first_event_ts) / 1000.0
            if event_relative_sec >= video_relative_sec:
                end_event_index = i
                break
        if end_event_index == full_snapshot_index:
            end_event_index += 1
        print(f"Full snapshot index: {full_snapshot_index}, End event index: {end_event_index}")
        return rrweb_events[full_snapshot_index:end_event_index]
    
    async def _record_rrweb_to_video(self, html_path: str, video_duration: float) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": self._video_width, "height": self._video_height},
                record_video_dir="data/",
                record_video_size={"width": self._video_width, "height": self._video_height}
            )
            page = await context.new_page()

            # Navigate to the HTML file
            await page.goto(f"file://{html_path}", wait_until="networkidle")

            # Wait for player to be ready
            await self._wait_for_player_ready(page)
            
            await page.wait_for_timeout(int(video_duration * 1000))
            
            # Finalize recording
            await page.close()
            video_path = page.video.path()
            await context.close()
            await browser.close()

            return str(video_path)
        
    
    async def _wait_for_player_ready(self, page: Page) -> None:
        """Wait for rrweb player to load and be ready"""
        print("⏳ Waiting for rrweb player to load...")

        # Wait for the player container
        await page.wait_for_selector("#player", timeout=self._selector_timeout_ms)

        # Wait for rrweb player component to be attached
        await page.wait_for_selector("#player .rr-player", timeout=self._selector_timeout_ms)

        # Wait for the iframe to be present (rrweb uses iframe for replay)
        try:
            await page.wait_for_selector("#player iframe", timeout=self._selector_timeout_ms)
            print("✓ Player iframe detected")
        except Exception:
            print("⚠ Warning: No iframe detected, but continuing...")

        # Wait for any network activity to settle
        await page.wait_for_load_state("networkidle", timeout=self._selector_timeout_ms)

        print("✓ Player loaded successfully")
        
    def _generate_html_with_embedded_events(self, events: List) -> str:
        """
        Generate an HTML file with rrweb events embedded directly.
        This avoids CORS issues with file:// protocol.
        """
        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/index.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/style.css" rel="stylesheet" />
    <style>
        html, body {{
        margin: 0;
        height: 100%;
        background: #fff;
        }}
        #player {{
        width: {self._video_width}px;
        height: {self._video_height}px;
        }}
    </style>
    </head>
    <body>
    <div id="player"></div>
    <script>
        const events = {json.dumps(events)};
        new rrwebPlayer({{
        target: document.getElementById('player'),
        props: {{ events, width: {self._video_width}, height: {self._video_height}, autoPlay: true }}
        }});
    </script>
    </body>
    </html>"""
        
        print(f"📝 Creating temporary HTML file...")
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".html")
        os.close(tmp_fd)
        with open(tmp_path, 'w') as f:
            f.write(html_content)
        
        return tmp_path
    
    
    def _calculate_recording_duration(self, events: List) -> float:
        first_timestamp = events[0].get("timestamp", 0)
        last_timestamp = events[-1].get("timestamp", 0)
        
        duration_ms = last_timestamp - first_timestamp
        duration_seconds = duration_ms / 1000
        return duration_seconds