from datetime import datetime
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional, Type, Union
from ..models import enums
from ..utils.settings import settings
from urllib.parse import urlsplit, urlunsplit

class _BaseDTO(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta='iso8601',
    )
    
    @staticmethod
    def _truncate_string(s: str, max_length: Optional[int] = None) -> str:
        if not isinstance(s, (str,)):
            s = str(s)
        if not s:
            return s
        limit = max_length or settings.flowlens_max_string_length
        if isinstance(s, str) and len(s) > limit:
            return s[:limit] + "...(truncated)"
        return s
    
class RequestParams(BaseModel):
    endpoint: str
    payload: Optional[dict] = None
    qparams: Optional[dict] = None
    request_type: enums.RequestType
    response_model: Optional[Type[BaseModel]] = None

class FlowTag(BaseModel):
    id: str
    title: str
    
class FlowTagList(BaseModel):
    tags: List[FlowTag]
    
class FlowComment(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta='iso8601',
    )
    
    flow_id: Optional[str] = None
    video_second: int
    content: str
    id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @model_validator(mode="before")
    def validate_timestamp(cls, values:dict):
        values["video_second"] = max(0, values.get("timestamp"))
        return values

class System(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    users: Optional[List["User"]] = None

class User(BaseModel):
    id: str
    username: str
    email: str
    systems: Optional[List[System]] = None
    auth_id: str

class LocalFilesData(BaseModel):
    zip_file_path: str
    extracted_dir_path: str
    timeline_file_path: str
    video_file_path: Optional[str] = None
    rrweb_file_path: Optional[str] = None
    
class Flow(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta='iso8601',
    )
    id: str
    title: str
    description: Optional[str] = None
    video_duration_ms: int
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: str
    is_local: bool
    system: Optional[System] = []
    tags: Optional[List[FlowTag]] = []
    reporter: Optional[str] = None
    sequence_diagram_status: Optional[enums.ProcessingStatus] = enums.ProcessingStatus.COMPLETED
    is_timeline_uploaded: Optional[bool] = True
    is_video_uploaded: Optional[bool] = True
    has_extended_sequence_diagram: Optional[bool] = False
    comments: Optional[List[FlowComment]] = None
    recording_type: enums.RecordingType
    recording_status: Optional[enums.ProcessingStatus] = enums.ProcessingStatus.COMPLETED
    local_files_data: Optional[LocalFilesData] = Field(None, exclude=True)
    
    @model_validator(mode="before")
    def validate_timestamp(cls, values:dict):
        values["id"] = values.get("flow_id", values.get("id"))
        values["video_duration_ms"] = values.get("recording_duration_ms", values.get("video_duration_ms"))
        recording_type_dict = {
            "RRWEB": enums.RecordingType.RRWEB,
            "WEBM": enums.RecordingType.WEBM
        }
        values["recording_type"] = recording_type_dict.get(values.get("recording_type"))
        return values

class FlowList(BaseModel):
    flows: List[Flow]

class FullFlow(Flow):
    timeline_url: Optional[str] = None
    video_url: Optional[str] = None
    sequence_diagram_url: Optional[str] = None
    extended_sequence_diagram_url: Optional[str] = None
    
    @property
    def are_screenshots_available(self) -> bool:
        if self.video_url:
            return True
        return self.is_local
    
    @property
    def uuid(self) -> str:
        return self.id
    
class DeleteResponse(BaseModel):
    id: str
    success: bool
    message: Optional[str] = None

class FlowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    system_id: str
    tag_ids: Optional[List[int]] = None

class FlowTagCreateUpdate(BaseModel):
    title: str
    system_id: str

class FlowSequenceDiagramResponse(BaseModel):
    flow_id: str
    status: enums.ProcessingStatus
    url: Optional[str] = None
    has_extended_diagram: bool = False
    extended_diagram_url: Optional[str] = None
    
class FlowShareLink(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta='iso8601',
    )
    
    flow_id: str
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
    
class WebSocketOverview(BaseModel):
    socket_id: str
    url: Optional[str] = None
    sent_messages_count: Optional[int] = 0
    received_messages_count: Optional[int] = 0
    is_open: Optional[bool] = True
    opened_at_relative_time_ms: Optional[int] = 0
    opened_event_index: Optional[int] = None
    closed_at_relative_time_ms: Optional[int] = None
    closed_event_index: Optional[int] = None
    closure_reason: Optional[str] = None
    handshake_requests_count: Optional[int] = 0
    handshake_responses_count: Optional[int] = 0

class FlowlensFlow(_BaseDTO):
    uuid: str
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: str
    tags: Optional[List[FlowTag]] = None
    comments: Optional[List[FlowComment]] = None
    reporter: Optional[str] = None
    events_count: int
    duration_ms: int
    event_type_summaries: List[EventTypeSummary]
    http_requests_count: int
    http_request_status_code_summaries: List[RequestStatusCodeSummary]
    http_request_domain_summary: List[NetworkRequestDomainSummary]
    recording_type: enums.RecordingType
    are_screenshots_available: bool
    websockets_overview: List[WebSocketOverview]
    is_local: bool
    local_files_data: Optional[LocalFilesData] = Field(None, exclude=True)
    video_url: Optional[str] = Field(None, exclude=True)
    is_rendering_finished: Optional[bool] = Field(None, exclude=True)
    
    def truncate(self):
        copy = self.model_copy(deep=True)
        # if copy.description:
        #     copy.description = self._truncate_string(copy.description)
        for comment in (copy.comments or []):
            comment.content = self._truncate_string(comment.content)
        return copy


class TracingData(_BaseDTO):
    traceparent: Optional[str] = None
    datadog_trace_id: Optional[str] = None
    
    @model_validator(mode="before")
    def validate_traceparent(cls, values:dict):
        values['datadog_trace_id'] = values.get("x-datadog-trace-id", None)
        return values
    
    def reduce_into_one_line(self) -> str:
        line = []
        if self.traceparent:
            line.append(f"trace_id={self.traceparent.split('-')[1]}")
        if self.datadog_trace_id:
            line.append(f"datadog_trace_id={self.datadog_trace_id}")
        return " ".join(line)

    
class BaseNetworkData(_BaseDTO):
    headers: Optional[dict] = None
    body: Optional[str] = None
    trace_headers: Optional[TracingData] = None
    
    def truncate(self):
        copy = self.model_copy(deep=True)
        copy.body = self._truncate_string(copy.body)
        new_headers = {}
        for key, value in (copy.headers or {}).items():
            new_headers[key] = self._truncate_string(value)
        copy.headers = new_headers
        return copy
    
    def reduce_into_one_line(self) -> str:
        line = []
        if self.trace_headers:
            line.append(self.trace_headers.reduce_into_one_line())
        return " ".join(line)


class NetworkRequestData(BaseNetworkData):
    method: str
    url: str
    resource_type: Optional[str] = None
    network_level_err_text: Optional[str] = None
    
    @property
    def domain_name(self) -> str:
        parts = urlsplit(self.url)
        return parts.netloc
    
    def reduce_into_one_line(self) -> str:
        line = [self.method, self._truncate_string(self.url)]
        if self.trace_headers:
            line.append(self.trace_headers.reduce_into_one_line())
        return " ".join(line)

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
        return (f"status_code={self.status}")
    
    @model_validator(mode="before")
    def validate_str_length(cls, values:dict):
        url: str = values.get("request_url")
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif', '.bmp', '.tiff', '.mp4', '.mp3', '.wav', '.avi', '.mov', '.wmv', '.flv', '.mkv')):
            values["body"] = "<binary or media content not shown>"
        values["url"] = cls._truncate_string(url, 2000)
        return values
    

class DomTarget(_BaseDTO):
    src: Optional[str] = None
    textContent: Optional[str] = None
    xpath: str
    type: Optional[str] = None
    

    def reduce_into_one_line(self) -> str:
        items = [
            f"type={self.type or 'unknown'}"
        ]
        if self.textContent or self.src:
            items.append(f"text_content={self._truncate_string(self.textContent or self.src)}")
        return " ".join(items)

class NavigationData(BaseModel):
    url: str
    frame_id: int
    transition_type: str
    
    def reduce_into_one_line(self) -> str:
        return f"{self.url} {self.frame_id} {self.transition_type}"

class LocalStorageData(_BaseDTO):
    key: Optional[str] = None
    value: Optional[str] = None
    
    def reduce_into_one_line(self) -> str:
        items = []
        if self.key:
            items.append(f"key={self._truncate_string(self.key)}")
        if self.value:
            items.append(f"value={self._truncate_string(self.value)}")
        return " ".join(items)

    @model_validator(mode="before")
    def validate_value_length(cls, values:dict):
        value = values.get("value")
        values["value"] = cls._truncate_string(value)
        return values
    

class BaseTimelineEvent(_BaseDTO):
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
    latency_ms: Optional[int] = None
    
    @property
    def is_network_level_failed_request(self) -> bool:
        return self.network_request_data.network_level_err_text is not None

    def search_url_with_regex(self, pattern: str) -> bool:
        is_url_match = re.search(pattern, self.network_request_data.url or "")
        return is_url_match is not None
    
    def search_with_regex(self, pattern: str) -> bool:
        match_obj = super().search_with_regex(pattern)
        match_obj = match_obj or re.search(pattern, self.network_request_data.body or "")
        return match_obj is not None

    def reduce_into_one_line(self) -> str:
        items = [
            super().reduce_into_one_line(),
            self.correlation_id,
            self.network_request_data.reduce_into_one_line()
        ]
        if self.latency_ms is not None:
            items.append(f"latency={self.latency_ms}ms")
        if self.is_network_level_failed_request:
            items.append(f"network_error={self.network_request_data.network_level_err_text}")
        return " ".join(items)

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
        copy = self.model_copy(deep=True)
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
            "keydown_session": enums.ActionType.KEYDOWN_SESSION,
            "submit": enums.ActionType.SUBMIT,
            "scroll": enums.ActionType.SCROLL,
            "input": enums.ActionType.INPUT
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
        action_map = {
            "history_change": enums.ActionType.HISTORY_CHANGE,
            "page_navigation": enums.ActionType.PAGE_NAVIGATION,
            "hash_change": enums.ActionType.HASH_CHANGE
        }
        action = values.get("action_type")
        values["action_type"] = action_map.get(action, enums.ActionType.UNKNOWN)
        return values

class LocalStorageEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
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
    page_url: Optional[str] = None
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

class ConsoleErrorEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
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
    

class ConsoleInfoEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
    console_info_data: ConsoleData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.console_info_data.message)} ")

    @model_validator(mode="before")
    def validate_console_info(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.CONSOLE_INFO
        values['action_type'] = enums.ActionType.INFO_LOGGED
        return values

class ConsoleDebugEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
    console_debug_data: ConsoleData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.console_debug_data.message)} ")

    @model_validator(mode="before")
    def validate_console_debug(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.CONSOLE_DEBUG
        values['action_type'] = enums.ActionType.DEBUG_LOGGED
        return values

class ConsoleLogEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
    console_log_data: ConsoleData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return (f"{base_line} {self._truncate_string(self.console_log_data.message)} ")

    @model_validator(mode="before")
    def validate_console_log(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.CONSOLE_LOG
        values['action_type'] = enums.ActionType.LOG_LOGGED
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
    page_url: Optional[str] = None
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
        if isinstance(s, str) and len(s) > settings.flowlens_max_string_length:
            return s[:settings.flowlens_max_string_length] + "...(truncated)"
        return s

class SessionStorageData(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    
    @model_validator(mode="before")
    def validate_value_length(cls, values:dict):
        value = values.get("value")
        values["value"] = str(value) if value else None
        return values

class SessionStorageEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
    session_storage_data: SessionStorageData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        items = [
            base_line
        ]
        if self.session_storage_data.key:
            items.append(f"key={self._truncate_string(self.session_storage_data.key)}")
        if self.session_storage_data.value:
            items.append(f"value={self._truncate_string(self.session_storage_data.value)}")
        return ' '.join(items)

    @model_validator(mode="before")
    def validate_session_storage(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.SESSION_STORAGE
        actions_map = {
            "set": enums.ActionType.SET,
            "get": enums.ActionType.GET,
            "clear": enums.ActionType.CLEAR,
            "remove": enums.ActionType.REMOVE
        }
        action = values.get("action_type")
        values["action_type"] = actions_map.get(action, None)
        return values

class WebSocketInitiatorData(BaseModel):
    columnNumber: Optional[int] = None
    functionName: Optional[str] = None
    lineNumber: Optional[int] = None
    scriptId: Optional[str] = None
    url: Optional[str] = None

class WebSocketCreatedData(BaseModel):
    url: Optional[str] = None
    initiator_data: Optional[WebSocketInitiatorData] = None
    
    def reduce_into_one_line(self) -> str:
        return f"{self.url or ''}"
    
    @model_validator(mode="before")
    def validate_url_length(cls, values:dict):
        frames = values.get('initiator', {}).get('stack', {}).get('callFrames', [])
        values['initiator_data'] = frames[0] if frames else None
        return values

class WebsocketCreatedEvent(BaseTimelineEvent):
    correlation_id: str
    websocket_created_data: WebSocketCreatedData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return f"{base_line} socket_id={self.correlation_id} {self.websocket_created_data.reduce_into_one_line()}"

    @model_validator(mode="before")
    def validate_websocket_created(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_CREATED
        values['action_type'] = enums.ActionType.CONNECTION_OPENED
        return values

class WebSocketHandshakeData(BaseModel):
    headers: Optional[dict] = None
    status: Optional[int] = None
    
    def reduce_into_one_line(self) -> str:
        return f"status_code={self.status or ''}"
    
class WebSocketHandshakeEvent(BaseTimelineEvent):
    correlation_id: str
    websocket_handshake_data: WebSocketHandshakeData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return f"{base_line} socket_id={self.correlation_id} {self.websocket_handshake_data.reduce_into_one_line()}"

class WebSocketHandshakeRequestEvent(WebSocketHandshakeEvent):
    @model_validator(mode="before")
    def validate_websocket_handshake(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_HANDSHAKE_REQUEST
        values['action_type'] = enums.ActionType.HANDSHAKE_REQUEST
        return values

class WebSocketHandshakeResponseEvent(WebSocketHandshakeEvent):
    @model_validator(mode="before")
    def validate_websocket_handshake(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_HANDSHAKE_RESPONSE
        values['action_type'] = enums.ActionType.HANDSHAKE_RESPONSE
        return values
    

class WebSocketFrameData(_BaseDTO):
    opcode: int
    mask: bool
    payloadData: Optional[str] = None
    payloadLength: Optional[int] = None

    def reduce_into_one_line(self) -> str:
        return f"message={self._truncate_string(self.payloadData, 100)}" if self.payloadData else ""


class WebSocketFrameEvent(BaseTimelineEvent):
    correlation_id: str
    websocket_frame_data: WebSocketFrameData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return f"{base_line} socket_id={self.correlation_id} {self.websocket_frame_data.reduce_into_one_line()}"
    

class WebSocketFrameSentEvent(WebSocketFrameEvent):
    @model_validator(mode="before")
    def validate_websocket_frame_sent(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_FRAME_SENT
        values['action_type'] = enums.ActionType.MESSAGE_SENT
        return values


class WebSocketFrameReceivedEvent(WebSocketFrameEvent):
    @model_validator(mode="before")
    def validate_websocket_frame_received(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_FRAME_RECEIVED
        values['action_type'] = enums.ActionType.MESSAGE_RECEIVED
        return values

class WebSocketClosedData(BaseModel):
    reason: Optional[str] = None

class WebSocketClosedEvent(BaseTimelineEvent):
    correlation_id: str
    websocket_closed_data: WebSocketClosedData
    
    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return f"{base_line} socket_id={self.correlation_id} reason={self.websocket_closed_data.reason or ''}"

    @model_validator(mode="before")
    def validate_websocket_closed(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.WEBSOCKET_CLOSED
        values['action_type'] = enums.ActionType.CONNECTION_CLOSED
        return values
     
TimelineEventType = Union[NetworkRequestEvent, NetworkResponseEvent, NetworkRequestWithResponseEvent,
                         DomActionEvent, NavigationEvent, LocalStorageEvent, ConsoleWarningEvent, ConsoleErrorEvent,
                         JavaScriptErrorEvent, SessionStorageEvent, 
                         WebsocketCreatedEvent, WebSocketHandshakeRequestEvent, WebSocketHandshakeResponseEvent,
                         WebSocketFrameSentEvent, WebSocketFrameReceivedEvent,
                         WebSocketClosedEvent, ConsoleDebugEvent, ConsoleLogEvent, ConsoleInfoEvent]

    
types_dict: dict[str, Type[TimelineEventType]] = {
        enums.TimelineEventType.NETWORK_REQUEST.value: NetworkRequestEvent,
        enums.TimelineEventType.NETWORK_RESPONSE.value: NetworkResponseEvent,
        enums.TimelineEventType.DOM_ACTION.value: DomActionEvent,
        enums.TimelineEventType.NAVIGATION.value: NavigationEvent,
        enums.TimelineEventType.LOCAL_STORAGE.value: LocalStorageEvent,
        enums.TimelineEventType.CONSOLE_WARNING.value: ConsoleWarningEvent,
        enums.TimelineEventType.CONSOLE_ERROR.value: ConsoleErrorEvent,
        enums.TimelineEventType.JAVASCRIPT_ERROR.value: JavaScriptErrorEvent,
        enums.TimelineEventType.SESSION_STORAGE.value: SessionStorageEvent,
        enums.TimelineEventType.WEBSOCKET_CREATED.value: WebsocketCreatedEvent,
        enums.TimelineEventType.WEBSOCKET_HANDSHAKE_REQUEST.value: WebSocketHandshakeRequestEvent,
        enums.TimelineEventType.WEBSOCKET_HANDSHAKE_RESPONSE.value: WebSocketHandshakeResponseEvent,
        enums.TimelineEventType.WEBSOCKET_FRAME_SENT.value: WebSocketFrameSentEvent,
        enums.TimelineEventType.WEBSOCKET_FRAME_RECEIVED.value: WebSocketFrameReceivedEvent,
        enums.TimelineEventType.WEBSOCKET_CLOSED.value: WebSocketClosedEvent,
        enums.TimelineEventType.CONSOLE_DEBUG.value: ConsoleDebugEvent,
        enums.TimelineEventType.CONSOLE_LOG.value: ConsoleLogEvent,
        enums.TimelineEventType.CONSOLE_INFO.value: ConsoleInfoEvent,
        }

class McpVersionResponse(BaseModel):
    version: str
    is_supported: bool
    session_uuid: str
    recommendation: Optional[str] = None
