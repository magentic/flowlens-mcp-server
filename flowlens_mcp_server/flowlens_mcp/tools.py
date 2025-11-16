from typing import List
# from fastmcp import Context

from flowlens_mcp_server.models import enums

from ..dto import dto
from ..flowlens_mcp import server_instance
from ..service.flow_lens import FlowLensService, FlowLensServiceParams
from ..service.timeline import TimelineService, TimelineServiceParams

@server_instance.flowlens_mcp.tool
async def get_flow_by_uuid(flow_uuid: str) -> dto.FlowlensFlow:
    """
    Get a specific full flow by its UUID. It contains all flow data including a summary of timeline events 
    e.g. number of events, status codes distribution, events types distribution, network requests domain distribution, etc.
    It is a very important entry point to start investigating a flow.
    Note: the comments field in the returned flow is truncated to max of 50 characters per comment. If you need full comments use get_flow_full_comments tool.
    Consider running get_flow again if are_screenshots_available is False and recording type is not RRWEB 
    because the flow might be still processing and screenshots might become available later.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    service: FlowLensService = _get_flow_service(flow_uuid=flow_uuid)
    return await service.get_truncated_flow()

@server_instance.flowlens_mcp.tool
async def get_flow_from_local_zip(flow_zip_path: str) -> dto.FlowlensFlow:
    """
    Get a specific full flow from a local zip file path. It contains all flow data including a summary of timeline events 
    e.g. number of events, status codes distribution, events types distribution, network requests domain distribution, etc.
    It is a very important entry point to start investigating a flow.
    Note: the comments field in the returned flow is truncated to max of 50 characters per comment. If you need full comments use get_flow_full_comments tool.
    Consider running get_flow again if are_screenshots_available is False and recording type is not RRWEB 
    because the flow might be still processing and screenshots might become available later.
    Args:
        flow_zip_path (string): The local zip file path of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    params = FlowLensServiceParams(local_flow_zip_path=flow_zip_path)
    service = FlowLensService(params)
    return await service.get_truncated_flow()


@server_instance.flowlens_mcp.tool
async def get_flow_full_comments(flow_uuid: str) -> List[dto.FlowComment]:
    """
    Get all comments for a specific flow. It contains the full content of each comment without truncation.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve comments for.
    Returns:
        List[dto.FlowComment]: A list of FlowComment dto objects.
    """
    service: FlowLensService = _get_cached_flow_service(flow_uuid)
    return await service.get_flow_full_comments()

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_range(flow_uuid: str, start_index: int, end_index: int) -> str:
    """
    List timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_uuid and event_index.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.list_events_within_range(start_index, end_index)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_duration(flow_uuid: str, start_relative_time_ms: int, end_relative_time_ms: int) -> str:
    """
    List timeline events for a specific flow within a duration range. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_uuid and event_index.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        start_relative_time_ms (int): The starting time in milliseconds of the events to retrieve. it is relative to the start of the recording.
        end_relative_time_ms (int): The ending time in milliseconds of the events to retrieve. it is relative to the start of the recording.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.list_events_within_duration(start_relative_time_ms, end_relative_time_ms)

@server_instance.flowlens_mcp.tool
async def get_full_flow_timeline_event_by_index(flow_uuid: str, event_index: int) -> dto.TimelineEventType:
    """
    Get a full timeline event for a specific flow by its index. headers and body fields are potentially trucated to avoid very large responses (max 50 chars).
    If you need the full headers and body use get_network_request_full_headers_by_index, get_network_response_full_headers_by_index,
    get_network_request_full_body_by_index, get_network_response_full_body_by_index tools using the flow_uuid and event_index.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve.
    Returns:
        dto.TimelineEventType: The TimelineEventType dto object which is union of all possible event types (
                                    NetworkRequestEvent, NetworkResponseEvent, NetworkRequestWithResponseEvent,
                                    DomActionEvent, NavigationEvent, LocalStorageEvent)
                                    
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.get_full_event_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_range_of_type(flow_uuid: str, start_index: int, end_index: int, event_type: enums.TimelineEventType) -> str:
    """
    List timeline events for a specific flow within a range of indices and of a specific type. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_uuid and event_index.
    Favour this tool to get events of a specific type over get_flow_timeline_events_within_range but no tool for that specific type exists e.g. 
    get_flow_timeline_dom_actions_events_within_range, get_flow_timeline_navigation_events_within_range, etc.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
        event_type (enums.TimelineEventType): The type of events to retrieve. must be one of enums.TimelineEventType values.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType(event_type))

