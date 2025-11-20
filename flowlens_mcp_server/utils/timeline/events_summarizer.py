from collections import defaultdict
from typing import List

from flowlens_mcp_server.models import enums
from ...dto import dto, dto_timeline

class TimelineSummarizer:
    def __init__(self, timeline: dto_timeline.Timeline):
        self.timeline = timeline

    def get_summary(self) -> dto_timeline.TimelineSummary:
        """Process timeline events and return computed summary statistics."""
        total_recording_duration_ms = self.timeline.metadata.get("recording_duration_ms", 0)

        return dto_timeline.TimelineSummary(
            duration_ms=total_recording_duration_ms,
            events_count=len(self.timeline.events),
            http_requests_count=self.count_network_requests(),
            event_type_summaries=self.summarize_event_types(),
            http_request_status_code_summaries=self.summarize_request_status_codes(),
            http_request_domain_summary=self.summarize_request_domains(),
            websockets_overview=self.summarize_websockets()
        )

    def summarize_event_types(self) -> List[dto.EventTypeSummary]:
        count_dict = defaultdict(int)
        for event in self.timeline.events:
            event_type = event.type
            if event_type:
                count_dict[event_type] += 1
        return [dto.EventTypeSummary(event_type=event_type, events_count=count) 
                for event_type, count in count_dict.items()]

    def summarize_request_status_codes(self) -> List[dto.RequestStatusCodeSummary]:
        count_dict = defaultdict(int)
        for event in self.timeline.events:
            if event.type == enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE:
                status_code = event.network_response_data.status
                if status_code:
                    count_dict[status_code] += 1
            if event.type == enums.TimelineEventType.NETWORK_REQUEST_PENDING:
                count_dict["no_response"] += 1
            elif event.type == enums.TimelineEventType.NETWORK_LEVEL_FAILED_REQUEST:
                count_dict["network_failed"] += 1
        return [dto.RequestStatusCodeSummary(status_code=str(status_code), requests_count=count) 
                for status_code, count in count_dict.items()]
    
    def summarize_request_domains(self) -> List[dto.NetworkRequestDomainSummary]:
        count_dict = defaultdict(int)
        request_types = {enums.TimelineEventType.NETWORK_REQUEST, enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE,
                         enums.TimelineEventType.NETWORK_REQUEST_PENDING}
        for event in self.timeline.events:
            if event.type not in request_types:
                continue
            domain = event.network_request_data.domain_name
            if domain:
                count_dict[domain] += 1
        return [dto.NetworkRequestDomainSummary(domain=domain, requests_count=count) 
                for domain, count in count_dict.items()]
        
    def count_network_requests(self) -> int:
        return sum(1 for event in self.timeline.events
                   if event.type in {enums.TimelineEventType.NETWORK_REQUEST, 
                                     enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE})

    def summarize_websockets(self) -> List[dto_timeline.WebSocketOverview]:
        sockets = defaultdict(lambda: dto_timeline.WebSocketOverview(socket_id=""))
        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.WEBSOCKET:
                continue
            socket_id = event.correlation_id
            sockets[socket_id].socket_id = socket_id
            if event.action_type == enums.ActionType.CONNECTION_OPENED:
                sockets[socket_id].url = event.websocket_created_data.url if event.websocket_created_data else None
                sockets[socket_id].opened_at_relative_time_ms = event.relative_time_ms
                sockets[socket_id].opened_event_index = event.index
            elif event.action_type == enums.ActionType.MESSAGE_SENT:
                sockets[socket_id].sent_messages_count += 1
            elif event.action_type == enums.ActionType.MESSAGE_RECEIVED:
                sockets[socket_id].received_messages_count += 1
            elif event.action_type == enums.ActionType.HANDSHAKE_REQUEST:
                sockets[socket_id].handshake_requests_count += 1
            elif event.action_type == enums.ActionType.HANDSHAKE_RESPONSE:
                sockets[socket_id].handshake_responses_count += 1
            elif event.action_type == enums.ActionType.CONNECTION_CLOSED:
                sockets[socket_id].is_open = False
                sockets[socket_id].closed_at_relative_time_ms = event.relative_time_ms
                sockets[socket_id].closure_reason = event.websocket_closed_data.reason if event.websocket_closed_data else None
                sockets[socket_id].closed_event_index = event.index

        return list(sockets.values())