from ..dto import dto

class TimelineServiceParams:
    def __init__(self, flow: dto.FullFlow):
        self.flow = flow
        
class TimelineService:
    _timeline_state = {}
    
    def __init__(self, params: TimelineServiceParams):
        self.params = params
        
    
    async def create_overview(self):
        # Placeholder for timeline creation logic
        pass
    
    async def get_events_within_range(self, start_index: int, end_index: int):
        # Placeholder for fetching events within a range
        pass

    async def get_events_within_duration(self, start_time: int, end_time: int):
        # Placeholder for fetching events within a time duration
        pass
    
    
    
    
    
    