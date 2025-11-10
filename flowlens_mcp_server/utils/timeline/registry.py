import asyncio
from ...dto import dto, dto_timeline
from .processor import TimelineProcessor


class TimelineRegistry:
    def __init__(self):
        self._timelines: dict[str, dto_timeline.TimelineOverview] = {}
        self._lock = asyncio.Lock()

    async def register_timeline(self, flow: dto.FullFlow) -> dto_timeline.TimelineOverview:
        if await self.is_registered(flow.id):
            return await self.get_timeline(flow.id)
        
        processor = TimelineProcessor(flow)
        timeline = await processor.process()

        async with self._lock:
            self._timelines[flow.id] = timeline
            return timeline
        raise KeyError(f"Failed to register timeline for flow ID {flow.id}.")
    
    async def is_registered(self, flow_id: str) -> bool:
        async with self._lock:
            return flow_id in self._timelines
        return False

    async def get_timeline(self, flow_id: str) -> dto_timeline.TimelineOverview:
        async with self._lock:
            return self._timelines.get(flow_id)
        raise KeyError(f"Timeline for flow ID {flow_id} not found.")


timeline_registry = TimelineRegistry()
