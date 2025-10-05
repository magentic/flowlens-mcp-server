from typing import List
from fastmcp import Context

from ..dto import dto
from ..flowlens_mcp import server_instance
from ..service import flow_lens, timeline


@server_instance.flowlens_mcp.tool
async def list_flows(ctx: Context) -> dto.FlowList:
    """
    List all flows for the authenticated user.
    Returns:
        dto.FlowList: List of Flow dto objects.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.list_flows()

@server_instance.flowlens_mcp.tool
async def get_flow(flow_id: int, ctx: Context) -> dto.FlowlensFlow:
    """
    Get a specific flow by its ID.
    Args:
        flow_id (int): The ID of the flow to retrieve.
    Returns:
        dto.FlowlensFlow: The FlowlensFlow dto object.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.get_flow(flow_id)

@server_instance.flowlens_mcp.tool
async def delete_flow(flow_id: int, ctx: Context) -> dto.DeleteResponse:
    """
    Delete a specific flow by its ID.
    Args:
        flow_id (int): The ID of the flow to delete.
    Returns:
        dto.DeleteFlowResponse: The response object containing the result of the delete operation.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.delete_flow(flow_id)

@server_instance.flowlens_mcp.tool
async def update_flow(flow_id: int, update_data: dto.FlowUpdate, ctx: Context) -> dto.FullFlow:
    """
    Update a specific flow by its ID.
    Args:
        flow_id (int): The ID of the flow to update.
        update_data (dto.FlowUpdate): The data to update the flow with.
    Returns:
        dto.FullFlow: The updated FullFlow dto object.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.update_flow(flow_id, update_data)

@server_instance.flowlens_mcp.tool
async def list_tags(ctx: Context) -> dto.FlowTagList:
    """
    List all tags.
    Returns:
        dto.FlowTagList: List of FlowTag dto objects.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.list_tags()

@server_instance.flowlens_mcp.tool
async def create_tag(data: dto.FlowTagCreateUpdate, ctx: Context) -> dto.FlowTag:
    """
    Create a new tag.
    Args:
        data (dto.FlowTagCreateUpdate): The data to create the tag with.
    Returns:
        dto.FlowTag: The created FlowTag dto object.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.create_tag(data)

@server_instance.flowlens_mcp.tool
async def update_tag(tag_id: int, data: dto.FlowTagCreateUpdate, ctx: Context) -> dto.FlowTag:
    """
    Update an existing tag.
    Args:
        tag_id (int): The ID of the tag to update.
        data (dto.FlowTagCreateUpdate): The data to update the tag with.
    Returns:
        dto.FlowTag: The updated FlowTag dto object.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.update_tag(tag_id, data)

@server_instance.flowlens_mcp.tool
async def delete_tag(tag_id: int, ctx: Context) -> dto.DeleteResponse:
    """
    Delete a specific tag by its ID.
    Args:
        tag_id (int): The ID of the tag to delete.
    Returns:
        dto.DeleteResponse: The response object containing the result of the delete operation.
    """
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.delete_tag(tag_id)

@server_instance.flowlens_mcp.tool
async def create_shareable_link(flow_id: int, ctx: Context) -> dto.FlowShareLink:
    """
    Create a shareable link for a specific flow by its ID.
    Args:
        flow_id (int): The ID of the flow to create a shareable link for.
    Returns:
        dto.FlowShareLink: The FlowShareLink dto object.
    """    
    service: flow_lens.FlowLensService = ctx.get_state("flowlens_service")
    return await service.create_shareable_link(flow_id)

@server_instance.flowlens_mcp.tool
async def get_flow_timeline_events_within_range(flow_id: int, start_index: int, end_index: int, ctx: Context) -> str:
    """
    Get timeline events for a specific flow within a range of indices.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_index (int): The starting index of the events to retrieve.
        end_index (int): The ending index of the events to retrieve.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_events_within_range(start_index, end_index)

@server_instance.flowlens_mcp.tool
async def get_flow_timeline_events_within_duration(flow_id: int, start_relative_time_ms: int, end_relative_time_ms: int, ctx: Context) -> str:
    """
    Get timeline events for a specific flow within a duration range.
    Args:
        flow_id (int): The ID of the flow to retrieve events for.
        start_relative_time_ms (int): The starting time in milliseconds of the events to retrieve. it is relative to the start of the recording.
        end_relative_time_ms (int): The ending time in milliseconds of the events to retrieve. it is relative to the start of the recording.
    Returns:
        str: header + A list of timeline events in string format one per line.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_events_within_duration(start_relative_time_ms, end_relative_time_ms)

@server_instance.flowlens_mcp.tool
async def get_full_flow_timeline_event_by_index(flow_id: int, event_index: int, ctx: Context) -> dto.TimelineEventType:
    """
    Get a full timeline event for a specific flow by its index.
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
async def get_network_request_full_headers_by_index(flow_id: int, event_index: int, ctx: Context) -> dict:
    """
    Get network request full headers for a specific flow by event index.
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
    Get network response full headers for a specific flow by event index.
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
    Get network request full body for a specific flow by event index.
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
    Get network response full body for a specific flow by event index.
    Args:
        flow_id (int): The ID of the flow to retrieve the event for.
        event_index (int): The index of the event to retrieve the response body for.
    Returns:
        str: The network response full body.
    """
    timeline_service = await _extract_timeline_service(flow_id, ctx)
    return await timeline_service.get_network_response_body(event_index)

async def _extract_timeline_service(flow_id: int, ctx: Context):
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


