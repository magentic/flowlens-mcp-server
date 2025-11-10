from typing import List, Optional

from ..dto import dto, dto_timeline
from ..models import enums
from ..utils.timeline.registry import timeline_registry

class TimelineServiceParams:
    def __init__(self, flow_uuid: str):
        self.flow_uuid = flow_uuid

def load_timeline(func):
    async def wrapper(self, *args, **kwargs):
        if not self._overview:
            self._overview = await timeline_registry.get_timeline(self.params.flow_uuid)
            self._timeline = self._overview.timeline
        return await func(self, *args, **kwargs)
    return wrapper
           
class TimelineService:
    _timeline_state = {}
    
    def __init__(self, params: TimelineServiceParams):
        self.params = params
        self._overview: dto_timeline.TimelineOverview = None
        self._timeline: dto_timeline.Timeline = None

    @load_timeline
    async def list_events_within_range(self, start_index: int, 
                                      end_index: int, events_type: Optional[enums.TimelineEventType] = None) -> List[dict]:
        return self._timeline.create_event_summary_for_range(start_index, end_index, events_type)

    @load_timeline
    async def list_events_within_duration(self, start_time: int, end_time: int) -> List[dict]:
        return self._timeline.create_event_summary_for_duration(start_time, end_time)

    @load_timeline
    async def list_all_events(self) -> str:
        return self._timeline.create_events_summary()
    
    @load_timeline
    async def get_full_event_by_index(self, index: int) -> dto.TimelineEventType:
        return self._timeline.get_event_by_index(index)
    
    @load_timeline
    async def get_full_event_by_relative_timestamp(self, relative_timestamp: int) -> dto.TimelineEventType:
        return self._timeline.get_event_by_relative_timestamp(relative_timestamp)
    
    @load_timeline
    async def get_network_request_headers_by_index(self, index: int) -> dict:
        return self._timeline.get_network_request_headers(index)
    
    @load_timeline
    async def get_network_response_headers_by_index(self, index: int) -> dict:
        return self._timeline.get_network_response_headers(index)
    
    @load_timeline
    async def get_network_request_body(self, index: int) -> str:
        return self._timeline.get_network_request_body(index)
    
    @load_timeline
    async def get_network_response_body(self, index: int) -> str:
        return self._timeline.get_network_response_body(index)
    
    @load_timeline
    async def search_events_with_regex(self, pattern: str, event_type:Optional[enums.TimelineEventType] = None) -> str:
        return self._timeline.search_events_with_regex(pattern, event_type)
    
    @load_timeline
    async def search_network_events_with_url_regex(self, url_pattern: str) -> str:
        return self._timeline.search_network_events_with_url_regex(url_pattern)
    

    


    
    
    