from typing import List

from flowlens_mcp_server.models import enums
from ...dto import dto


def process_events(events: List[dto.TimelineEventType]) -> List[dto.TimelineEventType]:
    """
    Process timeline events by merging HTTP request and response events.

    This function matches HTTP requests with their corresponding responses based on
    correlation_id, and marks unmatched requests as pending or network-failed.
    The final list is sorted chronologically and re-indexed.

    Args:
        events: List of raw timeline events

    Returns:
        List of processed timeline events with merged HTTP request/response pairs
    """
    requests_map = {}
    processed_timeline = []

    for event in events:
        event_type = event.type

        if event_type not in {enums.TimelineEventType.HTTP_REQUEST,
                                enums.TimelineEventType.HTTP_RESPONSE}:
            processed_timeline.append(event)
            continue
        
        correlation_id = event.correlation_id

        if event_type == enums.TimelineEventType.HTTP_REQUEST:
            requests_map[correlation_id] = event
            continue

        if (event_type == enums.TimelineEventType.HTTP_RESPONSE) and (correlation_id in requests_map):
            request_event = requests_map[correlation_id]
            merged_event = _merge_request_response_events(request_event, event)
            processed_timeline.append(merged_event)
            del requests_map[correlation_id]
            continue

    for request_event in (requests_map.values()):
        request_event: dto.NetworkRequestEvent
        if request_event.is_network_level_failed_request:
            action_type = enums.ActionType.NETWORK_LEVEL_FAILED_REQUEST
        else:
            action_type = enums.ActionType.HTTP_REQUEST_PENDING_RESPONSE

        processed_request = dto.ProcessedHTTPRequestEvent(
                type=enums.TimelineEventType.HTTP_REQUEST,
                action_type=action_type,
                timestamp=request_event.timestamp,
                relative_time_ms=request_event.relative_time_ms,
                index=request_event.index,

                correlation_id=request_event.correlation_id,
                network_request_data=request_event.network_request_data,
                duration_ms=request_event.latency_ms,
            )

        processed_timeline.append(processed_request)

    processed_timeline.sort(key=lambda x: x.relative_time_ms)
    for i, event in enumerate(processed_timeline):
        event.index = i
    return processed_timeline


def _merge_request_response_events(request_event: dto.NetworkRequestEvent, 
                                    response_event: dto.NetworkResponseEvent) -> dto.ProcessedHTTPRequestEvent:
    return dto.ProcessedHTTPRequestEvent(
        type=enums.TimelineEventType.HTTP_REQUEST,
        action_type=enums.ActionType.HTTP_REQUEST_WITH_RESPONSE,
        timestamp=response_event.timestamp,
        relative_time_ms=request_event.relative_time_ms,
        index=request_event.index,

        correlation_id=request_event.correlation_id,
        network_request_data=request_event.network_request_data,
        duration_ms=response_event.relative_time_ms - request_event.relative_time_ms,
        network_response_data=response_event.network_response_data
    )


