import asyncio
from ...dto import dto_timeline


class TimelineRegistry:
    def __init__(self):
        self._timelines: dict[str, dto_timeline.Timeline] = {}
        self._lock = asyncio.Lock()

    async def register_timeline(self, flow_id: str, timeline: dto_timeline.Timeline) -> bool:
        """
        Register a timeline in the registry.

        Args:
            flow_id: The flow UUID to register the timeline under
            timeline: The timeline to register

        Returns:
            True if timeline was registered successfully, False if already exists
        """
        async with self._lock:
            if flow_id in self._timelines:
                return False
            self._timelines[flow_id] = timeline
            return True

    async def is_registered(self, flow_id: str) -> bool:
        """Check if a timeline is registered for the given flow ID."""
        async with self._lock:
            return flow_id in self._timelines

    async def get_timeline(self, flow_id: str) -> dto_timeline.Timeline:
        """
        Get a registered timeline by flow ID.

        Args:
            flow_id: The flow UUID to look up

        Returns:
            The timeline

        Raises:
            KeyError: If timeline not found
        """
        async with self._lock:
            if flow_id not in self._timelines:
                raise KeyError(f"Timeline for flow ID {flow_id} not found. Must get flow first.")
            return self._timelines[flow_id]


timeline_registry = TimelineRegistry()
