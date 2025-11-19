import aiofiles
import aiohttp
import json
from abc import ABC, abstractmethod

from ...dto import dto, dto_timeline

from ..logger_setup import Logger

logger = Logger(__name__)


class TimelineLoader(ABC):
    """Abstract base class for loading timeline data."""

    def __init__(self, source: str):
        self._source = source
        self._raw_timeline: list = None
        self._metadata: dict = None

    async def load(self) -> dto_timeline.Timeline:
        """Load and parse timeline data into a Timeline object."""
        await self._load_timeline_data()
        events = []
        for i, event in enumerate(self._raw_timeline):
            event["index"] = i
            mapped_event = self._map_event(event)
            event_dto = TimelineLoader._create_event_dto(mapped_event)
            if event_dto:
                events.append(event_dto)
        return dto_timeline.Timeline(
            metadata=self._metadata,
            events=events)

    @staticmethod
    def _map_event(event):
        """Map event types to unified types (e.g., all console events to 'console')."""
        mapped_event_type = TimelineLoader.map_event_type(event.get("type"))
        event["type"] = mapped_event_type
        return event

    @staticmethod
    def map_event_type(event_type):
        """
        Note: This mapping should be done on the extension side.
        """
        if event_type == "dom_action":
            return "user_action"
        elif event_type in ["console_debug", "console_log", "console_info", "console_warning", "console_error"]:
            return "console"
        return event_type

    @staticmethod
    def _create_event_dto(event: dict) -> dto_timeline.TimelineEventType:
        """Create a DTO event object from raw event data."""
        try:
            event_type = event.get("type")
            dto_event_class = dto.types_dict.get(event_type)
            if not dto_event_class:
                return None
            return dto_event_class.model_validate(event)
        except Exception as e:
            logger.warning(f"Failed to parse event: {e}, event data: {event}")
            return None

    @abstractmethod
    async def _load_timeline_data(self) -> None:
        """
        Load raw timeline data and populate _raw_timeline and _metadata.

        Must be implemented by subclasses.
        """
        pass


class LocalTimelineLoader(TimelineLoader):
    """Timeline loader for local file system."""

    async def _load_timeline_data(self) -> None:
        """Load timeline data from a local JSON file."""
        async with aiofiles.open(self._source, mode='r') as f:
            content = await f.read()
        data = json.loads(content)
        self._raw_timeline = data.get("timeline", [])
        self._metadata = data.get("metadata", {})


class RemoteTimelineLoader(TimelineLoader):
    """Timeline loader for remote URLs."""

    async def _load_timeline_data(self) -> None:
        """Load timeline data from a remote URL."""
        data = await self._load_json_from_url()
        self._raw_timeline = data.get("timeline", [])
        self._metadata = data.get("metadata", {})

    async def _load_json_from_url(self) -> dict:
        """Fetch and parse JSON data from the timeline URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self._source) as response:
                response.raise_for_status()
                try:
                    return await response.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    text = await response.text()
                    return json.loads(text)
        raise RuntimeError("Failed to load timeline data")


def get_timeline_loader(is_local: bool, source: str) -> TimelineLoader:
    """
    Factory function to create the appropriate timeline loader.

    Args:
        is_local: Whether the timeline is stored locally or remotely
        source: The file path (if local) or URL (if remote) to the timeline data

    Returns:
        LocalTimelineLoader if is_local is True, otherwise RemoteTimelineLoader
    """
    if is_local:
        return LocalTimelineLoader(source)
    return RemoteTimelineLoader(source)
