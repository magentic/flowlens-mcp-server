import asyncio
from ...dto import dto

class FlowRegistry:
    def __init__(self):
        self._flows: dict[str, dto.FlowlensFlow] = {}
        self._lock = asyncio.Lock()

    async def register_flow(self, flow: dto.FlowlensFlow):
        """
        Register a flow in the registry.

        Args:
            flow: The FlowlensFlow to register

        Returns:
            None
        """
        async with self._lock:
            self._flows[flow.uuid] = flow

    async def get_flow(self, flow_id: str) -> dto.FlowlensFlow:
        """
        Get a registered flow by flow ID.

        Args:
            flow_id: The flow UUID to look up

        Returns:
            The FlowlensFlow

        Raises:
            KeyError: If flow not found
        """
        async with self._lock:
            flow = self._flows.get(flow_id)
            if not flow:
                raise KeyError(f"Flow with ID {flow_id} not found.")
            return flow

    async def is_registered(self, flow_id: str) -> bool:
        """Check if a flow is registered for the given flow ID."""
        async with self._lock:
            return flow_id in self._flows

flow_registry = FlowRegistry()