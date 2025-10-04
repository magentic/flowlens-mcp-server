from ..dto import dto
from ..utils import http_request, logger_setup
from ..utils.settings import settings

log = logger_setup.Logger(__name__)


class FlowLensServiceParams:
    def __init__(self, token: str):
        self.token = token


class FlowLensService:
    def __init__(self, params: FlowLensServiceParams):
        self._request_handler = http_request.HttpRequestHandler(params.token)

    async def list_flows(self) -> dto.FlowList:
        response = await self._request_handler.get("flow", dto.FlowList)
        return response

    async def get_flow(self, flow_id: int) -> dto.FullFlow:
        response = await self._request_handler.get(f"flow/{flow_id}", dto.FullFlow)
        return response

    async def delete_flow(self, flow_id: int) -> dto.DeleteFlowResponse:
        response = await self._request_handler.delete(f"flow/{flow_id}", dto.DeleteFlowResponse)
        return response

    async def update_flow(self, flow_id: int, update_data: dto.FlowUpdate) -> dto.FullFlow:
        response = await self._request_handler.post(f"flow/{flow_id}", 
                                                    update_data.model_dump(), dto.FullFlow)
        return response

    async def list_tags(self) -> dto.FlowTagList:
        response = await self._request_handler.get("tag", dto.FlowTagList)
        return response

    async def create_tag(self, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        response = await self._request_handler.post("tag", data.model_dump(), dto.FlowTag)
        return response
    
    async def update_tag(self, tag_id: int, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        response = await self._request_handler.patch(f"tag/{tag_id}", data.model_dump(), dto.FlowTag)
        return response
    
    async def delete_tag(self, tag_id: int) -> bool:
        response = await self._request_handler.delete(f"tag/{tag_id}", bool)
        return response
    
    async def get_flow_sequence_diagram(self, flow_id: int) -> dto.FlowSequenceDiagramResponse:
        response = await self._request_handler.get(f"flow/{flow_id}/sequence_diagram", dto.FlowSequenceDiagramResponse)
        return response

    async def create_shareable_link(self, flow_id: int) -> dto.FlowShareLink:
        response = await self._request_handler.post(f"flow/{flow_id}/share", {}, dto.FlowShareLink)
        return response
    
    async def get_flow_by_shareable_link(self, shareable_link: str) -> dto.FullFlow:
        response = await self._request_handler.get(f"share/{shareable_link}", dto.FullFlow)
        return response
    
