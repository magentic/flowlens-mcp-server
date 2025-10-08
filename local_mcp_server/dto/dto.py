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
    
class FlowComment(BaseModel):
    flow_id: int
    timestamp: int
    content: str
    id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
    comments: Optional[List[FlowComment]] = None

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
    comments: Optional[List[FlowComment]] = None
    reporter: Optional[str] = None
    events_count: int
    duration_ms: int
    network_requests_count: int
    event_type_summaries: List[EventTypeSummary]
    request_status_code_summaries: List[RequestStatusCodeSummary]
    network_request_domain_summary: List[NetworkRequestDomainSummary]
    
    def truncate(self):
        copy = self.model_copy()
        if copy.description:
            copy.description = self._truncate_string(copy.description)
        for comment in (copy.comments or []):
            comment.content = self._truncate_string(comment.content)
        return copy
    
    @staticmethod
    def _truncate_string(s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

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
        return f"{self.method} {self._truncate_string(self.url)}"
    
    @model_validator(mode="before")
    def validate_url_length(cls, values:dict):
        url = values.get("url")
        parts = urlsplit(url)
        # remove query params and fragment
        cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        values["url"] = cleaned
        return values
    
    def _truncate_string(self, s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s    

class NetworkResponseData(BaseNetworkData):
    status: int
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    
    def reduce_into_one_line(self) -> str:
        return (f"status_code={self.status}")
    
    @model_validator(mode="before")
    def validate_str_length(cls, values:dict):
        url: str = values.get("request_url")
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif', '.bmp', '.tiff', '.mp4', '.mp3', '.wav', '.avi', '.mov', '.wmv', '.flv', '.mkv')):
            values["body"] = "<binary or media content not shown>"
        values["url"] = cls._truncate_string(url, 2000)
        return values
    
    @staticmethod
    def _truncate_string(s: str, max_length: int=None) -> str:
        if isinstance(s, str) and len(s) > max_length:
            return s[:max_length or settings.max_string_length] + "...(truncated)"
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
        match_obj = super().search_with_regex(pattern)
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
        match_obj = super().search_with_regex(pattern)
        is_url_match = match_obj or re.search(pattern, self.network_request_data.url or "")
        return is_url_match is not None
    
    def search_with_regex(self, pattern: str) -> bool:
        match_obj = super().search_with_regex(pattern)
        match_obj = match_obj or re.search(pattern, self.network_request_data.url or "")
        match_obj = match_obj or re.search(pattern, self.network_request_data.body or "")
        match_obj = match_obj or re.search(pattern, self.network_response_data.body or "")
        return match_obj is not None
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.network_request_data.reduce_into_one_line()} "
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
            "get": enums.ActionType.SET,
            "clear": enums.ActionType.CLEAR,
            "remove": enums.ActionType.REMOVE
        }
        action = values.get("action_type")
        values["action_type"] = actions_map.get(action, None)
        return values

class ConsoleData(BaseModel):
    message: Optional[str] = None
    stack: Optional[str] = None
    userAgent: Optional[str] = None
    
class ConsoleWarningEvent(BaseTimelineEvent):
    page_url: str = None
    console_warn_data: ConsoleData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.console_warn_data.message)} ")

    @model_validator(mode="before")
    def validate_console_warning(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.CONSOLE_WARNING
        values['action_type'] = enums.ActionType.WARNING_LOGGED
        return values
    
    def _truncate_string(self, s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

class ConsoleErrorEvent(BaseTimelineEvent):
    page_url: str = None
    console_error_data: ConsoleData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self.console_error_data.message} ")

    @model_validator(mode="before")
    def validate_console_error(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.CONSOLE_ERROR
        values['action_type'] = enums.ActionType.ERROR_LOGGED
        return values

class JavaScriptErrorData(BaseModel):
    message: Optional[str] = None
    filename: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    error: Optional[str] = None
    stack: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None

class JavaScriptErrorEvent(BaseTimelineEvent):
    page_url: str = None
    javascript_error_data: JavaScriptErrorData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.javascript_error_data.message)} ")

    @model_validator(mode="before")
    def validate_javascript_error(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.JAVASCRIPT_ERROR
        values['action_type'] = enums.ActionType.ERROR_CAPTURED
        return values
    
    def _truncate_string(self, s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

class SessionStorageData(BaseModel):
    key: str
    value: Optional[str] = None

class SessionStorageEvent(BaseTimelineEvent):
    page_url: str = None
    session_storage_data: SessionStorageData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.session_storage_data.key)} {self._truncate_string(self.session_storage_data.value) or ''} ")

    @model_validator(mode="before")
    def validate_session_storage(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.LOCAL_STORAGE
        actions_map = {
            "set": enums.ActionType.SET,
            "get": enums.ActionType.GET,
            "clear": enums.ActionType.CLEAR,
            "remove": enums.ActionType.REMOVE
        }
        action = values.get("action_type")
        values["action_type"] = actions_map.get(action, None)
        return values

    def _truncate_string(self, s: str) -> str:
        if isinstance(s, str) and len(s) > settings.max_string_length:
            return s[:settings.max_string_length] + "...(truncated)"
        return s

TimelineEventType = Union[NetworkRequestEvent, NetworkResponseEvent, NetworkRequestWithResponseEvent,
                         DomActionEvent, NavigationEvent, LocalStorageEvent, ConsoleWarningEvent, ConsoleErrorEvent,
                         JavaScriptErrorEvent, SessionStorageEvent]



    
    