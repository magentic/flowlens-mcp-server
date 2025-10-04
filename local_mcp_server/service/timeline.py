from rpds import List
from ..dto import dto
from ..utils.timeline.registry import timeline_registry

class TimelineServiceParams:
    def __init__(self, flow_id: int):
        self.flow_id = flow_id
        
class TimelineService:
    _timeline_state = {}
    
    def __init__(self, params: TimelineServiceParams):
        self.params = params
    
    async def get_events_within_range(self, start_index: int, end_index: int) -> List[dict]:
        timeline_overview = await timeline_registry.get_timeline(self.params.flow_id)
        timeline: List[dict] = timeline_overview.timeline
        start_index = max(0, start_index)
        end_index = min(len(timeline) - 1, end_index)
        return List(timeline[start_index:end_index + 1])

    async def get_events_within_duration(self, start_time: int, end_time: int) -> List[dict]:
        timeline_overview = await timeline_registry.get_timeline(self.params.flow_id)
        timeline: List[dict] = timeline_overview.timeline
        events = list(event for event in timeline if start_time <= event["relative_time_ms"] <= end_time)
        events.sort(key=lambda e: e["relative_time_ms"])
        return events
    
    
    
    