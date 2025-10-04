from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Type

from ..models import enums


class RequestParams(BaseModel):
    endpoint: str
    payload: Optional[dict] = None
    request_type: enums.RequestType
    response_model: Optional[Type[BaseModel]] = None

class FlowTag(BaseModel):
    id: int
    title: str
    
class FlowTagList(BaseModel):
    tags: List[FlowTag]

class System(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    users: Optional[List["User"]] = None

class User(BaseModel):
    id: int
    username: str
    email: str
    systems: Optional[List[System]] = None
    auth_id: str

class Flow(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    video_duration_ms: int
    created_at: datetime = Field(..., description="Native datetime in UTC")
    system_id: int
    system: Optional[System] = None
    tags: Optional[List[FlowTag]] = None
    reporter: Optional[str] = None
    sequence_diagram_status: enums.FlowSequenceDiagramStatus
    is_timeline_uploaded: bool
    is_video_uploaded: bool
    has_extended_sequence_diagram: bool

class FlowList(BaseModel):
    flows: List[Flow]

class FullFlow(Flow):
    timeline_url: Optional[str] = None
    video_url: Optional[str] = None
    sequence_diagram_url: Optional[str] = None
    extended_sequence_diagram_url: Optional[str] = None
    
class DeleteResponse(BaseModel):
    id: int
    success: bool
    message: Optional[str] = None


class FlowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    system_id: int
    tag_ids: Optional[List[int]] = None

class FlowTagCreateUpdate(BaseModel):
    title: str
    system_id: int

class FlowSequenceDiagramResponse(BaseModel):
    flow_id: int
    status: enums.FlowSequenceDiagramStatus
    url: Optional[str] = None
    has_extended_diagram: bool = False
    extended_diagram_url: Optional[str] = None
    
class FlowShareLink(BaseModel):
    flow_id: int
    token: str
    share_url: str
    expires_at: datetime