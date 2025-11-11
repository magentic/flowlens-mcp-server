

import asyncio
import os
import json
import aiofiles
import time
from typing import List
from playwright.async_api import async_playwright

from ...utils.settings import settings
from ...utils.flow_registry import flow_registry
from ...dto import dto

class RrwebRenderer:
    def __init__(self, flow: dto.FullFlow):
        self._flow = flow
        self._video_width = 1280
        self._video_height = 720
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._video_path = self._flow.local_files_data.video_file_path
            self._screenshot_dir = self._flow.local_files_data.extracted_dir_path
        else:
            self._rrweb_file_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/rrweb_video.json"
            self._video_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/video.webm"
            self._screenshot_dir = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/extracted"
            os.makedirs(self._screenshot_dir, exist_ok=True)
    
    def render_rrweb(self):
        asyncio.create_task(self._render_rrweb())
        
    async def _render_rrweb(self):
        rrweb_events = await self._extract_events()
        if not rrweb_events:
            raise ValueError("No rrweb events found for the specified time range.")

        # Get first event timestamp for calculating relative time
        first_event_timestamp = rrweb_events[0]['timestamp']

        # Filter for type 2 (FullSnapshot) events
        type2_events = [event for event in rrweb_events if event.get('type') == 2]

        if not type2_events:
            raise ValueError("No type 2 (FullSnapshot) events found in rrweb recording.")

        # Get the first type 2 event timestamp as the base (video start time)
        base_timestamp = type2_events[0]['timestamp']

        print(f"📊 Found {len(type2_events)} type 2 (FullSnapshot) events")
        print(f"📍 First event timestamp: {first_event_timestamp}ms")
        print(f"📍 Base timestamp (first type 2): {base_timestamp}ms")

        # Calculate video duration from base timestamp
        video_duration_ms = rrweb_events[-1]['timestamp'] - base_timestamp
        video_duration_secs = video_duration_ms / 1000.0

        # Calculate exact second timestamps relative to first event (for goto())
        # Structure: {second: exact_relative_timestamp_ms}
        exact_seconds = {}
        for second in range(int(video_duration_secs) + 1):
            # Exact timestamp for this second mark
            abs_timestamp = base_timestamp + (second * 1000)
            relative_timestamp = int(abs_timestamp - first_event_timestamp)
            exact_seconds[second] = relative_timestamp

        print(f"📍 Using exact second timestamps")
        print(f"📍 Video duration: {video_duration_secs:.2f}s")
        print(f"📍 Total seconds to capture: {len(exact_seconds)}")

        duration_ms = rrweb_events[-1]['timestamp'] - rrweb_events[0]['timestamp']
        duration_secs = duration_ms / 1000.0
        print(f"📊 Total recording duration: {duration_secs:.2f}s")
        html_content = self._generate_html_with_embedded_events(rrweb_events)
        is_rendering_finished = await self._record_rrweb_to_video(html_content, exact_seconds)
        await flow_registry.set_finished_rendering(self._flow.id, is_rendering_finished)
        
    async def _extract_events(self):
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events
    
    async def _record_rrweb_to_video(self, html_content: str, exact_seconds: dict) -> str:
        start = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": self._video_width, "height": self._video_height},
                # record_video_dir="data/",
                # record_video_size={"width": self._video_width, "height": self._video_height}
            )
            page = await context.new_page()
            page.set_default_timeout(0)
            
            # Create events to signal when replay has started and finished
            replay_started = asyncio.Event()
            replay_finished = asyncio.Event()

            # Time synchronization for seeking
            target_timestamp = {"value": 0}  # Using dict to allow modification in closure
            time_reached = asyncio.Event()

            def on_time_update(current_time):
                """Called when player time updates. Checks if we've reached the target timestamp."""
                # Allow small tolerance (50ms) for time matching
                if abs(current_time - target_timestamp["value"]) < 50:
                    time_reached.set()

            # Navigate to blank page first
            await page.goto("about:blank")

            # Expose callback functions to the page BEFORE setting content
            await page.expose_function("onReplayStart", lambda: replay_started.set())
            await page.expose_function("onReplayFinish", lambda: replay_finished.set())
            await page.expose_function("onTimeUpdate", on_time_update)

            # Set the HTML content with rrweb player
            await page.set_content(html_content, wait_until="networkidle")

            # Wait for the replay to start (signals that player is ready)
            await replay_started.wait()

            # Immediately pause the player to take manual control
            await page.evaluate("window.replayer.pause()")

            # Sequential screenshot capture: loop through each second
            total_seconds = len(exact_seconds)
            max_retries = 5  # Retry up to 5 times
            retry_increment_ms = 100  # Move 100ms forward on each retry

            for second in sorted(exact_seconds.keys()):
                exact_timestamp = exact_seconds[second]
                print(f"\n📍 Second {second}: Starting at exact timestamp {exact_timestamp}ms")

                screenshot_taken = False
                # Try up to 6 attempts (original + 5 retries)
                for attempt in range(max_retries + 1):
                    # Calculate timestamp with retry offset
                    current_timestamp = exact_timestamp + (attempt * retry_increment_ms)
                    timestamp_secs = current_timestamp / 1000.0

                    # Set target timestamp and reset the event
                    target_timestamp["value"] = current_timestamp
                    time_reached.clear()

                    # Seek to the specific timestamp with timeout
                    if attempt == 0:
                        print(f"⏱ Attempt {attempt + 1}/{max_retries + 1}: Seeking to {timestamp_secs:.2f}s (relative: {current_timestamp}ms)")
                    else:
                        print(f"⏱ Retry {attempt}/{max_retries}: Seeking to {timestamp_secs:.2f}s (relative: {current_timestamp}ms, +{attempt * retry_increment_ms}ms offset)")

                    try:
                        # Wrap entire attempt in a timeout to ensure we never get stuck
                        async def try_screenshot():
                            # Goto with shorter timeout
                            await asyncio.wait_for(
                                page.evaluate(f"window.replayer.goto({current_timestamp})"),
                                timeout=1.5
                            )

                            # Wait for player to reach the target timestamp
                            await asyncio.wait_for(time_reached.wait(), timeout=2.0)

                            # Take screenshot
                            screenshot_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"
                            await page.screenshot(path=screenshot_path)
                            return True

                        # Overall timeout for entire attempt
                        success = await asyncio.wait_for(try_screenshot(), timeout=4.0)
                        if success:
                            print(f"✅ Player reached {current_timestamp}ms")
                            print(f"📸 Captured screenshot for second {second} at {current_timestamp}ms")
                            screenshot_taken = True
                            break  # Success! Move to next second

                    except asyncio.TimeoutError:
                        print(f"⚠️  Timeout for {current_timestamp}ms")
                        if attempt < max_retries:
                            print(f"   Retrying with +{retry_increment_ms}ms offset...")
                        continue
                    except Exception as e:
                        print(f"⚠️  Error for {current_timestamp}ms: {str(e)}")
                        if attempt < max_retries:
                            print(f"   Retrying with +{retry_increment_ms}ms offset...")
                        continue

                if not screenshot_taken:
                    print(f"❌ Failed to capture screenshot for second {second} after {max_retries + 1} attempt(s)")
            
            await page.close()
            # await page.video.save_as(self._video_path)
            await context.close()
            await browser.close()
            session_duration = time.time() - start
            print(f"\n✅ Session Duration: {session_duration:.2f} seconds")
            print(f"✅ Total seconds processed: {total_seconds}")
            # No timing offset needed with sequential screenshot approach

            return True
        
        
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
    <style>
      html, body {{padding: 0; border: none; margin: 0; overflow: hidden;}}
      #player-container {{position: relative; width: 100%; height: 100%;}}
      #custom-controls {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(0, 0, 0, 0.8);
        padding: 10px 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        z-index: 9999;
      }}
      #play-pause-btn {{
        background: #fff;
        border: none;
        border-radius: 4px;
        width: 36px;
        height: 36px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }}
      #play-pause-btn:hover {{
        background: #e0e0e0;
      }}
      #progress-container {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }}
      #progress-bar {{
        width: 100%;
        height: 6px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 3px;
        cursor: pointer;
        position: relative;
      }}
      #progress-fill {{
        height: 100%;
        background: #4CAF50;
        border-radius: 3px;
        width: 0%;
        transition: width 0.1s linear;
      }}
      #time-display {{
        color: #fff;
        font-family: monospace;
        font-size: 12px;
        text-align: center;
      }}
    </style>
  </head>
  <body>
    <div id="player-container"></div>
    <div id="custom-controls">
      <button id="play-pause-btn" title="Play/Pause">▶</button>
      <div id="progress-container">
        <div id="progress-bar">
          <div id="progress-fill"></div>
        </div>
        <div id="time-display">00:00 / 00:00</div>
      </div>
    </div>
    <script>
      /*<!--*/
      const events = {events_json};
      /*-->*/

      // Calculate total duration from events
      const totalDuration = events.length > 0 ? events[events.length - 1].timestamp - events[0].timestamp : 0;

      const userConfig = {{width: {self._video_width}, height: {self._video_height}}};
      window.replayer = new rrwebPlayer({{
        events,
        target: document.getElementById('player-container'),
        width: userConfig.width,
        height: userConfig.height,
        props: {{
          ...userConfig,
          events,
          showController: false,  // Disable default controller
          autoPlay: true,
          skipInactive: true,
        }}
      }});

      // Custom controls state
      let isPlaying = true;
      let currentTime = 0;

      // Get DOM elements
      const playPauseBtn = document.getElementById('play-pause-btn');
      const progressBar = document.getElementById('progress-bar');
      const progressFill = document.getElementById('progress-fill');
      const timeDisplay = document.getElementById('time-display');

      // Format time in mm:ss
      function formatTime(ms) {{
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${{String(minutes).padStart(2, '0')}}:${{String(seconds).padStart(2, '0')}}`;
      }}

      // Update progress display
      function updateProgress(time) {{
        currentTime = time;
        const progress = totalDuration > 0 ? (time / totalDuration) * 100 : 0;
        progressFill.style.width = `${{progress}}%`;
        timeDisplay.textContent = `${{formatTime(time)}} / ${{formatTime(totalDuration)}}`;
      }}

      // Play/Pause button handler
      playPauseBtn.addEventListener('click', () => {{
        if (isPlaying) {{
          window.replayer.pause();
          playPauseBtn.textContent = '▶';
          isPlaying = false;
        }} else {{
          window.replayer.play();
          playPauseBtn.textContent = '⏸';
          isPlaying = true;
        }}
      }});

      // Progress bar seek handler
      progressBar.addEventListener('click', (e) => {{
        const rect = progressBar.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const percentage = clickX / rect.width;
        const seekTime = percentage * totalDuration;
        window.replayer.goto(seekTime);
        updateProgress(seekTime);
      }});

      // Event listeners
      window.replayer.addEventListener('start', () => {{
        if (window.onReplayStart) window.onReplayStart();
        playPauseBtn.textContent = '⏸';
        isPlaying = true;
      }});

      window.replayer.addEventListener('finish', () => {{
        if (window.onReplayFinish) window.onReplayFinish();
        playPauseBtn.textContent = '▶';
        isPlaying = false;
      }});

      window.replayer.addEventListener('ui-update-current-time', (payload) => {{
        const time = payload.payload || 0;
        updateProgress(time);
        // Notify Python about time update for synchronization
        if (window.onTimeUpdate) window.onTimeUpdate(time);
      }});
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay")
        return html_content