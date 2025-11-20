from typing import List

from flowlens_mcp_server.models import enums
from ...dto import dto, dto_timeline


def process_events(events: List[dto_timeline.TimelineEventType]) -> List[dto_timeline.TimelineEventType]:
    requests_map = {}
    processed_timeline = []

    for event in events:
        event_type = event.type

        if event_type not in {enums.TimelineEventType.NETWORK_REQUEST,
                                enums.TimelineEventType.NETWORK_RESPONSE}:
            processed_timeline.append(event)
            continue
        
        correlation_id = event.correlation_id

        if event_type == enums.TimelineEventType.NETWORK_REQUEST:
            requests_map[correlation_id] = event
            continue

        if (event_type == enums.TimelineEventType.NETWORK_RESPONSE) and (correlation_id in requests_map):
            request_event = requests_map[correlation_id]
            merged_event = _merge_request_response_events(request_event, event)
            processed_timeline.append(merged_event)
            del requests_map[correlation_id]
            continue
        
            
    # Add remaining unmatched requests (pending)
    for request_event in (requests_map.values()):
        pending_request: dto.NetworkRequestEvent = request_event.model_copy(deep=True)
        if pending_request.is_network_level_failed_request:
            pending_request.type = enums.TimelineEventType.NETWORK_LEVEL_FAILED_REQUEST
            pending_request.action_type = enums.ActionType.NETWORK_LEVEL_FAILED_REQUEST
        else:
            pending_request.type = enums.TimelineEventType.NETWORK_REQUEST_PENDING
            pending_request.action_type = enums.ActionType.DEBUGGER_REQUEST_PENDING
        processed_timeline.append(pending_request)

    # Sort by relative_time_ms to maintain chronological order
    processed_timeline.sort(key=lambda x: x.relative_time_ms)
    for i, event in enumerate(processed_timeline):
        event.index = i
    return processed_timeline


def _merge_request_response_events(request_event: dto.NetworkRequestEvent, 
                                    response_event: dto.NetworkResponseEvent) -> dto.NetworkRequestWithResponseEvent:
    return dto.NetworkRequestWithResponseEvent(
        type=enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE,
        action_type=enums.ActionType.DEBUGGER_REQUEST_WITH_RESPONSE,
        timestamp=response_event.timestamp,
        relative_time_ms=request_event.relative_time_ms,
        index=request_event.index,
        correlation_id=request_event.correlation_id,
        network_request_data=request_event.network_request_data,
        network_response_data=response_event.network_response_data,
        duration_ms=response_event.relative_time_ms - request_event.relative_time_ms
    )


