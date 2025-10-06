from typing import List
from fastmcp import Context

from local_mcp_server.models import enums

from ..dto import dto
from ..flowlens_mcp import server_instance
from ..service import flow_lens, timeline


@server_instance.flowlens_mcp.tool
async def list_flows(ctx: Context) -> dto.FlowList:
    """
    List all flows for the authenticated user. the returned flows is a summary of the flow.
    For full details of a flow use get_flow tool. 
    Returns:
        dto.FlowList: List of Flow dto objects.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.list_flows()

@server_instance.flowlens_mcp.tool
async def get_flow(flow_id: int, ctx: Context) -> dto.FlowlensFlow:
    """
    Get a specific full flow by its ID. It contains all flow data including a summary of timeline events 
    e.g. number of events, status codes distribution, events types distribution, network requests domain distribution, etc.
    It is a very important entry point to start investigating a flow.
    Args:
        flow_id (int): The ID of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.get_flow(flow_id)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_duration(flow_id: int, start_relative_time_ms: int, end_relative_time_ms: int, ctx: Context) -> str:
    """
    List timeline events for a specific flow within a duration range. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_relative_time_ms (int): The starting time in milliseconds of the events to retrieve. it is relative to the start of the recording.
        end_relative_time_ms (int): The ending time in milliseconds of the events to retrieve. it is relative to the start of the recording.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_duration(start_relative_time_ms, end_relative_time_ms)

@server_instance.flowlens_mcp.tool
async def get_full_flow_timeline_event_by_index(flow_id: int, event_index: int, ctx: Context) -> dto.TimelineEventType:
    """
    Get a full timeline event for a specific flow by its index. headers and body fields are potentially trucated to avoid very large responses (max 50 chars).
    If you need the full headers and body use get_network_request_full_headers_by_index, get_network_response_full_headers_by_index,
    get_network_request_full_body_by_index, get_network_response_full_body_by_index tools using the flow_id and event_index.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve.
    Returns:
        dto.TimelineEventType: The TimelineEventType dto object which is union of all possible event types (
                                    NetworkRequestEvent, NetworkResponseEvent, NetworkRequestWithResponseEvent,
                                    DomActionEvent, NavigationEvent, LocalStorageEvent)
                                    
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_full_event_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def list_flow_network_timeline_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List network request timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get network request events when you are interested in events that have a response (e.g. successful requests, failed requests) over get_flow_timeline_network_events_within_range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of network request timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE)

@server_instance.flowlens_mcp.tool
async def list_flow_pending_network_timeline_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List pending network request timeline events that don't have a response for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get network request events as it includes events that do not have a response (e.g. pending requests) over get_flow_timeline_network_events_within_range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of network request timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType.NETWORK_REQUEST_PENDING)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_dom_actions_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List DOM action timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get user interactions like clicks, scrolls, form inputs, etc. over get_flow_timeline_events_within_range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of DOM action timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType.DOM_ACTION)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_navigation_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List navigation timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get page navigations over get_flow_timeline_events_within_range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.  
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType.NAVIGATION)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_local_storage_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    List local storage timeline events for a specific flow within a range of indices. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get local storage changes over get_flow_timeline_events_within_range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of local storage timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType.LOCAL_STORAGE)

@server_instance.flowlens_mcp.tool
async def list_flow_timeline_events_within_range_of_type(flow_id: int, start_index: int, end_index: int, event_type: str, ctx: Context) -> str:
    """
    List timeline events for a specific flow within a range of indices and of a specific type. this returns a summary of the events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to get events of a specific type over get_flow_timeline_events_within_range but no tool for that specific type exists e.g. 
    get_flow_timeline_dom_actions_events_within_range, get_flow_timeline_navigation_events_within_range, etc.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
        event_type (str): The type of events to retrieve. must be one of enums.TimelineEventType values.
                            Possible values are:
                                "console_warn" -> console warning events
                                "console_error" -> console error events
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    
    return await timeline_service.list_events_within_range(start_index, end_index, events_type=enums.TimelineEventType(event_type))

@server_instance.flowlens_mcp.tool
async def get_network_request_full_headers_by_index(flow_id: int, event_index: int, ctx: Context) -> dict:
    """
    Get network request full headers for a specific flow by event index. This is important to understand the context of the request.
    so you can see all headers including authentication headers, cookies, user-agent, etc. 
    It helps you understand what the client is dealing with the server. and include tracing headers for debugging.
    which is very important for debugging API calls. and can be used to investigate using observability tools like datadog, jaeger, etc.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve headers for.
    Returns:
        dict: The network request full headers.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_network_request_headers_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_response_full_headers_by_index(flow_id: int, event_index: int, ctx: Context) -> dict:
    """
    Get network response full headers for a specific flow by event index. This is important to understand the context of the response.
    so you can see all headers including content-type, content-encoding, set-cookie, etc. It helps you understand how the server responded to the request.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve headers for.
    Returns:
        dict: The network response full headers.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_network_response_headers_by_index(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_request_full_body_by_index(flow_id: int, event_index: int, ctx: Context) -> str:
    """
    Get network request full body for a specific flow by event index. This is important to understand the context of the request.
    so you can see the full payload sent to the server. This is especially important for POST, PUT, PATCH requests.
    it helps you understand what data is being sent to the server.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve the request body for.
    Returns:
        str: The network request full body.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_network_request_body(event_index)

@server_instance.flowlens_mcp.tool
async def get_network_response_full_body_by_index(flow_id: int, event_index: int, ctx: Context) -> str:
    """
    Get network response full body for a specific flow by event index. This is important to understand the context of the response.
    so you can see the full payload sent by the server. which is very important for debugging API calls. and understanding the data sent by the server.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve the response body for.
    Returns:
        str: The network response full body.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_network_response_body(event_index)


@server_instance.flowlens_mcp.tool
async def search_flow_network_events_with_url_regex(flow_id: int, url_pattern: str, ctx: Context) -> str:
    """
    Search network request timeline events for a specific flow by URL pattern using regex. this returns a summary of the matched events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to search for specific network requests by URL pattern.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        url_pattern (str): The URL pattern to search for using regex.
    Returns:
        str: header + A list of matched network request timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.search_network_events_with_url_regex(url_pattern)

@server_instance.flowlens_mcp.tool
async def search_flow_events_with_regex(flow_id: int, pattern: str, ctx: Context) -> str:
    """
    Search timeline events for a specific flow by pattern using regex. this returns a summary of the matched events in one line each.
    each line starts with the event index, event_type, action_type, relative_timestamp, and the rest is data depending on the event type.
    If you need full details of an event use get_full_flow_timeline_event_by_index tool using the flow_id and event_index.
    Favour this tool to search for specific events by pattern. Use this tool when you want to search the events content.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        pattern (str): The pattern to search for using regex.
    Returns:
        str: header + A list of matched timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.search_events_with_regex(pattern)



async def _extract_timeline_service(flow_id: int, ctx: Context) -> timeline.TimelineService:
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    flow: dto.FlowlensFlow = await service.get_flow(flow_id)
    if not flow:
        raise ValueError(f"Flow with ID {flow_id} not found.")
    timeline_service = timeline.TimelineService(
        timeline.TimelineServiceParams(
            flow_id=flow.id
        )
    )
    
    return timeline_service


