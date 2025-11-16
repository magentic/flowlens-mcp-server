import asyncio
import os
import json
import aiofiles
import time
from playwright.async_api import async_playwright
from typing import Union
from ..settings import settings
from ..flow_registry import flow_registry
from ...dto import dto
from .html_builder import HtmlBuilder, BuilderParams

class RrwebRenderer:
    def __init__(self, flow: Union[dto.FullFlow, dto.FlowlensFlow], show_controller: bool = False):
        self._flow = flow
        self._show_controller = show_controller
        self._video_width = 1280
        self._video_height = 720
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._screenshot_dir = f"{self._flow.local_files_data.extracted_dir_path}/screenshots"
            self._snapshot_dir = f"{self._flow.local_files_data.extracted_dir_path}/snapshots"
        else:
            flow_dir = f"{settings.flowlens_save_dir_path}/flows/{self._flow.uuid}"
            self._rrweb_file_path = f"{flow_dir}/rrweb_video.json"
            self._screenshot_dir = f"{flow_dir}/screenshots"
            self._snapshot_dir = f"{flow_dir}/snapshots"
        os.makedirs(self._screenshot_dir, exist_ok=True)
        os.makedirs(self._snapshot_dir, exist_ok=True)
            
        # Timing configurations
        self._time_sync_timeout = 2.0
        self._dom_stability_wait_ms = 150
        self._screenshot_attempt_timeout = 5.0
        self._time_matching_tolerance_ms = 50
        self._evaluate_timeout = 2.0

        # Retry configurations
        self._retry_offsets = [0, 100, -100]
        self._fallback_search_distances = [1]

        # Computed state (to be set during rendering)
        self._video_duration_secs = None
        self._type2_timestamps = None
        self._html_file_path = None
        self._page = None

        # Replay synchronization state
        self._replay_started = None
        self._replay_finished = None
        self._target_timestamp = None
        self._time_reached = None

    def render_rrweb(self):
        asyncio.create_task(self._compile_screenshots())
        
    async def save_snapshot(self, second: int) -> str:
        target_ms = second * 1000
        events = await self._extract_events()
        for event in reversed(events):
            if event['type'] != 2:
                continue
            event_timestamp = event['timestamp']
            event_ms = (event_timestamp - events[0]['timestamp'])
            if event_ms > target_ms:
                continue
            snapshot_path = f"{self._snapshot_dir}/snapshot_sec{second}.json"
            async with aiofiles.open(snapshot_path, mode='w') as f:
                await f.write(json.dumps(event, indent=2))
            return snapshot_path
            
    async def _compile_screenshots(self):
        rrweb_events = await self._extract_events()
        if not rrweb_events:
            raise ValueError("No rrweb events found for the specified time range.")

        # Prepare rendering data and store in member variables
        self._prepare_rendering_data(rrweb_events)

        # Generate HTML and store path
        self._html_file_path = self._create_html_file_with_events(rrweb_events)

        # Record video (uses member variables)
        is_rendering_finished = await self._take_screenshots()
        await flow_registry.set_finished_rendering(self._flow.id, is_rendering_finished)
        os.remove(self._html_file_path)

    async def _extract_events(self):
        if not os.path.exists(self._rrweb_file_path):
            raise FileNotFoundError(f"RRWEB file not found at {self._rrweb_file_path}")
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events

    def _prepare_rendering_data(self, rrweb_events):
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
        builder_params = BuilderParams(
            events=rrweb_events,
            video_width=self._video_width,
            video_height=self._video_height
        )
        html_builder = HtmlBuilder(builder_params)
        html_content = html_builder.build(self._show_controller)
        return self._create_html_file(html_content)

    def _find_nearest_snapshot(self, timestamp: int) -> int:
        candidates = [ts for ts in self._type2_timestamps if ts <= timestamp]
        return candidates[-1] if candidates else self._type2_timestamps[0]

    def _calculate_exact_timestamp(self, second: int) -> int:
        return second * 1000

    async def _setup_browser_context(self, playwright):
        browser = await playwright.chromium.launch()
        context = await browser.new_context(
            viewport={"width": self._video_width, "height": self._video_height},
        )
        self._page = await context.new_page()
        self._page.set_default_timeout(0)
        return browser, context

    async def _setup_replay_synchronization(self):
        # Create events to signal when replay has started and finished
        self._replay_started = asyncio.Event()
        self._replay_finished = asyncio.Event()

        # Time synchronization for seeking
        self._target_timestamp = {"value": 0}  # Using dict to allow modification in closure
        self._time_reached = asyncio.Event()

        # Navigate to blank page first
        await self._page.goto("about:blank")

        # Expose callback functions to the page BEFORE setting content
        await self._page.expose_function("onReplayStart", lambda: self._replay_started.set())
        await self._page.expose_function("onReplayFinish", lambda: self._replay_finished.set())
        await self._page.expose_function("onTimeUpdate", self._on_time_update)
    
    def _on_time_update(self, current_time):
        self._replay_started.set()
        if abs(current_time - self._target_timestamp["value"]) < self._time_matching_tolerance_ms:
            self._time_reached.set()

    async def _initialize_replay_page(self):
        await self._page.goto(f"file://{self._html_file_path}", wait_until="domcontentloaded")
        await self._page.wait_for_function("typeof window.replayer !== 'undefined'", timeout=5000)
        await self._replay_started.wait()

        # Immediately pause the player to take manual control
        await self._page.evaluate("window.replayer.pause()")

        # Inject simple wait function for DOM settling
        await self._page.evaluate(f"window.waitForDOMStability = function() {{ return new Promise(resolve => setTimeout(resolve, {self._dom_stability_wait_ms})); }}")

    async def _cleanup_browser(self, context, browser):
        await self._page.close()
        await context.close()
        await browser.close()

    async def _evaluate_with_timeout(self, script: str):
        return await asyncio.wait_for(
            self._page.evaluate(script),
            timeout=self._evaluate_timeout
        )

    async def _take_screenshot_at_second(self, second: int) -> str:
        screenshot_path = f"{self._screenshot_dir}/screenshot_sec{second}.jpg"
        await self._page.screenshot(path=screenshot_path)
        return screenshot_path

    async def _try_screenshot(self, second: int, current_timestamp: int) -> bool:
        await self._seek_to_timestamp(current_timestamp)
        await self._take_screenshot_at_second(second)
        return True

    async def _seek_to_timestamp(self, timestamp: int) -> bool:
        # Set target timestamp and reset the event
        self._target_timestamp["value"] = timestamp
        self._time_reached.clear()

        # Goto with timeout
        await self._evaluate_with_timeout(
            f"window.replayer.goto({timestamp})"
        )

        # Wait for player to reach the target timestamp
        await asyncio.wait_for(self._time_reached.wait(), timeout=self._time_sync_timeout)

        # Wait for DOM stability
        await self._evaluate_with_timeout(
            "window.waitForDOMStability()"
        )

        return True

    async def _attempt_snapshot_recovery(self, second: int, current_timestamp: int) -> bool:
        nearest_snapshot = self._find_nearest_snapshot(current_timestamp)
        await self._seek_to_timestamp(nearest_snapshot)
        await self._seek_to_timestamp(current_timestamp)
        await self._take_screenshot_at_second(second)
        return True

    async def _try_capture_with_retries(self, second: int) -> bool:
        exact_timestamp = self._calculate_exact_timestamp(second)

        screenshot_taken = False
        used_snapshot_recovery = False

        for attempt, offset in enumerate(self._retry_offsets):
            current_timestamp = exact_timestamp + offset

            try:
                # Overall timeout for entire attempt
                success = await asyncio.wait_for(
                    self._try_screenshot(second, current_timestamp),
                    timeout=self._screenshot_attempt_timeout
                )
                if success:
                    screenshot_taken = True
                    break  # Success! Move to next second

            except asyncio.TimeoutError:
                if attempt < len(self._retry_offsets) - 1:
                    continue
                continue

            except Exception:
                if not used_snapshot_recovery and attempt < len(self._retry_offsets) - 1:
                    used_snapshot_recovery = True
                    try:
                        await self._attempt_snapshot_recovery(second, current_timestamp)
                        screenshot_taken = True
                        break

                    except Exception:
                        pass
                else:
                    if attempt < len(self._retry_offsets) - 1:
                        continue
                continue
        return screenshot_taken

    async def _take_screenshots(self) -> bool:
        async with async_playwright() as p:
            # Setup browser and page
            browser, context = await self._setup_browser_context(p)
            await self._setup_replay_synchronization()
            await self._initialize_replay_page()

            # Capture screenshots for each second
            total_seconds = int(self._video_duration_secs) + 1
            for second in range(total_seconds):
                await self._try_capture_with_retries(second)

            # Cleanup
            await self._cleanup_browser(context, browser)

            return True

    def _create_html_file(self, html_content: str) -> str:
        file_path = os.path.join(self._screenshot_dir, "temp_rrweb_player.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path
