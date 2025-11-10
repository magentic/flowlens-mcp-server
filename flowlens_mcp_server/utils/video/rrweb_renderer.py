

import asyncio
import json
import aiofiles
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
            await page.video.save_as(self._video_path)
            await context.close()
            await browser.close()
        
        
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