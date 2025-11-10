

import asyncio
import json
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
        html_content = self._generate_html_with_embedded_events(rrweb_events)
        video_path = await self._record_rrweb_to_video(html_content)
        return video_path
        
    
    async def _extract_events(self, video_relative_sec: int):
        # work around showing white screen with a cursor
        if video_relative_sec == 0:
            video_relative_sec = 1
        async with aiofiles.open(self.rrweb_json_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        first_event_ts = rrweb_events[0]['timestamp']
        full_snapshot_index = None
        end_event_index = None
        for i, event in enumerate(rrweb_events):
            if event['type'] == 2:  # Full snapshot
                full_snapshot_index = i
            event_relative_sec = (event['timestamp'] - first_event_ts) / 1000.0
            if event_relative_sec > video_relative_sec:
                end_event_index = i
                break

        # Ensure we have at least 2 events (rrweb requirement)
        if end_event_index is None:
            end_event_index = len(rrweb_events)
        if end_event_index <= full_snapshot_index + 1:
            end_event_index = min(full_snapshot_index + 2, len(rrweb_events))

        print(f"Full snapshot index: {full_snapshot_index}, End event index: {end_event_index}")
        return rrweb_events[0:end_event_index]
    
    async def _record_rrweb_to_video(self, html_content: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": self._video_width, "height": self._video_height},
                record_video_dir="data/",
                record_video_size={"width": self._video_width, "height": self._video_height}
            )
            page = await context.new_page()

            # Create event to signal when replay is finished
            replay_finished = asyncio.Event()

            # Navigate to blank page first
            await page.goto("about:blank")

            # Expose callback functions to the page BEFORE setting content
            await page.expose_function("onReplayFinish", lambda: replay_finished.set())
            await page.expose_function(
                "onReplayProgressUpdate",
                lambda payload: print(f"⏳ Replay progress: {payload.get('payload', 0) if isinstance(payload, dict) else payload}")
            )

            # Set HTML content (matching rrvideo approach)
            await page.set_content(html_content, wait_until="networkidle")


            # Wait for the replay to finish (event-driven instead of fixed duration)
            print("⏳ Waiting for replay to finish...")
            await replay_finished.wait()
            print("✓ Replay finished")

            # Add a small buffer to ensure video encoding completes
            await page.wait_for_timeout(500)

            # Finalize recording
            await page.close()
            video_path = await page.video.path()
            print("Local video path", video_path)
            await context.close()
            await browser.close()

            return str(video_path)
        
    
    async def _wait_for_player_ready(self, page: Page) -> None:
        """Wait for rrweb player to load and be ready"""
        print("⏳ Waiting for rrweb player to load...")

        # Wait for the replayer wrapper to be created
        await page.wait_for_selector(".replayer-wrapper", timeout=self._selector_timeout_ms)

        # Wait for rrweb player component to be attached
        await page.wait_for_selector(".rr-player", timeout=self._selector_timeout_ms)

        # Wait for window.replayer to be defined
        await page.wait_for_function("typeof window.replayer !== 'undefined'", timeout=self._selector_timeout_ms)
        print("✓ window.replayer is ready")

        # Wait for the iframe to be present (rrweb uses iframe for replay)
        try:
            await page.wait_for_selector("iframe.replayer-iframe", timeout=self._selector_timeout_ms)
            print("✓ Player iframe detected")
        except Exception:
            print("⚠ Warning: No iframe detected, but continuing...")

        # Wait for any network activity to settle
        await page.wait_for_load_state("networkidle", timeout=self._selector_timeout_ms)

        print("✓ Player loaded successfully")
        
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
      window.replayer.addEventListener('finish', () => window.onReplayFinish());
      window.replayer.addEventListener('ui-update-progress', (payload) => window.onReplayProgressUpdate(payload));
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay")
        return html_content