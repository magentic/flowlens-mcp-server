from datetime import datetime
import re
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Type, Union
from ..models import enums
from ..utils.settings import settings
from urllib.parse import urlsplit, urlunsplit

class RequestParams(BaseModel):
    endpoint: str
    payload: Optional[dict] = None
    request_type: enums.RequestType
    response_model: Optional[Type[BaseModel]] = None

class FlowTag(BaseModel):
    id: int
    title: str
    
class FlowTagList(BaseModel):
    tags: List[FlowTag]

class System(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    users: Optional[List["User"]] = None

class User(BaseModel):
    id: int
    username: str
    email: str
    systems: Optional[List[System]] = None
    auth_id: str

class Flow(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    video_duration_ms: int
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: int
    system: Optional[System] = None
    tags: Optional[List[FlowTag]] = None
    reporter: Optional[str] = None
    sequence_diagram_status: enums.FlowSequenceDiagramStatus
    is_timeline_uploaded: bool
    is_video_uploaded: bool
    has_extended_sequence_diagram: bool

class FlowList(BaseModel):
    flows: List[Flow]

class FullFlow(Flow):
    timeline_url: Optional[str] = None
    video_url: Optional[str] = None
    sequence_diagram_url: Optional[str] = None
    extended_sequence_diagram_url: Optional[str] = None
    
class DeleteResponse(BaseModel):
    id: int
    success: bool
    message: Optional[str] = None

class FlowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    system_id: int
    tag_ids: Optional[List[int]] = None

class FlowTagCreateUpdate(BaseModel):
    title: str
    system_id: int

class FlowSequenceDiagramResponse(BaseModel):
    flow_id: int
    status: enums.FlowSequenceDiagramStatus
    url: Optional[str] = None
    has_extended_diagram: bool = False
    extended_diagram_url: Optional[str] = None
    
class FlowShareLink(BaseModel):
    flow_id: int
    token: str
    share_url: str
    expires_at: datetime

class EventTypeSummary(BaseModel):
    event_type: str
    events_count: int

class RequestStatusCodeSummary(BaseModel):
    status_code: str
    requests_count: int

class NetworkRequestDomainSummary(BaseModel):
    domain: str
    requests_count: int
    


class FlowlensFlow(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: int
    tags: Optional[List[FlowTag]] = None
    reporter: Optional[str] = None
    events_count: int
    duration_ms: int
    network_requests_count: int
    event_type_summaries: List[EventTypeSummary]
    request_status_code_summaries: List[RequestStatusCodeSummary]

class BaseNetworkData(BaseModel):
    headers: Optional[dict] = None
    body: Optional[str] = None
    
    def truncate(self):
        copy = self.model_copy()
        copy.body = self._truncate_string(copy.body)
        new_headers = {}
        for key, value in (copy.headers or {}).items():
            new_headers[key] = self._truncate_string(value)
        copy.headers = new_headers
        return copy
    
    @staticmethod
    def _truncate_string(s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s
    
class NetworkRequestData(BaseNetworkData):
    method: str
    url: str
    resource_type: Optional[str] = None
    
    
    @property
    def domain_name(self) -> str:
        parts = urlsplit(self.url)
        return parts.netloc
    
    def reduce_into_one_line(self) -> str:
        return f"{self.method} {self.url}"
    
    @model_validator(mode="before")
    def validate_url_length(cls, values:dict):
        url = values.get("url")
        parts = urlsplit(url)
        # remove query params and fragment
        cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        values["url"] = cleaned
        return values

class NetworkResponseData(BaseNetworkData):
    status: int
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    
    def reduce_into_one_line(self) -> str:
        return (f"{self.status}")
    
    @model_validator(mode="before")
    def validate_str_length(cls, values:dict):
        # TODO: do truncation in the scope of get_event()
        # headers = values.get("headers")
        # new_headers = {}
        # if headers and isinstance(headers, dict):
        #     for key, value in headers.items():
        #         new_headers[key] = cls._truncate_string(value)
        #     values["headers"] = new_headers
        url: str = values.get("request_url")
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif', '.bmp', '.tiff', '.mp4', '.mp3', '.wav', '.avi', '.mov', '.wmv', '.flv', '.mkv')):
            values["body"] = "<binary or media content not shown>"
        return values
    
    @staticmethod
    def _truncate_string(s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

class DomTarget(BaseModel):
    src: Optional[str] = None
    textContent: Optional[str] = None
    xpath: str

    def reduce_into_one_line(self) -> str:
        return f"{self.textContent or self.src or ''}"

class NavigationData(BaseModel):
    url: str
    frame_id: int
    transition_type: str
    
    def reduce_into_one_line(self) -> str:
        return f"{self.url} {self.frame_id} {self.transition_type}"

class LocalStorageData(BaseModel):
    key: str
    value: Optional[str] = None
    
    def reduce_into_one_line(self) -> str:
        return f"{self.key} {self.value or ''}"
    
    @model_validator(mode="before")
    def validate_value_length(cls, values:dict):
        value = values.get("value")
        values["value"] = cls._truncate_string(value)
        return values
    
    @staticmethod
    def _truncate_string(s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s
    
class BaseTimelineEvent(BaseModel):
    type: enums.TimelineEventType
    action_type: enums.ActionType
    timestamp: datetime
    relative_time_ms: int
    index: int
    
    def truncate(self):
        return self
    
    def search_with_regex(self, pattern: str) -> bool:
        match_obj = re.search(pattern, self.reduce_into_one_line() or "")
        return match_obj is not None

    def reduce_into_one_line(self) -> str:
        return f"{self.index} {self.type.value} {self.action_type.value} {self.relative_time_ms}ms"

class NetworkRequestEvent(BaseTimelineEvent):
    correlation_id: str
    network_request_data: NetworkRequestData

    def search_url_with_regex(self, pattern: str) -> bool:
        is_url_match = re.search(pattern, self.network_request_data.url or "")
        return is_url_match is not None
    
    def search_with_regex(self, pattern: str) -> bool:
        match_obj = re.search(pattern, self.network_request_data.url or "")
        match_obj = match_obj or re.search(pattern, self.network_request_data.body or "")
        return match_obj is not None

    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.correlation_id} {self.network_request_data.reduce_into_one_line()}")

    @model_validator(mode="before")
    def validate_request_data(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.NETWORK_REQUEST
        values['action_type'] = enums.ActionType.DEBUGGER_REQUEST
        return values

class NetworkResponseEvent(BaseTimelineEvent):
    correlation_id: str
    network_response_data: NetworkResponseData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.correlation_id} {self.network_response_data.reduce_into_one_line()}")
    
    @model_validator(mode="before")
    def validate_response_data(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.NETWORK_RESPONSE
        values['action_type'] = enums.ActionType.DEBUGGER_RESPONSE
        return values
    
class NetworkRequestWithResponseEvent(BaseTimelineEvent):
    correlation_id: str
    network_request_data: NetworkRequestData
    network_response_data: NetworkResponseData
    duration_ms: int

    def truncate(self):
        copy = self.model_copy()
        copy.network_response_data = copy.network_response_data.truncate()
        copy.network_request_data = copy.network_request_data.truncate()
        return copy
    
    def search_url_with_regex(self, pattern: str) -> bool:
        is_url_match = re.search(pattern, self.network_request_data.url or "")
        return is_url_match is not None
    
    def search_with_regex(self, pattern: str) -> bool:
        match_obj = re.search(pattern, self.network_request_data.url or "")
        match_obj = match_obj or re.search(pattern, self.network_request_data.body or "")
        match_obj = match_obj or re.search(pattern, self.network_response_data.body or "")
        return match_obj is not None
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.correlation_id} {self.network_request_data.reduce_into_one_line()} "
                f"{self.network_response_data.reduce_into_one_line()} duration={self.duration_ms}ms")

    @model_validator(mode="before")
    def validate_request_response_data(cls, values):
        if not isinstance(values, dict):
            return values
            
        values['type'] = enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE
        values['action_type'] = enums.ActionType.DEBUGGER_REQUEST_WITH_RESPONSE
        
        # Only calculate duration_ms if the nested data is still in dict form
        network_response = values.get('network_response_data')
        network_request = values.get('network_request_data')
        
        if isinstance(network_response, dict) and isinstance(network_request, dict):
            values['duration_ms'] = network_response.get('relative_time_ms', 0) - network_request.get('relative_time_ms', 0)
            values['correlation_id'] = network_response.get('correlation_id')
        return values
    
    @staticmethod
    def _truncate_string(s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

class DomActionEvent(BaseTimelineEvent):
    page_url: str
    target: DomTarget
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.target.reduce_into_one_line()} ")
    
    @model_validator(mode="before")
    def validate_dom_action(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.DOM_ACTION
        action_map = {
            "click": enums.ActionType.CLICK,
            "keydown_session": enums.ActionType.KEYDOWN_SESSION
        }
        action = values.get("action_type")
        values["action_type"] = action_map.get(action, enums.ActionType.UNKNOWN)
        return values

class NavigationEvent(BaseTimelineEvent):
    page_url: str
    navigation_data: NavigationData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.page_url}")
    
    @model_validator(mode="before")
    def validate_navigation(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.NAVIGATION
        values['action_type'] = enums.ActionType.HISTORY_CHANGE
        return values

class LocalStorageEvent(BaseTimelineEvent):
    page_url: str
    local_storage_data: LocalStorageData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.local_storage_data.reduce_into_one_line()} ")
    
    @model_validator(mode="before")
    def validate_local_storage(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.LOCAL_STORAGE
        actions_map = {
            "set": enums.ActionType.GET,
            "get": enums.ActionType.SET
        }
        action = values.get("action_type")
        values["action_type"] = actions_map.get(action, None)
        return values


TimelineEventType = Union[NetworkRequestEvent, NetworkResponseEvent, NetworkRequestWithResponseEvent,
                         DomActionEvent, NavigationEvent, LocalStorageEvent]


    
    