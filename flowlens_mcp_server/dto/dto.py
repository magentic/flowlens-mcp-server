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

class McpVersionResponse(BaseModel):
    version: str
    is_supported: bool
    session_uuid: str
    recommendation: Optional[str] = None
    
class RequestParams(BaseModel):
    endpoint: str
    payload: Optional[dict] = None
    qparams: Optional[dict] = None
    request_type: enums.RequestType
    response_model: Optional[Type[BaseModel]] = None

class FlowTag(BaseModel):
    id: str
    title: str
    
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


class LocalFilesData(BaseModel):
    zip_file_path: str
    extracted_dir_path: str
    timeline_file_path: str
    video_file_path: Optional[str] = None
    rrweb_file_path: Optional[str] = None
    
class FullFlow(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta='iso8601',
    )
    id: str
    title: str
    description: Optional[str] = None
    video_duration_ms: int
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: Optional[str] = 'N/A'
    is_local: bool
    tags: Optional[List[FlowTag]] = []
    comments: Optional[List[FlowComment]] = None
    recording_type: enums.RecordingType
    local_files_data: Optional[LocalFilesData] = Field(None, exclude=True)
    anonymous_user_id: Optional[str] = None
    timeline_url: Optional[str] = None
    video_url: Optional[str] = None
    
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
    
    @property
    def is_recording_available(self) -> bool:
        if self.video_url:
            return True
        return self.is_local
    
    @property
    def uuid(self) -> str:
        return self.id