@server_instance.flowlens_mcp.tool
async def get_network_request_full_headers_by_index(flow_uuid: str, event_index: int) -> dict:
    """
    Get network request full headers for a specific flow by event index. This is important to understand the context of the request.
    so you can see all headers including authentication headers, cookies, user-agent, etc. 
    It helps you understand what the client is dealing with the server. and include tracing headers for debugging.
    which is very important for debugging API calls. and can be used to investigate using observability tools like datadog, jaeger, etc.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve headers for.
    Returns:
        dict: The network request full headers.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.get_network_request_headers_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_response_full_headers_by_index(flow_uuid: str, event_index: int) -> dict:
    """
    Get network response full headers for a specific flow by event index. This is important to understand the context of the response.
    so you can see all headers including content-type, content-encoding, set-cookie, etc. It helps you understand how the server responded to the request.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve headers for.
    Returns:
        dict: The network response full headers.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.get_network_response_headers_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_request_full_body_by_index(flow_uuid: str, event_index: int) -> str:
    """
    Get network request full body for a specific flow by event index. This is important to understand the context of the request.
    so you can see the full payload sent to the server. This is especially important for POST, PUT, PATCH requests.
    it helps you understand what data is being sent to the server.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve the request body for.
    Returns:
        str: The network request full body.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.get_network_request_body(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_response_full_body_by_index(flow_uuid: str, event_index: int) -> str:
    """
    Get network response full body for a specific flow by event index. This is important to understand the context of the response.
    so you can see the full payload sent by the server. which is very important for debugging API calls. and understanding the data sent by the server.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve the response body for.
    Returns:
        str: The network response full body.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.get_network_response_body(event_index)

