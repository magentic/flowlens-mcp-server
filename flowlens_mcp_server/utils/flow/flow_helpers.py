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
