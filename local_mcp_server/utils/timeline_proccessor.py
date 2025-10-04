import aiohttp
from ..dto import dto

class TimelineProcessor:
    def __init__(self, url: str):
        self.url = url
        self._timeline: list = None
        self._metadata: dict = None

    async def process(self) -> dto.TimelineOverview:
        await self._load_timeline_data()
        total_recording_duration_ms = self._metadata.get("recording_duration_ms", 0)
        self._process_timeline()
        
        return dto.TimelineOverview(
            total_duration_ms=total_recording_duration_ms,
            total_events_count=len(self._timeline),
            event_type_summaries=[],
            request_status_code_summaries=[])

    def _process_timeline(self):
        requests_map = {}
        processed_timeline = []

        for event in self._timeline:
            event_type = event.get("type")
            correlation_id = event.get("correlation_id", None)

            if ("network_" not in event_type) or (correlation_id is None):
                processed_timeline.append(event)
                continue

            if event_type == "network_request":
                requests_map[correlation_id] = event
                continue

            if (event_type == "network_request") and (correlation_id in requests_map):
                request_event = requests_map[correlation_id]
                merged_event = self._merge_request_response_events(request_event, event)
                processed_timeline.append(merged_event)
                del requests_map[correlation_id]
                continue
            
            processed_timeline.append(event)
                
        # Add remaining unmatched requests (pending)
        for request_event in requests_map.values():
            pending_request = request_event.copy()
            pending_request["type"] = "network_request_pending"
            pending_request["action_type"] = "debugger_request_pending"
            processed_timeline.append(pending_request)

        # Sort by relative_time_ms to maintain chronological order
        processed_timeline.sort(key=lambda x: x.get("relative_time_ms", 0))
        
        self._timeline = processed_timeline

        
    def _merge_request_response_events(self, request_event, response_event) -> dict:
        duration_ms = response_event.get("relative_time_ms", 0) - request_event.get("relative_time_ms", 0)
        correlation_id = response_event.get("correlation_id")
        return {
                    "type": "network_request_response",
                    "action_type": "debugger_request_response",
                    "timestamp": request_event.get("timestamp"),
                    "relative_time_ms": request_event.get("relative_time_ms"),
                    "correlation_id": correlation_id,
                    "request_data": request_event.get("network_request_data", {}),
                    "trace": request_event.get("trace", {}),
                    "response_data": response_event.get("network_response_data", {}),
                    "response_timestamp": response_event.get("timestamp"),
                    "response_relative_time_ms": response_event.get("relative_time_ms"),
                    "duration_ms": duration_ms
                }
    
    async def _load_timeline_data(self):
        data = await self._load_json_from_url(self.url)
        self._timeline = data.get("timeline", [])
        self._metadata = data.get("metadata", {})
        
    @staticmethod
    async def _load_json_from_url(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        raise RuntimeError("Failed to load JSON from URL")