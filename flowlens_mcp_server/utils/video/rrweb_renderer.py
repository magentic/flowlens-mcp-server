

import asyncio
import os
import json
import aiofiles
import time
from playwright.async_api import async_playwright

from ...utils.settings import settings
from ...utils.flow_registry import flow_registry
from ...dto import dto
from .html_builder import HtmlBuilder, BuilderParams

class RrwebRenderer:
    def __init__(self, flow: dto.FullFlow, show_controller: bool = False):
        self._flow = flow
        self._show_controller = show_controller
        self._video_width = 1280
        self._video_height = 720
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._screenshot_dir = self._flow.local_files_data.extracted_dir_path
        else:
            self._rrweb_file_path = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}/rrweb_video.json"
            self._screenshot_dir = f"{settings.flowlens_save_dir_path}/flows/{self._flow.id}"

        # Timing configurations
        self._seek_timeout = 1.5
        self._time_sync_timeout = 2.0
        self._dom_stability_timeout = 1.0
        self._dom_stability_wait_ms = 150
        self._screenshot_attempt_timeout = 5.0
        self._time_matching_tolerance_ms = 50
        self._snapshot_stabilization_wait = 0.3

        # Retry configurations
        self._retry_offsets = [0, 100, -100, 200, -200, 300, -300, 500, -500]
        self._fallback_search_distances = [1, 2, 3]

        # Computed state (to be set during rendering)
        self._video_duration_secs = None
        self._type2_timestamps = None
        self._html_file_path = None

        # Replay synchronization state
        self._replay_started = None
        self._replay_finished = None
        self._target_timestamp = None
        self._time_reached = None
    
    def render_rrweb(self):
        asyncio.create_task(self._render_rrweb())
        
    async def _render_rrweb(self):
        rrweb_events = await self._extract_events()
        if not rrweb_events:
            raise ValueError("No rrweb events found for the specified time range.")

        # Prepare rendering data and store in member variables
        self._prepare_rendering_data(rrweb_events)

        # Generate HTML and store path
        self._html_file_path = self._create_html_file_with_events(rrweb_events)

        # Record video (uses member variables)
        is_rendering_finished = await self._record_rrweb_to_video()
        await flow_registry.set_finished_rendering(self._flow.id, is_rendering_finished)
        
    async def _extract_events(self):
        if not os.path.exists(self._rrweb_file_path):
            raise FileNotFoundError(f"RRWEB file not found at {self._rrweb_file_path}")
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events

    def _prepare_rendering_data(self, rrweb_events):
        """Calculate and store rendering data: type2 timestamps and video duration."""
        first_event_timestamp = rrweb_events[0]['timestamp']

        # Filter for type 2 (FullSnapshot) events
        type2_events = [event for event in rrweb_events if event.get('type') == 2]
        if not type2_events:
            raise ValueError("No type 2 (FullSnapshot) events found in rrweb recording.")

        # Calculate video duration from base timestamp
        base_timestamp = type2_events[0]['timestamp']
        video_duration_ms = rrweb_events[-1]['timestamp'] - base_timestamp
        self._video_duration_secs = video_duration_ms / 1000.0

        # Store type2 relative timestamps for snapshot recovery
        self._type2_timestamps = [event['timestamp'] - first_event_timestamp for event in type2_events]

    def _create_html_file_with_events(self, rrweb_events) -> str:
        """Generate HTML content with rrweb events and create file."""
        builder_params = BuilderParams(
            events=rrweb_events,
            video_width=self._video_width,
            video_height=self._video_height
        )
        html_builder = HtmlBuilder(builder_params)
        html_content = html_builder.build(self._show_controller)
        return self._create_html_file(html_content)

    def _find_nearest_snapshot(self, timestamp: int) -> int:
        """Find the nearest Type 2 snapshot before the given timestamp."""
        candidates = [ts for ts in self._type2_timestamps if ts <= timestamp]
        return candidates[-1] if candidates else self._type2_timestamps[0]

    def _calculate_exact_timestamp(self, second: int) -> int:
        """Calculate the exact timestamp for a given second."""
        return second * 1000

    def _log_attempt(self, attempt: int, total_attempts: int, timestamp: int, offset: int = 0):
        """Log screenshot capture attempt with formatted output."""
        timestamp_secs = timestamp / 1000.0
        if attempt == 0:
            print(f"⏱ Attempt {attempt + 1}/{total_attempts}: Seeking to {timestamp_secs:.2f}s (relative: {timestamp}ms)")
        else:
            offset_str = f"{offset:+d}ms" if offset != 0 else "0ms"
            print(f"⏱ Retry {attempt}/{total_attempts - 1}: Seeking to {timestamp_secs:.2f}s (relative: {timestamp}ms, {offset_str} offset)")

    def _log_capture_result(self, second: int, timestamp: int, success: bool, method: str = "direct"):
        """Log the result of a screenshot capture attempt."""
        if success:
            if method == "direct":
                print(f"✅ Player reached {timestamp}ms")
                print(f"📸 Captured screenshot for second {second} at {timestamp}ms")
            elif method == "snapshot_recovery":
                print(f"✅ Snapshot recovery successful!")
                print(f"📸 Captured screenshot for second {second} at {timestamp}ms")
            elif method == "fallback":
                print(f"📸 Using fallback screenshot from second {timestamp}")
        else:
            print(f"❌ Failed to capture screenshot for second {second}")

    def _print_session_statistics(self, start_time: float, total_seconds: int, successful_count: int):
        """Print final statistics about the rendering session."""
        session_duration = time.time() - start_time
        print(f"\n✅ Session Duration: {session_duration:.2f} seconds")
        print(f"✅ Total seconds processed: {total_seconds}")
        print(f"✅ Successful screenshots: {successful_count}/{total_seconds}")

    async def _setup_browser_context(self, playwright):
        """Initialize browser, context, and page with proper configuration."""
        browser = await playwright.chromium.launch()
        context = await browser.new_context(
            viewport={"width": self._video_width, "height": self._video_height},
        )
        page = await context.new_page()
        page.set_default_timeout(0)
        return browser, context, page

    async def _setup_replay_synchronization(self, page):
        """Setup event listeners and callbacks for replay coordination."""
        # Create events to signal when replay has started and finished
        self._replay_started = asyncio.Event()
        self._replay_finished = asyncio.Event()

        # Time synchronization for seeking
        self._target_timestamp = {"value": 0}  # Using dict to allow modification in closure
        self._time_reached = asyncio.Event()

        def on_time_update(current_time):
            """Called when player time updates. Checks if we've reached the target timestamp."""
            if abs(current_time - self._target_timestamp["value"]) < self._time_matching_tolerance_ms:
                self._time_reached.set()

        # Navigate to blank page first
        await page.goto("about:blank")

        # Expose callback functions to the page BEFORE setting content
        await page.expose_function("onReplayStart", lambda: self._replay_started.set())
        await page.expose_function("onReplayFinish", lambda: self._replay_finished.set())
        await page.expose_function("onTimeUpdate", on_time_update)

    async def _initialize_replay_page(self, page):
        """Load HTML, wait for player, and inject helper functions."""
        print("⏳ Loading rrweb player...")
        await page.goto(f"file://{self._html_file_path}", wait_until="domcontentloaded")
        print("⏳ Waiting for rrweb player to initialize...")
        await page.wait_for_function("typeof window.replayer !== 'undefined'", timeout=5000)
        print("⏳ Waiting for replay to start...")
        await self._replay_started.wait()
        print("✅ Replay started, player is ready.")

        # Immediately pause the player to take manual control
        await page.evaluate("window.replayer.pause()")

        # Inject simple wait function for DOM settling
        await page.evaluate(f"window.waitForDOMStability = function() {{ return new Promise(resolve => setTimeout(resolve, {self._dom_stability_wait_ms})); }}")
        print("✅ DOM wait function injected.")

    async def _cleanup_browser(self, page, context, browser):
        """Close page, context, and browser."""
        await page.close()
        await context.close()
        await browser.close()

    async def _take_screenshot_at_second(self, page, second: int) -> str:
        """Take a screenshot and return the file path."""
        screenshot_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"
        await page.screenshot(path=screenshot_path)
        return screenshot_path

    async def _try_screenshot(self, page, second: int, current_timestamp: int) -> bool:
        """Try to take a screenshot at the given timestamp with timeout.
        Returns True on success."""
        await self._seek_to_timestamp(page, current_timestamp)
        await self._take_screenshot_at_second(page, second)
        return True

    async def _seek_to_timestamp(self, page, timestamp: int) -> bool:
        """Seek to a specific timestamp and wait for stability.
        Returns True on success, raises exception on failure."""
        # Set target timestamp and reset the event
        self._target_timestamp["value"] = timestamp
        self._time_reached.clear()

        # Goto with timeout
        await asyncio.wait_for(
            page.evaluate(f"window.replayer.goto({timestamp})"),
            timeout=self._seek_timeout
        )

        # Wait for player to reach the target timestamp
        await asyncio.wait_for(self._time_reached.wait(), timeout=self._time_sync_timeout)

        # Wait for DOM stability
        await asyncio.wait_for(
            page.evaluate("window.waitForDOMStability()"),
            timeout=self._dom_stability_timeout
        )

        return True

    async def _attempt_snapshot_recovery(self, page, second: int, current_timestamp: int) -> bool:
        """Attempt to recover from DOM errors using snapshot recovery.
        Returns True if screenshot was successfully captured."""
        # Find nearest snapshot
        nearest_snapshot = self._find_nearest_snapshot(current_timestamp)
        print(f"   📸 Seeking to nearest snapshot at {nearest_snapshot}ms")

        # Reset to snapshot
        await asyncio.wait_for(
            page.evaluate(f"window.replayer.goto({nearest_snapshot})"),
            timeout=self._seek_timeout
        )
        await page.evaluate("window.waitForDOMStability()")  # Allow DOM to stabilize

        # Now try to seek to target again
        await asyncio.wait_for(
            page.evaluate(f"window.replayer.goto({current_timestamp})"),
            timeout=self._seek_timeout
        )

        # Wait for time sync and DOM stability
        self._target_timestamp["value"] = current_timestamp
        self._time_reached.clear()
        await asyncio.wait_for(self._time_reached.wait(), timeout=self._time_sync_timeout)
        await asyncio.wait_for(
            page.evaluate("window.waitForDOMStability()"),
            timeout=self._dom_stability_timeout
        )

        # Take screenshot
        await self._take_screenshot_at_second(page, second)
        return True

    def _create_fallback_screenshot(self, second: int, successful_screenshots: dict) -> bool:
        """Copy a nearby successful screenshot as fallback.
        Returns True if fallback was created successfully."""
        # Try to find nearest successful screenshot
        fallback_source = None
        for distance in self._fallback_search_distances:
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
                self._log_capture_result(second, fallback_source, True, "fallback")
                return True
            except Exception as copy_error:
                print(f"⚠️  Failed to copy fallback screenshot: {str(copy_error)}")
        return False

    async def _try_capture_with_retries(self, page, second: int, successful_screenshots: dict) -> bool:
        """Try to capture screenshot with multiple retry offsets and strategies.
        Returns True if screenshot was captured (including fallback)."""
        exact_timestamp = self._calculate_exact_timestamp(second)
        print(f"\n📍 Second {second}: Starting at exact timestamp {exact_timestamp}ms")

        screenshot_taken = False
        used_snapshot_recovery = False

        # Try each offset
        for attempt, offset in enumerate(self._retry_offsets):
            current_timestamp = exact_timestamp + offset

            # Log attempt
            self._log_attempt(attempt, len(self._retry_offsets), current_timestamp, offset)

            try:
                # Overall timeout for entire attempt
                success = await asyncio.wait_for(
                    self._try_screenshot(page, second, current_timestamp),
                    timeout=self._screenshot_attempt_timeout
                )
                if success:
                    self._log_capture_result(second, current_timestamp, True, "direct")
                    screenshot_taken = True
                    successful_screenshots[second] = True
                    break  # Success! Move to next second

            except asyncio.TimeoutError:
                print(f"⚠️  Timeout for {current_timestamp}ms")
                if attempt < len(self._retry_offsets) - 1:
                    print(f"   Retrying with different offset...")
                continue

            except Exception as e:
                error_msg = str(e)
                print(f"⚠️  Error for {current_timestamp}ms: {error_msg}")

                if not used_snapshot_recovery and attempt < len(self._retry_offsets) - 1:
                    print(f"   🔄 DOM error detected, attempting snapshot recovery...")
                    used_snapshot_recovery = True
                    try:
                        await self._attempt_snapshot_recovery(page, second, current_timestamp)
                        self._log_capture_result(second, current_timestamp, True, "snapshot_recovery")
                        screenshot_taken = True
                        successful_screenshots[second] = True
                        break

                    except Exception as recovery_error:
                        print(f"   ⚠️  Snapshot recovery failed: {str(recovery_error)}")
                        print(f"   Continuing with next offset...")
                else:
                    if attempt < len(self._retry_offsets) - 1:
                        print(f"   Retrying with different offset...")
                continue

        # If all retries failed, try fallback to adjacent frame
        if not screenshot_taken:
            print(f"❌ Failed to capture screenshot for second {second} after {len(self._retry_offsets)} attempt(s)")
            if self._create_fallback_screenshot(second, successful_screenshots):
                successful_screenshots[second] = True
                screenshot_taken = True

        return screenshot_taken

    async def _record_rrweb_to_video(self) -> bool:
        """Record rrweb replay to video by capturing screenshots at each second.
        Uses self._html_file_path, self._video_duration_secs, self._type2_timestamps."""
        start = time.time()
        async with async_playwright() as p:
            # Setup browser and page
            browser, context, page = await self._setup_browser_context(p)
            await self._setup_replay_synchronization(page)
            await self._initialize_replay_page(page)

            # Capture screenshots for each second
            successful_screenshots = {}
            total_seconds = int(self._video_duration_secs) + 1
            for second in range(total_seconds):
                await self._try_capture_with_retries(page, second, successful_screenshots)

            # Cleanup
            await self._cleanup_browser(page, context, browser)
            self._print_session_statistics(start, total_seconds, len(successful_screenshots))

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