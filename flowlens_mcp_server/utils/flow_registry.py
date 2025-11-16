import asyncio
from ..dto import dto

class FlowRegistry:
    def __init__(self):
        self._flows: dict[str, dto.FlowlensFlow] = {}
        self._lock = asyncio.Lock()

    async def register_flow(self, flow: dto.FlowlensFlow):
        async with self._lock:
            self._flows[flow.uuid] = flow

    async def get_flow(self, flow_id: str) -> dto.FlowlensFlow:
        async with self._lock:
            flow = self._flows.get(flow_id)
            if not flow:
                raise KeyError(f"Flow with ID {flow_id} not found.")
            return flow

    async def is_registered(self, flow_id: str) -> bool:
        async with self._lock:
            return flow_id in self._flows
        
    async def set_finished_rendering(self, flow_id: str, is_finished: bool):
        async with self._lock:
            flow = self._flows.get(flow_id)
            if not flow:
                raise KeyError(f"Flow with ID {flow_id} not found.")
            flow.is_rendering_finished = is_finished

flow_registry = FlowRegistry()