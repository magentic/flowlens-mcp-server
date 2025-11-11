

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
    def __init__(self, flow: dto.FullFlow, show_controller: bool = False):
        self._flow = flow
        self._show_controller = show_controller
        self._video_width = 1280
        self._video_height = 720
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._video_path = self._flow.local_files_data.video_file_path
            self._screenshot_dir = self._flow.local_files_data.extracted_dir_path
        else:
            self._rrweb_file_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/rrweb_video.json"
            self._video_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/video.webm"
            self._screenshot_dir = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}"
    
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

        # Store type2 events for snapshot recovery
        type2_relative_timestamps = [event['timestamp'] - first_event_timestamp for event in type2_events]

        # Generate HTML with or without controller based on flag
        if self._show_controller:
            html_content = self._generate_html_with_controller(rrweb_events)
        else:
            html_content = self._generate_html_without_controller(rrweb_events)
        html_file_path = self._create_html_file(html_content)
        is_rendering_finished = await self._record_rrweb_to_video(html_file_path, exact_seconds, type2_relative_timestamps)
        await flow_registry.set_finished_rendering(self._flow.id, is_rendering_finished)
        
    async def _extract_events(self):
        if not os.path.exists(self._rrweb_file_path):
            raise FileNotFoundError(f"RRWEB file not found at {self._rrweb_file_path}")
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events
    
    async def _record_rrweb_to_video(self, html_file_path: str, exact_seconds: dict, type2_timestamps: List[int]) -> str:
        start = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": self._video_width, "height": self._video_height},
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

            # Load the HTML file with rrweb player
            print("⏳ Loading rrweb player...")
            await page.goto(f"file://{html_file_path}", wait_until="domcontentloaded")
            print("⏳ Waiting for rrweb player to initialize...")
            await page.wait_for_function("typeof window.replayer !== 'undefined'", timeout=5000)
            print("⏳ Waiting for replay to start...")
            await replay_started.wait()
            print("✅ Replay started, player is ready.")

            # Immediately pause the player to take manual control
            await page.evaluate("window.replayer.pause()")

            # Inject simple wait function for DOM settling
            await page.evaluate("window.waitForDOMStability = function() { return new Promise(resolve => setTimeout(resolve, 150)); }")
            print("✅ DOM wait function injected.")

            # Helper function to find nearest snapshot
            def find_nearest_snapshot(timestamp: int) -> int:
                """Find the nearest Type 2 snapshot before the given timestamp."""
                candidates = [ts for ts in type2_timestamps if ts <= timestamp]
                return candidates[-1] if candidates else type2_timestamps[0]

            # Track successful screenshots for fallback
            successful_screenshots = {}

            # Sequential screenshot capture: loop through each second
            total_seconds = len(exact_seconds)

            # Bidirectional retry offsets: try original, then ±100ms, ±200ms, ±300ms, ±500ms
            retry_offsets = [0, 100, -100, 200, -200, 300, -300, 500, -500]

            for second in sorted(exact_seconds.keys()):
                exact_timestamp = exact_seconds[second]
                print(f"\n📍 Second {second}: Starting at exact timestamp {exact_timestamp}ms")

                screenshot_taken = False
                used_snapshot_recovery = False

                # Try each offset
                for attempt, offset in enumerate(retry_offsets):
                    current_timestamp = exact_timestamp + offset
                    timestamp_secs = current_timestamp / 1000.0

                    # Set target timestamp and reset the event
                    target_timestamp["value"] = current_timestamp
                    time_reached.clear()

                    # Log attempt
                    if attempt == 0:
                        print(f"⏱ Attempt {attempt + 1}/{len(retry_offsets)}: Seeking to {timestamp_secs:.2f}s (relative: {current_timestamp}ms)")
                    else:
                        offset_str = f"{offset:+d}ms" if offset != 0 else "0ms"
                        print(f"⏱ Retry {attempt}/{len(retry_offsets) - 1}: Seeking to {timestamp_secs:.2f}s (relative: {current_timestamp}ms, {offset_str} offset)")

                    try:
                        # Wrap entire attempt in a timeout
                        async def try_screenshot():
                            # Goto with timeout
                            await asyncio.wait_for(
                                page.evaluate(f"window.replayer.goto({current_timestamp})"),
                                timeout=1.5
                            )

                            # Wait for player to reach the target timestamp
                            await asyncio.wait_for(time_reached.wait(), timeout=2.0)

                            # Wait for DOM stability
                            await asyncio.wait_for(
                                page.evaluate("window.waitForDOMStability()"),
                                timeout=1.0
                            )

                            # Take screenshot
                            screenshot_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"
                            await page.screenshot(path=screenshot_path)
                            return True

                        # Overall timeout for entire attempt
                        success = await asyncio.wait_for(try_screenshot(), timeout=5.0)
                        if success:
                            print(f"✅ Player reached {current_timestamp}ms")
                            print(f"📸 Captured screenshot for second {second} at {current_timestamp}ms")
                            screenshot_taken = True
                            successful_screenshots[second] = True
                            break  # Success! Move to next second

                    except asyncio.TimeoutError:
                        print(f"⚠️  Timeout for {current_timestamp}ms")
                        if attempt < len(retry_offsets) - 1:
                            print(f"   Retrying with different offset...")
                        continue

                    except Exception as e:
                        error_msg = str(e)
                        print(f"⚠️  Error for {current_timestamp}ms: {error_msg}")

                        # Check if this is a DOM error (insertBefore, Node type errors)
                        is_dom_error = any(keyword in error_msg for keyword in ['insertBefore', 'Node', 'appendChild', 'removeChild'])

                        if is_dom_error and not used_snapshot_recovery and attempt < len(retry_offsets) - 1:
                            print(f"   🔄 DOM error detected, attempting snapshot recovery...")
                            used_snapshot_recovery = True

                            try:
                                # Find nearest snapshot
                                nearest_snapshot = find_nearest_snapshot(current_timestamp)
                                print(f"   📸 Seeking to nearest snapshot at {nearest_snapshot}ms")

                                # Reset to snapshot
                                await asyncio.wait_for(
                                    page.evaluate(f"window.replayer.goto({nearest_snapshot})"),
                                    timeout=1.5
                                )
                                await asyncio.sleep(0.3)  # Allow DOM to stabilize

                                # Now try to seek to target again
                                await asyncio.wait_for(
                                    page.evaluate(f"window.replayer.goto({current_timestamp})"),
                                    timeout=1.5
                                )

                                # Wait for time sync and DOM stability
                                target_timestamp["value"] = current_timestamp
                                time_reached.clear()
                                await asyncio.wait_for(time_reached.wait(), timeout=2.0)
                                await asyncio.wait_for(
                                    page.evaluate("window.waitForDOMStability()"),
                                    timeout=1.0
                                )

                                # Take screenshot
                                screenshot_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"
                                await page.screenshot(path=screenshot_path)
                                print(f"✅ Snapshot recovery successful!")
                                print(f"📸 Captured screenshot for second {second} at {current_timestamp}ms")
                                screenshot_taken = True
                                successful_screenshots[second] = True
                                break

                            except Exception as recovery_error:
                                print(f"   ⚠️  Snapshot recovery failed: {str(recovery_error)}")
                                print(f"   Continuing with next offset...")
                        else:
                            if attempt < len(retry_offsets) - 1:
                                print(f"   Retrying with different offset...")
                        continue

                # If all retries failed, try fallback to adjacent frame
                if not screenshot_taken:
                    print(f"❌ Failed to capture screenshot for second {second} after {len(retry_offsets)} attempt(s)")

                    # Try to find nearest successful screenshot
                    fallback_source = None
                    for distance in [1, 2, 3]:
                        if second - distance in successful_screenshots:
                            fallback_source = second - distance
                            break
                        elif second + distance in successful_screenshots:
                            fallback_source = second + distance
                            break

                    if fallback_source is not None:
                        try:
                            source_path = f"{self._screenshot_dir}/screenshot_sec{fallback_source}.jpg"
                            target_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"

                            # Copy the file
                            import shutil
                            shutil.copy2(source_path, target_path)
                            print(f"📸 Using fallback screenshot from second {fallback_source}")
                            successful_screenshots[second] = True
                        except Exception as copy_error:
                            print(f"⚠️  Failed to copy fallback screenshot: {str(copy_error)}")

            await page.close()
            await context.close()
            await browser.close()
            session_duration = time.time() - start
            print(f"\n✅ Session Duration: {session_duration:.2f} seconds")
            print(f"✅ Total seconds processed: {total_seconds}")
            print(f"✅ Successful screenshots: {len(successful_screenshots)}/{total_seconds}")

            return True
        
    def _create_html_file(self, html_content: str) -> str:
        """
        Create a temporary HTML file with the given content.
        Returns the file path.
        """
        file_path = os.path.join(self._screenshot_dir, "temp_rrweb_player.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📝 Created temporary HTML file at {file_path}")
        return file_path
        
        
    def _generate_html_with_controller(self, events: List) -> str:
        """
        Generate HTML content with rrweb events embedded directly and custom controller.
        Includes play/pause button, progress bar, and time display.
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

        print("📝 Generated HTML content for rrweb replay with controller")
        return html_content

    def _generate_html_without_controller(self, events: List) -> str:
        """
        Generate HTML content with rrweb events embedded directly without custom controller.
        Minimal HTML structure with only the rrweb player, no custom controls.
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
    </style>
  </head>
  <body>
    <div id="player-container"></div>
    <script>
      /*<!--*/
      const events = {events_json};
      /*-->*/

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

      // Event listeners for synchronization with Python
      window.replayer.addEventListener('start', () => {{
        if (window.onReplayStart) window.onReplayStart();
      }});

      window.replayer.addEventListener('finish', () => {{
        if (window.onReplayFinish) window.onReplayFinish();
      }});

      window.replayer.addEventListener('ui-update-current-time', (payload) => {{
        const time = payload.payload || 0;
        // Notify Python about time update for synchronization
        if (window.onTimeUpdate) window.onTimeUpdate(time);
      }});
    </script>
  </body>
</html>"""

        print("📝 Generated HTML content for rrweb replay without controller")
        return html_content