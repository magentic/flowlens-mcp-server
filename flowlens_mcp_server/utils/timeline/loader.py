import aiofiles
import aiohttp
import json

from ...dto import dto, dto_timeline

from ..logger_setup import Logger

logger = Logger(__name__)

class TimelineLoader:
    def __init__(self, flow: dto.FullFlow):
        self._flow = flow
        self._raw_timeline: list = None
        self._metadata: dict = None
        
    async def load(self) -> dto_timeline.Timeline:
        await self._load_timeline_data()
        events = []
        for i, event in enumerate(self._raw_timeline):
            event["index"] = i
            dto_event = self._create_dto_event(event)
            if dto_event:
                events.append(dto_event)
        return dto_timeline.Timeline(
            metadata=self._metadata,
            events=events)

    def _create_dto_event(self, event: dict) -> dto_timeline.TimelineEventType:
        try:
            event_type = event.get("type")
            dto_event_class = dto.types_dict.get(event_type)
            if not dto_event_class:
                return None
            return dto_event_class.model_validate(event)
        except Exception as e:
            logger.warning(f"Failed to parse event: {e}, event data: {event}")
            return None

    async def _load_timeline_data(self):
        if self._flow.is_local:
            timeline_file_path = self._flow.local_files_data.timeline_file_path
            async with aiofiles.open(timeline_file_path, mode='r') as f:
                content = await f.read()
            data = json.loads(content)
        else:
            data = await self._load_json_from_url()
        self._raw_timeline = data.get("timeline", [])
        self._metadata = data.get("metadata", {})
        
    async def _load_json_from_url(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self._flow.timeline_url) as response:
                response.raise_for_status()
                try:
                    return await response.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    text = await response.text()
                    return json.loads(text)
        raise RuntimeError("Failed to load timeline data")