@server_instance.flowlens_mcp.tool
async def search_flow_events_with_regex(flow_uuid: str, pattern: str, event_type: enums.TimelineEventType) -> str:
    """
    Search timeline events for a specific flow by pattern using regex. 
    It works by searching the oneliner of each event which contains the most important information about the event.
    Oneliners are as below:
    - NetworkRequestWithResponseEvent (network request and response)
    [index:int] network_request_with_response debugger_request_with_response [relative_timestamp:int]ms [POST|PUT|PATCH|GET|DELETE] [url:string] {[trace_id=opentelemtry_trace_id:string]:Optional} {[datadog_trace_id=datadog_trace_id:string]:Optional} status_code=[status_code:int] duration=[duration:int]ms
    - NetworkRequestPending (request sent but no response received yet)
    [index:int] network_request_pending debugger_request_pending [relative_timestamp:int]ms [POST|PUT|PATCH|GET|DELETE] [url:string] {[trace_id=opentelemtry_trace_id:string]:Optional} {[datadog_trace_id=datadog_trace_id:string]:Optional} 
    - NetworkRequestFailedAtNetworkLevel (request failed at network level e.g. DNS failure, connection timeout, etc.)
    [index:int] network_level_failed_request network_level_failed_request [relative_timestamp:int]ms [POST|PUT|PATCH|GET|DELETE] [url:string] {[trace_id=opentelemtry_trace_id:string]:Optional} {[datadog_trace_id=datadog_trace_id:string]:Optional} latency=[latency_ms:int]ms network_error=[error_text:string]
    - DomActionEvent (click, keydown_session, scroll, etc.)
    [index:int] dom_action [click|keydown_session|scroll|etc.] [relative_timestamp:int]ms type=[element_type:string] text_content=[element_text:string or element_src:string:optional] 
    - NavigationEvent (page navigation)
    [index:int] navigation history_change [relative_timestamp:int]ms [url:string] [frame_id:string] [transition_type:string]
    - LocalStorageEvent (local storage set or get)
    [index:int] local_storage [set|get] [relative_timestamp:int]ms key=[key:string:optional] value=[value:string:optional]
    - SessionStorageEvent (session storage set or get)
    [index:int] session_storage [set|get] [relative_timestamp:int]ms key=[key:string:optional] value=[value:string:optional]
    - ConsoleDebugEvent (console debug message)
    [index:int] console_debug debug_logged [relative_timestamp:int]ms [message:string]
    - ConsoleLogEvent (console log message) 
    [index:int] console_log log_logged [relative_timestamp:int]ms [message:string]
    - ConsoleInfoEvent (console info message)
    [index:int] console_info info_logged [relative_timestamp:int]ms [message:string]
    - ConsoleWarningEvent (console warning message)
    [index:int] console_warn warning_logged [relative_timestamp:int]ms [message:string]
    - ConsoleErrorEvent (console error message)
    [index:int] console_error error_logged [relative_timestamp:int]ms [message:string]
    - JavaScriptErrorEvent (javascript error message)
    [index:int] javascript_error error_captured [relative_timestamp:int]ms [message:string]
    - WebSocketCreatedEvent (websocket connection opened)
    [index:int] websocket_created connection_opened [relative_timestamp:int]ms socket_id=[socket_id:string] [[url:string]:Optional]
    - WebSocketHandshakeRequestEvent (websocket handshake request)
    [index:int] websocket_handshake_request handshake_request [relative_timestamp:int]ms socket_id=[socket_id:string] [status_code=[status_code:int]:Optional]
    - WebSocketFrameSentEvent (websocket frame sent)
    [index:int] websocket_frame_sent frame_sent [relative_timestamp:int]ms socket_id=[socket_id:string] [message=[message:string]:Optional]
    - WebSocketFrameReceivedEvent (websocket frame received)
    [index:int] websocket_frame_received frame_received [relative_timestamp:int]ms socket_id=[socket_id:string] [message=[message:string]:Optional]
    - WebSocketClosedEvent (websocket connection closed)
    [index:int] websocket_closed connection_closed [relative_timestamp:int]ms socket_id=[socket_id:string] [reason=[reason:string]:Optional]
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        pattern (str): The pattern to search for using regex.
    Returns:
        str: header + A list of matched timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.search_events_with_regex(pattern, event_type)

@server_instance.flowlens_mcp.tool
async def take_flow_screenshot_at_second(flow_uuid: str, second: int) -> str:
    """
        Save a screenshot at a specific timeline relative second for a specific flow. 
        Screenshots are a key tool to capture the visual state of the application at a specific moment in time.
        The screenshot is taken from the video recording of the flow. 
        
        NOTE: For RRWEB flows, prefer using take_flow_snapshot_at_second() tool to get full DOM snapshot at that second.
        
        BEST PRACTICE: Always analyze timeline events FIRST before taking screenshots.
        1. Use list_flow_timeline_events_within_range to identify key moments
        2. Look for specific event types: console warnings, errors, user interactions, network failures
        3. Take screenshots at the EXACT relative_time_ms (converted to seconds) of interesting events
        4. For example: if event shows "relative_time_ms:48940", use second=48 or 49
        
        NOTE: You can use arbitrary seconds If you don't have specific events to investigate 
        e.g. when have a flow related to UX so you can take screenshots at multiple intervals to have a visual understanding of the flow.
        NOTE: This tool works for both WEBM and RRWEB recorded flows. If you have issue getting a screenshot from RRWEB flow.
        you have two options:
        1. Use take_flow_snapshot_at_second() tool to get full DOM snapshot at specific second. 
        2. Wait for 20 seconds and try again as RRWEB processing might not be complete yet.
        
        WHY: Screenshots are most valuable when tied to specific events rather than arbitrary time intervals.
        This approach helps you understand the exact application state when issues occurred.


        Important Note: The screenshot bottom middle contains a recording UI showing elapsed time. 
        IGNORE that UI element as it is part of the recording state, not the application state.

        Args:
            flow_uuid (string): The UUID of the flow to take the screenshot for.
            second (int): The second to take the screenshot at. 
                            IMPORTANT: Use the relative_time_ms from timeline events, converted to seconds.
                            Example: relative_time_ms:48940 -> second=48 or 49
                            Favour using the exact second of the timeline event you are investigating.
                            
        Returns:
            str: The path to the saved screenshot JPEG image.
    """
    service: FlowLensService = _get_cached_flow_service(flow_uuid)
    return await service.save_screenshot(second)

@server_instance.flowlens_mcp.tool
async def take_flow_snapshot_at_second(flow_uuid: str, second: int) -> str:
    """
    Saves RRWEB full snapshot at specific second in json format for flow with recording type RRWEB.
    Snapshots are a key tool to capture the full DOM state of the application at a specific moment in time.
    The snapshot is taken from the RRWEB recording of the flow.
    NOTE: Snapshots can only be taken from flows with recording type RRWEB.
    NOTE: For RRWEB flows, prefer using this tool to get full DOM snapshot at that second.
    NOTE: If you need a visual screenshot image instead use take_flow_screenshot_at_second()
    Args:
        flow_uuid (string): The UUID of the flow to take the snapshot for.
        second (int): The second to take the snapshot at.
    """
    service: FlowLensService = _get_cached_flow_service(flow_uuid)
    return await service.save_snapshot(second)

def _get_flow_service(flow_uuid: str):
    params = FlowLensServiceParams(flow_uuid=flow_uuid)
    return FlowLensService(params)

def _assert_flow_cached(flow_uuid: str):
    flow_service = _get_flow_service(flow_uuid)
    cached_flow = flow_service.get_cached_flow()
    if not cached_flow:
        raise RuntimeError(f"Flow with id {flow_uuid} not found in cache. Must get the flow first before accessing its timeline.")
        
    
def _get_cached_flow_service(flow_uuid: str) -> FlowLensService:
    _assert_flow_cached(flow_uuid)
    return _get_flow_service(flow_uuid)

async def _get_timeline_service(flow_uuid: str) -> TimelineService:
    _assert_flow_cached(flow_uuid)
    timeline_service = TimelineService(
        TimelineServiceParams(
            flow_uuid=flow_uuid
        )
    )
    return timeline_service


