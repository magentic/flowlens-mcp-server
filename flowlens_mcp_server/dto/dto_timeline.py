from typing import List, Optional
from pydantic import BaseModel

from ..models import enums

from .dto import *

class Timeline(BaseModel):
    metadata: dict
    events: List[TimelineEventType]

    def create_events_summary(self) -> str:
        lines = [f"Total Events: {len(self.events)}"]
        for event in self.events:
            lines.append(event.reduce_into_one_line())
        return "\n".join(lines)


    def create_event_summary_for_range(self, start_index: int, end_index: int, events_type: Optional[enums.TimelineEventType] = None) -> str:
        start_index = max(0, start_index)
        end_index = min(len(self.events) - 1, end_index)
        header = f"Events from index {start_index} to {end_index}:\n"
        if events_type:
            header = f"Events of type {events_type.value} from index {start_index} to {end_index}:\n"
        return header + "\n".join(event.reduce_into_one_line() 
                                  for event in self.events[start_index:end_index + 1] if event.type == events_type or events_type is None)

    def create_event_summary_for_duration(self, start_time: int, end_time: int, events_type: Optional[enums.TimelineEventType] = None) -> str:
        events = list(event for event in self.events if start_time <= event.relative_time_ms <= end_time and (event.type == events_type if events_type else True))
        events.sort(key=lambda e: e.relative_time_ms)
        header = f"Events from {start_time}ms to {end_time}ms:\n"
        return header + "\n".join(event.reduce_into_one_line() 
                                  for event in events if event.type == events_type or events_type is None)
    
    def get_event_by_index(self, index: int) -> TimelineEventType:
        if 0 <= index < len(self.events):
            return self.events[index].truncate()
        raise IndexError(f"Event index {index} out of range.")
    
    def get_full_event_by_index(self, index: int) -> TimelineEventType:
        if 0 <= index < len(self.events):
            return self.events[index]
        raise IndexError(f"Event index {index} out of range.")
    
    def get_event_by_relative_timestamp(self, relative_timestamp: int) -> TimelineEventType:
        for event in self.events:
            if event.relative_time_ms == relative_timestamp:
                return event.truncate()
        raise ValueError(f"No event found with relative timestamp {relative_timestamp}ms.")
    
    def get_network_request_headers(self, event_index: int):
        event = self.get_full_event_by_index(event_index)
        if isinstance(event, (NetworkRequestEvent, NetworkRequestWithResponseEvent)):
            return event.network_request_data.headers
        raise TypeError(f"Event with type {event.type} does not have network request headers.")

    def get_network_response_headers(self, event_index: int):
        event = self.get_full_event_by_index(event_index)
        if isinstance(event, NetworkRequestWithResponseEvent):
            return event.network_response_data.headers
        raise TypeError(f"Event with type {event.type} does not have network response headers.")
    
    def get_network_request_body(self, event_index: int):
        event = self.get_full_event_by_index(event_index)
        if isinstance(event, (NetworkRequestEvent, NetworkRequestWithResponseEvent)):
            return event.network_request_data.body
        raise TypeError(f"Event with type {event.type} does not have network request body.")
    
    def get_network_response_body(self, event_index: int):
        event = self.get_full_event_by_index(event_index)
        if isinstance(event, NetworkRequestWithResponseEvent):
            return event.network_response_data.body
        raise TypeError(f"Event with type {event.type} does not have network response body.")

    def search_events_with_regex(self, pattern: str, event_type: Optional[enums.TimelineEventType] = None) -> str:
        header = f"Events matching pattern '{pattern}':\n"
        matches: List[TimelineEventType] = []
        for event in self.events:
            if event.type != event_type:
                    continue
            if event.search_with_regex(pattern):
                matches.append(event)
        header += f"Total Matches: {len(matches)}\n"
        return header + "\n".join([event.reduce_into_one_line() for event in matches])

    def search_network_events_with_url_regex(self, url_pattern: str) -> str:
        header = f"Network events matching URL pattern '{url_pattern}':\n"
        matches: List[TimelineEventType] = []
        for event in self.events:
            if isinstance(event, (NetworkRequestEvent, NetworkRequestWithResponseEvent)):
                if event.search_url_with_regex(url_pattern):
                    matches.append(event.truncate())
        header += f"Total Matches: {len(matches)}\n"
        return header + "\n".join([event.reduce_into_one_line() for event in matches])

  
class TimelineOverview(BaseModel):
    timeline: Timeline
    events_count: int
    duration_ms: int
    event_type_summaries: List[EventTypeSummary]
    http_requests_count: int
    http_request_status_code_summaries: List[RequestStatusCodeSummary]
    http_request_domain_summary: List[NetworkRequestDomainSummary]
    websockets_overview: List[WebSocketOverview]
    
    def __str__(self):
        return (f"TimelineOverview(duration_ms={self.duration_ms}, \n"
                f"events_count={self.events_count}, \n"
                f"network_requests_count={self.network_requests_count}, \n"
                f"event_type_summaries={self.event_type_summaries}, \n"
                f"request_status_code_summaries={self.http_request_status_code_summaries}) \n"
                f"http_request_domain_summary={self.http_request_domain_summary})")