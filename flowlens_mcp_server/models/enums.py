from enum import Enum

class RequestType(Enum):
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    PUT = "PUT"
    DELETE = "DELETE"
    
class ProcessingStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    
class RecordingType(Enum):
    WEBM = "WEBM"
    RRWEB = "RRWEB"
    
class TimelineEventType(Enum):
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"    
    LOCAL_STORAGE = "local_storage"
    SESSION_STORAGE = "session_storage"
    USER_ACTION = "user_action"
    NAVIGATION = "navigation"
    CONSOLE = "console"
    JAVASCRIPT_ERROR = "javascript_error"
    WEBSOCKET = "websocket"
    

class ActionType(Enum):
    HTTP_REQUEST_WITH_RESPONSE = "with_response"
    HTTP_REQUEST_PENDING_RESPONSE = "pending_response"
    NETWORK_LEVEL_FAILED_REQUEST = "network_failure"
    CLICK = "click"
    INPUT = "input"
    SUBMIT = "submit"
    GET = "get"
    SET = "set"
    CLEAR = "clear"
    REMOVE = "remove"
    HISTORY_CHANGE = "history_change"
    PAGE_NAVIGATION = "page_navigation"
    HASH_CHANGE = "hash_change"
    WARNING = "warning"
    ERROR = "error"
    LOG = "log"
    DEBUG = "debug"
    INFO = "info"
    ERROR_CAPTURED = "error_captured"
    CONNECTION_OPENED = "connection_opened"
    HANDSHAKE_REQUEST = "handshake_request"
    HANDSHAKE_RESPONSE = "handshake_response"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    CONNECTION_CLOSED = "connection_closed"
    UNKNOWN = "unknown"

