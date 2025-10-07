import aiohttp
import json
from typing import List, Type
from ...dto import dto, dto_timeline

class TimelineLoader:
    def __init__(self, url: str):
        self._url = url
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
        types_dict: dict[str, Type[dto_timeline.TimelineEventType]] = {
            "network_request": dto.NetworkRequestEvent,
            "network_response": dto.NetworkResponseEvent,
            "dom_action": dto.DomActionEvent,
            "navigation": dto.NavigationEvent,
            "local_storage": dto.LocalStorageEvent,
            "console_warn": dto.ConsoleWarningEvent,
            "console_error": dto.ConsoleErrorEvent,
            "javascript_error": dto.JavaScriptErrorEvent,
            "session_storage": dto.SessionStorageEvent
        }
        event_type = event.get("type")
        dto_event_class = types_dict.get(event_type)
        if not dto_event_class:
            return None
        return dto_event_class.model_validate(event)

    async def _load_timeline_data(self):
        data = await self._load_json_from_url()
        self._raw_timeline = data.get("timeline", [])
        self._metadata = data.get("metadata", {})
        
    async def _load_json_from_url(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self._url) as response:
                response.raise_for_status()
                try:
                    return await response.json(content_type=None)
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    return json.loads(text)
        raise RuntimeError("Failed to load timeline data")