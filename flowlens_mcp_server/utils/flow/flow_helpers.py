from typing import Union
import os
import tempfile

from ...dto import dto
from .. import logger_setup

log = logger_setup.Logger(__name__)


def save_flow_to_file_if_large(flow: dto.FlowlensFlow) -> Union[dto.FlowlensFlow, str]:
    """
    Save flow to file if it exceeds 45k tokens (estimated as 135k characters).

    Args:
        flow: The FlowlensFlow object to check and potentially save

    Returns:
        Either the original flow object if small enough, or the file path if saved
    """
    # Convert flow to JSON
    json_string = flow.model_dump_json(indent=2)

    # Estimate token count: 3 characters ≈ 1 token
    estimated_tokens = len(json_string) / 3

    # If flow is large, save to file and return path
    if estimated_tokens > 45000:
        file_path = os.path.join(tempfile.gettempdir(), f"flowlens_flow_{flow.uuid}.json")
        with open(file_path, 'w') as f:
            f.write(json_string)
        log.logger.info(f"Flow {flow.uuid} exceeds 45k tokens ({estimated_tokens:.0f} estimated). Saved to {file_path}")
        return file_path

    # Otherwise return the flow object
    return flow


def save_event_to_file_if_large(event: dto.TimelineEventType, flow_uuid: str, event_index: int) -> Union[dto.TimelineEventType, str]:
    """
    Save event to file if it exceeds 45k tokens (estimated as 135k characters).

    Args:
        event: The timeline event object to check and potentially save
        flow_uuid: The UUID of the flow this event belongs to
        event_index: The index of the event in the timeline

    Returns:
        Either the original event object if small enough, or the file path if saved
    """
    json_string = event.model_dump_json(indent=2)
    estimated_tokens = len(json_string) / 3

    if estimated_tokens > 45000:
        file_path = os.path.join(tempfile.gettempdir(), f"flowlens_event_{flow_uuid}_{event_index}.json")
        with open(file_path, 'w') as f:
            f.write(json_string)
        log.logger.info(f"Event {event_index} from flow {flow_uuid} exceeds 45k tokens ({estimated_tokens:.0f} estimated). Saved to {file_path}")
        return file_path

    return event
