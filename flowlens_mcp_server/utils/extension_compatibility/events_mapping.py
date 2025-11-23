def map_event(event: dict) -> dict:
    """Map event types to unified types (e.g., all console events to 'console').
    Note: This is only intended for backward compatibility with the extension"""
    event_type = event.get("type")

    if event_type == "dom_action":
        event["type"] = "user_action"

    elif event_type in ["console_debug", "console_log", "console_info", "console_warn", "console_error"]:
        event["type"] = "console"
        if 'console_log_data' in event:
            event["console_data"] = event['console_log_data']
            event["action_type"] = "log"
        elif 'console_warn_data' in event:
            event["console_data"] = event['console_warn_data']
            event["action_type"] = "warning"
        elif 'console_error_data' in event:
            event["console_data"] = event['console_error_data']
            event["action_type"] = "error"
        elif 'console_info_data' in event:
            event["console_data"] = event['console_info_data']
            event["action_type"] = "info"
        elif 'console_debug_data' in event:
            event["console_data"] = event['console_debug_data']
            event["action_type"] = "debug"

    elif event_type == "network_request":
        event["type"] = "http_request"
        event["action_type"] = "unknown"
    
    elif event_type == "network_response":
        event["type"] = "http_response"
        event["action_type"] = "unknown"
        
    elif event_type in ["websocket_created", "websocket_handshake_request", "websocket_handshake_response",
                        "websocket_frame_sent", "websocket_frame_received", "websocket_closed"]:
        event["type"] = "websocket"
            
    
    return event