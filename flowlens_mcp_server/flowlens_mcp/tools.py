from typing import Optional

from flowlens_mcp_server.models import enums

from ..dto import dto
from ..flowlens_mcp import server_instance
from ..service.flow_lens import FlowLensService, FlowLensServiceParams
from ..service.timeline import RegisteredTimelineService

@server_instance.flowlens_mcp.tool
async def get_flow_by_uuid(flow_uuid: str) -> dto.FlowlensFlow:
    """
    Get a specific full flow by its UUID. It contains all flow data including a timeline_summary object that has:
    - Total events count
    - Events types distribution
    - Network requests count per domain with status code distribution (showing which domains had which status codes)
    - Console events count grouped by level (log, info, debug, warning, error) when present
    - WebSockets overview
    It is a very important entry point to start investigating a flow.
    because the flow might be still processing and screenshots might become available later.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    service: FlowLensService = _get_flow_service(flow_uuid=flow_uuid)
    return await service.get_flow()

@server_instance.flowlens_mcp.tool
async def get_flow_from_local_zip(flow_zip_path: str) -> dto.FlowlensFlow:
    """
    Get a specific full flow from a local zip file path. It contains all flow data including a timeline_summary object that has:
    - Total events count
    - Events types distribution
    - Network requests count per domain with status code distribution (showing which domains had which status codes)
    - Console events count grouped by level (log, info, debug, warning, error) when present
    - WebSockets overview
    It is a very important entry point to start investigating a flow.
    because the flow might be still processing and screenshots might become available later.
    Args:
        flow_zip_path (string): The local zip file path of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    params = FlowLensServiceParams(local_flow_zip_path=flow_zip_path)
    service = FlowLensService(params)
    return await service.get_flow()

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
    Get a full timeline event for a specific flow by its index.
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
async def list_flow_timeline_events_within_range(flow_uuid: str, start_index: int, end_index: int, event_type: Optional[enums.TimelineEventType] = None) -> str:
    """
    List timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_uuid and event_index.
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
        event_type (enums.TimelineEventType, optional): The type of events to filter by. If not provided, returns all event types.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=event_type)

@server_instance.flowlens_mcp.tool
async def search_flow_events_with_regex(flow_uuid: str, pattern: str) -> str:
    """
    Search timeline events for a specific flow by pattern using regex.
    It works by searching the oneliner of each event which contains the most important information about the event.
    Oneliners are as below:
    - HTTPRequestEvent (HTTP requests: completed, no response received during recording, or failed at network level)
    [index:int] http_request [with_response|pending_response|network_failure] [relative_timestamp:int]ms [POST|PUT|PATCH|GET|DELETE] [url:string] {[trace_id=opentelemtry_trace_id:string]:Optional} {[datadog_trace_id=datadog_trace_id:string]:Optional} correlation_id=[correlation_id:string] {[status_code=[status_code:int]]:Optional for with_response} {[network_error=[error_text:string]]:Optional for network_failure} duration=[duration:int]ms
    - UserActionEvent (user interactions: click, input, submit)
    [index:int] user_action [click|input|submit] [relative_timestamp:int]ms [page_url:string] {[elementId=[id:string]]:Optional} {[parentId=[parent_id:string]]:Optional} {[type=[element_type:string]]:Optional} {[text_content=[text or src]]:Optional} {[value=[value:string]]:Optional} {[final_value=[value:string]]:Optional}
    - NavigationEvent (page navigation)
    [index:int] navigation history_change [relative_timestamp:int]ms [url:string] [frame_id:string] [transition_type:string]
    - LocalStorageEvent (local storage set or get)
    [index:int] local_storage [set|get|remove|clear] [relative_timestamp:int]ms key=[key:string:optional] value=[value:string:optional]
    - SessionStorageEvent (session storage set or get)
    [index:int] session_storage [set|get|remove|clear] [relative_timestamp:int]ms key=[key:string:optional] value=[value:string:optional]
    - ConsoleEvent (console messages: log, info, debug, warning, error)
    [index:int] console [log|info|debug|warning|error] [relative_timestamp:int]ms [message:string]
    - JavaScriptErrorEvent (javascript error message)
    [index:int] javascript_error error_captured [relative_timestamp:int]ms [message:string]
    - WebSocketEvent (websocket events: connection_opened, handshake_request, handshake_response, message_sent, message_received, connection_closed)
    [index:int] websocket [connection_opened|handshake_request|handshake_response|message_sent|message_received|connection_closed] [relative_timestamp:int]ms socket_id=[socket_id:string] {[url:string]:Optional for connection_opened} {[status_code=[status_code:int]]:Optional for handshake} {[message=[message:string]]:Optional for frames} {[reason=[reason:string]]:Optional for connection_closed}
    Args:
        flow_uuid (string): The UUID of the flow to retrieve events for.
        pattern (str): The pattern to search for using regex.
    Returns:
        str: header + A list of matched timeline events in string format one per line.
    """
    timeline_service = await _get_timeline_service(flow_uuid)
    return await timeline_service.search_events_with_regex(pattern)

@server_instance.flowlens_mcp.tool
async def take_flow_screenshot_at_second(flow_uuid: str, second: int) -> str:
    """
        Save a screenshot at a specific timeline relative second for ONLY WEBM flow type. 
        Screenshots are a key tool to capture the visual state of the application at a specific moment in time.
        The screenshot is taken from the video recording of the flow. 
        
        NOTE: For RRWEB flow type, Use take_flow_snapshot_at_second() tool to get full DOM snapshot at that second.
        
        BEST PRACTICE: Always analyze timeline events FIRST before taking screenshots.
        1. Use list_flow_timeline_events_within_range to identify key moments
        2. Look for specific event types: console warnings, errors, user interactions, network failures
        3. Take screenshots at the EXACT relative_time_ms (converted to seconds) of interesting events
        4. For example: if event shows "relative_time_ms:48940", use second=48 or 49
        
        NOTE: You can use arbitrary seconds If you don't have specific events to investigate 
        e.g. when have a flow related to UX so you can take screenshots at multiple intervals to have a visual understanding of the flow.
        
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
    Saves list of RRWEB events starting from the full snapshot followed by all incremental and meta_data events till the input second for flow with recording type RRWEB. 
    RRWEB events are dumped in json file with this format {"rrwebEvents": [<events>]}.
    
    Snapshots are a key tool to capture the full DOM state of the application at a specific moment in time.
    The snapshot is taken from the RRWEB recording of the flow.
    NOTE: Snapshots can only be taken from flows with recording type RRWEB.
    NOTE: For WEBM flow type, Use take_flow_screenshot_at_second() tool to get full DOM snapshot at that second.
    NOTE: Returned path refers a large JSON file containing the RRWEB events nearly ~5MB depending on the recorded website. 
          Consider using **jq** tool to extract specific data from the JSON file.
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

async def _get_timeline_service(flow_uuid: str) -> RegisteredTimelineService:
    _assert_flow_cached(flow_uuid)
    timeline_service = RegisteredTimelineService(flow_uuid=flow_uuid)

    return timeline_service


