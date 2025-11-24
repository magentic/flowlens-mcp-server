from typing import List, Optional

from ..dto import dto, dto_timeline
from ..models import enums
from ..utils.timeline.registry import timeline_registry
from ..utils.timeline.loader import get_timeline_loader
from ..utils.timeline.events_processing import process_events
from ..utils.timeline.events_summarizer import TimelineSummarizer

def _load_timeline_from_registry_decorator(func):
    async def wrapper(self, *args, **kwargs):
        if not self.timeline:
            self.timeline = await timeline_registry.get_timeline(self.flow_uuid)
        return await func(self, *args, **kwargs)
    return wrapper

class RegisteredTimelineService:
    def __init__(self, flow_uuid: str):
        self.flow_uuid = flow_uuid
        self.timeline: dto_timeline.Timeline = None

    @_load_timeline_from_registry_decorator
    async def list_events_within_range(self, start_index: int, 
                                      end_index: int, events_type: Optional[enums.TimelineEventType] = None) -> List[dict]:
        return self.timeline.create_event_summary_for_range(start_index, end_index, events_type)

    @_load_timeline_from_registry_decorator
    async def list_events_within_duration(self, start_time: int, end_time: int) -> List[dict]:
        return self.timeline.create_event_summary_for_duration(start_time, end_time)

    @_load_timeline_from_registry_decorator
    async def list_all_events(self) -> str:
        return self.timeline.create_events_summary()
    
    @_load_timeline_from_registry_decorator
    async def get_full_event_by_index(self, index: int) -> dto.TimelineEventType:
        return self.timeline.get_event_by_index(index)
    
    @_load_timeline_from_registry_decorator
    async def get_full_event_by_relative_timestamp(self, relative_timestamp: int) -> dto.TimelineEventType:
        return self.timeline.get_event_by_relative_timestamp(relative_timestamp)
    
    @_load_timeline_from_registry_decorator
    async def get_network_request_headers_by_index(self, index: int) -> dict:
        return self.timeline.get_network_request_headers(index)
    
    @_load_timeline_from_registry_decorator
    async def get_network_response_headers_by_index(self, index: int) -> dict:
        return self.timeline.get_network_response_headers(index)
    
    @_load_timeline_from_registry_decorator
    async def get_network_request_body(self, index: int) -> str:
        return self.timeline.get_network_request_body(index)
    
    @_load_timeline_from_registry_decorator
    async def get_network_response_body(self, index: int) -> str:
        return self.timeline.get_network_response_body(index)
    
    @_load_timeline_from_registry_decorator
    async def search_events_with_regex(self, pattern: str) -> str:
        return self.timeline.search_events_with_regex(pattern)
    
    @_load_timeline_from_registry_decorator
    async def search_network_events_with_url_regex(self, url_pattern: str) -> str:
        return self.timeline.search_network_events_with_url_regex(url_pattern)

async def load_process_and_register_timeline(flow_id: str, is_local: bool, source: str) -> dto_timeline.Timeline:
    """
    Load, process, and register a timeline for a flow.

    This orchestrates the complete timeline initialization pipeline:
    1. Load timeline data from source (local file or remote URL)
    2. Process events (merge HTTP request/response pairs)
    3. Register the processed timeline in the registry

    Args:
        flow_id: The flow UUID to register the timeline under
        is_local: Whether the timeline source is local or remote
        source: File path (if local) or URL (if remote) to the timeline data

    Returns:
        Tuple of (processed Timeline, recording duration in milliseconds)
    """
    timeline_loader = get_timeline_loader(is_local, source)
    timeline = await timeline_loader.load()
    timeline.events = process_events(timeline.events)
    await timeline_registry.register_timeline(flow_id, timeline)
    return timeline

def summarize_timeline(timeline: dto_timeline.Timeline) -> str:
    summarizer = TimelineSummarizer(timeline)
    summary = summarizer.get_summary()
    return summary