class WebSocketOverview(BaseModel):
    socket_id: str
    url: Optional[str] = None
    frames_sent_count: Optional[int] = 0
    frames_received_count: Optional[int] = 0
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
    system_id: str = Field(exclude=True)
    tags: Optional[List[FlowTag]] = None
    comments: Optional[List[FlowComment]] = None
    recording_type: enums.RecordingType
    is_recording_available: bool
    is_local: bool = Field(exclude=True)
    local_files_data: Optional[LocalFilesData] = Field(None, exclude=True)
    video_url: Optional[str] = Field(None, exclude=True)
    timeline_summary: str


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
        
    def reduce_into_one_line(self) -> str:
        return "UNKNOWN"

    @model_validator(mode="before")
    def validate_request_data(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.HTTP_REQUEST
        values['action_type'] = enums.ActionType.UNKNOWN
        return values

class NetworkResponseEvent(BaseTimelineEvent):
    correlation_id: str
    network_response_data: NetworkResponseData
    
    def reduce_into_one_line(self) -> str:
        return "UNKNOWN"
    
    @model_validator(mode="before")
    def validate_response_data(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.HTTP_RESPONSE
        values['action_type'] = enums.ActionType.UNKNOWN
        return values
    
class ProcessedHTTPRequestEvent(BaseTimelineEvent):
    correlation_id: str
    network_request_data: NetworkRequestData
    duration_ms: Optional[int] = None
    network_response_data: Optional[NetworkResponseData] = None

    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        items = [
            base_line,
            self.network_request_data.reduce_into_one_line(),
            f"correlation_id={self.correlation_id}"
        ]
        if self.network_response_data:
            items.append(self.network_response_data.reduce_into_one_line())
        if self.network_request_data.network_level_err_text:
            items.append(f"network_error={self.network_request_data.network_level_err_text}")
        duration_display = f"{self.duration_ms}ms" if self.duration_ms is not None else "N/A"
        items.append(f"duration={duration_display}")
        return " ".join(items)

    @model_validator(mode="before")
    def validate_processed_request_data(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.HTTP_REQUEST
        return values




class _DomTarget(_BaseDTO):
    id: Optional[str] = None
    parentId: Optional[str] = None
    src: Optional[str] = None
    textContent: Optional[str] = None
    xpath: str
    type: Optional[str] = None
    value: Optional[str] = None

    def reduce_into_one_line(self) -> str:
        items = []
        if self.id:
            items.append(f"elementId={self.id}")
        if self.parentId:
            items.append(f"parentId={self.parentId}")
        if self.type:
            items.append(f"type={self.type}")
        if self.textContent or self.src:
            items.append(f"text_content={self._truncate_string(self.textContent or self.src)}")
        if self.value:
            items.append(f"value={self._truncate_string(self.value)}")
        return " ".join(items)

class UserActionEvent(BaseTimelineEvent):
    page_url: str
    target: _DomTarget
    final_value: Optional[str] = None

    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        parts = [base_line, self._truncate_string(self.page_url), self.target.reduce_into_one_line()]

        if self.final_value:
            parts.append(f"final_value={self._truncate_string(self.final_value)}")

        return " ".join(parts) + " "

    @model_validator(mode="before")
    def validate_user_action(cls, values):
        if not isinstance(values, dict):
            return values
        values['type'] = enums.TimelineEventType.USER_ACTION
        action_map = {
            "click": enums.ActionType.CLICK,
            "input": enums.ActionType.INPUT,
            "submit": enums.ActionType.SUBMIT,
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

class _ConsoleData(BaseModel):
    message: Optional[str] = None
    stack: Optional[str] = None
    userAgent: Optional[str] = None

class ConsoleEvent(BaseTimelineEvent):
    page_url: Optional[str] = None
    console_data: _ConsoleData

    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        return f"{base_line} {self._truncate_string(self.console_data.message)} "

    @model_validator(mode="before")
    def validate_console(cls, values):
        if not isinstance(values, dict):
            return values

        values['type'] = enums.TimelineEventType.CONSOLE
        values['action_type'] = enums.ActionType(values.get("action_type"))
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

class _WebSocketHandshakeData(BaseModel):
    headers: Optional[dict] = None
    status: Optional[int] = None

    def reduce_into_one_line(self) -> str:
        return f"status_code={self.status or ''}"

class _WebSocketFrameData(_BaseDTO):
    opcode: int
    mask: bool
    payloadData: Optional[str] = None
    payloadLength: Optional[int] = None

    def reduce_into_one_line(self) -> str:
        return f"message={self._truncate_string(self.payloadData, 100)}" if self.payloadData else ""

class _WebSocketClosedData(BaseModel):
    reason: Optional[str] = None

class WebSocketEvent(BaseTimelineEvent):
    correlation_id: str
    websocket_created_data: Optional[WebSocketCreatedData] = None
    websocket_handshake_data: Optional[_WebSocketHandshakeData] = None
    websocket_frame_data: Optional[_WebSocketFrameData] = None
    websocket_closed_data: Optional[_WebSocketClosedData] = None

    def reduce_into_one_line(self) -> str:
        base_line = super().reduce_into_one_line()
        socket_id = f"socket_id={self.correlation_id}"

        if self.websocket_created_data:
            return f"{base_line} {socket_id} {self.websocket_created_data.reduce_into_one_line()}"
        elif self.websocket_handshake_data:
            return f"{base_line} {socket_id} {self.websocket_handshake_data.reduce_into_one_line()}"
        elif self.websocket_frame_data:
            return f"{base_line} {socket_id} {self.websocket_frame_data.reduce_into_one_line()}"
        elif self.websocket_closed_data:
            return f"{base_line} {socket_id} reason={self.websocket_closed_data.reason or ''}"
        else:
            return f"{base_line} {socket_id}"

    @model_validator(mode="before")
    def validate_websocket(cls, values):
        if not isinstance(values, dict):
            return values

        values['type'] = enums.TimelineEventType.WEBSOCKET
        values['action_type'] = enums.ActionType(values.get("action_type"))
        
        return values


TimelineEventType = Union[NetworkRequestEvent, NetworkResponseEvent, ProcessedHTTPRequestEvent,
                         UserActionEvent, NavigationEvent, LocalStorageEvent,
                         JavaScriptErrorEvent, SessionStorageEvent,
                         WebSocketEvent, ConsoleEvent]


types_dict: dict[str, Type[TimelineEventType]] = {
        enums.TimelineEventType.HTTP_REQUEST.value: NetworkRequestEvent,
        enums.TimelineEventType.HTTP_RESPONSE.value: NetworkResponseEvent,
        enums.TimelineEventType.USER_ACTION.value: UserActionEvent,
        enums.TimelineEventType.NAVIGATION.value: NavigationEvent,
        enums.TimelineEventType.LOCAL_STORAGE.value: LocalStorageEvent,
        enums.TimelineEventType.JAVASCRIPT_ERROR.value: JavaScriptErrorEvent,
        enums.TimelineEventType.SESSION_STORAGE.value: SessionStorageEvent,
        enums.TimelineEventType.WEBSOCKET.value: WebSocketEvent,
        enums.TimelineEventType.CONSOLE.value: ConsoleEvent,
        }