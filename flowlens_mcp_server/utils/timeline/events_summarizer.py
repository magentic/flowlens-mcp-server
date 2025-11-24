from collections import defaultdict
from typing import List, Optional

from flowlens_mcp_server.models import enums
from ...dto import dto, dto_timeline

class TimelineSummarizer:
    def __init__(self, timeline: dto_timeline.Timeline):
        self.timeline = timeline

    def get_summary(self) -> str:
        """Process timeline events and return computed summary statistics as a formatted string."""
        total_recording_duration_ms = self.timeline.metadata.get("recording_duration_ms", 0)
        starting_url = self.timeline.metadata.get("starting_url", "N/A")
        network_requests_summary = self.summarize_network_requests()
        console_events_summary = self.summarize_console_events()
        local_storage_summary = self.summarize_local_storage_events()
        session_storage_summary = self.summarize_session_storage_events()
        user_actions_summary = self.summarize_user_actions()
        websockets_overview = self.summarize_websockets()

        navigations_count = sum(
            1 for event in self.timeline.events
            if event.type == enums.TimelineEventType.NAVIGATION
        )

        javascript_errors_count = sum(
            1 for event in self.timeline.events
            if event.type == enums.TimelineEventType.JAVASCRIPT_ERROR
        )

        lines = [
            f"- Total Events: {len(self.timeline.events)}",
            f"- Duration: {total_recording_duration_ms}ms",
            f"- Starting URL: {starting_url}",
            f"- Navigations: {navigations_count}",
        ]

        if javascript_errors_count > 0:
            lines.append(f"- JavaScript Errors: {javascript_errors_count}")


        lines.append("\n## Breakdown for existing timeline events:")

        if network_requests_summary:
            total_requests = sum(sum(status_counts.values()) for status_counts in network_requests_summary.values())
            lines.append(f"\nHTTP Requests by Domain and Status (Total requests = {total_requests}):")
            lines.append("- domain:")
            lines.append("  - status: count")
            for domain, status_counts in network_requests_summary.items():
                lines.append(f"- {domain}:")
                for status, count in status_counts.items():
                    lines.append(f"  - {status}: {count}")

        if console_events_summary:
            lines.append(f"\nConsole Events by Level (Total events = {sum(console_events_summary.values())}):")
            lines.append("- level: count")
            for level, count in console_events_summary.items():
                lines.append(f"- {level}: {count}")

        if local_storage_summary:
            lines.append(f"\nLocal Storage Operations (Total operations = {sum(local_storage_summary.values())}):")
            lines.append("- operation: count")
            for operation, count in local_storage_summary.items():
                lines.append(f"- {operation}: {count}")

        if session_storage_summary:
            lines.append(f"\nSession Storage Operations (Total operations = {sum(session_storage_summary.values())}):")
            lines.append("- operation: count")
            for operation, count in session_storage_summary.items():
                lines.append(f"- {operation}: {count}")

        if user_actions_summary:
            lines.append(f"\nUser Actions (Total actions = {sum(user_actions_summary.values())}):")
            lines.append("- action: count")
            for action, count in user_actions_summary.items():
                lines.append(f"- {action}: {count}")

        if websockets_overview:
            lines.append(f"\nWebSockets Overview (Total connections = {len(websockets_overview)}):")
            for ws in websockets_overview:
                lines.append(f"- Socket ID: {ws.socket_id}")
                if ws.url:
                    lines.append(f"  - URL: {ws.url}")
                lines.append(f"  - Status: {'Open' if ws.is_open else 'Closed'}")
                lines.append(f"  - Frames Sent: {ws.frames_sent_count}")
                lines.append(f"  - Frames Received: {ws.frames_received_count}")
                if ws.opened_at_relative_time_ms is not None:
                    lines.append(f"  - Opened At: {ws.opened_at_relative_time_ms}ms")
                if ws.closed_at_relative_time_ms is not None:
                    lines.append(f"  - Closed At: {ws.closed_at_relative_time_ms}ms")
                if ws.closure_reason:
                    lines.append(f"  - Closure Reason: {ws.closure_reason}")


        missing_event_types = []
        if not network_requests_summary:
            missing_event_types.append("HTTP requests")
        if not console_events_summary:
            missing_event_types.append("console events")
        if not local_storage_summary:
            missing_event_types.append("local storage events")
        if not session_storage_summary:
            missing_event_types.append("session storage events")
        if not user_actions_summary:
            missing_event_types.append("user actions")
        if not websockets_overview:
            missing_event_types.append("websocket events")

        if missing_event_types:
            lines.append(f"\n No {', '.join(missing_event_types)} recorded.")

        return "\n".join(lines)

    def summarize_event_types(self) -> dict[str, int]:
        """Summarize event types with their counts.
        Returns a dict mapping event_type to count."""
        count_dict = defaultdict(int)
        for event in self.timeline.events:
            event_type = event.type
            if event_type:
                count_dict[event_type.value] += 1
        return dict(count_dict)

    def summarize_network_requests(self) -> dict[str, dict[str, int]]:
        """Summarize network requests by domain with status code distribution.
        Returns a nested dict: domain -> status_code -> count."""
        domain_stats = defaultdict(lambda: defaultdict(int))

        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.HTTP_REQUEST:
                continue

            domain = event.network_request_data.domain_name
            if not domain:
                continue

            if event.network_response_data and event.network_response_data.status:
                status_code = str(event.network_response_data.status)
            elif event.action_type == enums.ActionType.HTTP_REQUEST_PENDING_RESPONSE:
                status_code = enums.ActionType.HTTP_REQUEST_PENDING_RESPONSE.value
            elif event.action_type == enums.ActionType.NETWORK_LEVEL_FAILED_REQUEST:
                status_code = enums.ActionType.NETWORK_LEVEL_FAILED_REQUEST.value
            else:
                continue

            domain_stats[domain][status_code] += 1

        return {domain: dict(status_counts) for domain, status_counts in domain_stats.items()}

    def summarize_console_events(self) -> Optional[dict[str, int]]:
        """Summarize console events by level (log, info, debug, warning, error).
        Returns None if there are no console events."""
        level_counts = defaultdict(int)

        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.CONSOLE:
                continue

            level = event.action_type.value if event.action_type else "unknown"
            level_counts[level] += 1

        return dict(level_counts) if level_counts else None

    def summarize_local_storage_events(self) -> Optional[dict[str, int]]:
        """Summarize local storage events by operation (get, set, clear, remove).
        Returns None if there are no local storage events."""
        operation_counts = defaultdict(int)

        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.LOCAL_STORAGE:
                continue

            operation = event.action_type.value if event.action_type else "unknown"
            operation_counts[operation] += 1

        return dict(operation_counts) if operation_counts else None

    def summarize_session_storage_events(self) -> Optional[dict[str, int]]:
        """Summarize session storage events by operation (get, set, clear, remove).
        Returns None if there are no session storage events."""
        operation_counts = defaultdict(int)

        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.SESSION_STORAGE:
                continue

            operation = event.action_type.value if event.action_type else "unknown"
            operation_counts[operation] += 1

        return dict(operation_counts) if operation_counts else None

    def summarize_user_actions(self) -> Optional[dict[str, int]]:
        """Summarize user action events by action type (click, input, submit).
        Returns None if there are no user action events."""
        action_counts = defaultdict(int)

        for event in self.timeline.events:
            if event.type != enums.TimelineEventType.USER_ACTION:
                continue

            action = event.action_type.value if event.action_type else "unknown"
            action_counts[action] += 1

        return dict(action_counts) if action_counts else None

    def summarize_websockets(self) -> List[dto.WebSocketOverview]:
        sockets = defaultdict(lambda: dto.WebSocketOverview(socket_id=""))
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
                sockets[socket_id].frames_sent_count += 1
            elif event.action_type == enums.ActionType.MESSAGE_RECEIVED:
                sockets[socket_id].frames_received_count += 1
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