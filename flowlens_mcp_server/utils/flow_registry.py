import asyncio
from ..dto import dto

class FlowRegistry:
    def __init__(self):
        self._flows: dict[int, dto.FlowlensFlow] = {}
        self._lock = asyncio.Lock()

    async def register_flow(self, flow: dto.FlowlensFlow):
        async with self._lock:
            self._flows[flow.id] = flow

    async def get_flow(self, flow_id: int) -> dto.FlowlensFlow:
        async with self._lock:
            flow = self._flows.get(flow_id)
            if not flow:
                raise KeyError(f"Flow with ID {flow_id} not found.")
            return flow

    async def is_registered(self, flow_id: int) -> bool:
        async with self._lock:
            return flow_id in self._flows

flow_registry = FlowRegistry()