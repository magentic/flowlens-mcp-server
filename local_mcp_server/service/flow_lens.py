from typing import List
from ..dto import dto
from ..utils import http_request, logger_setup
from ..utils.flow_registry import flow_registry
from ..utils.timeline.registry import timeline_registry
from ..utils.video.handler import VideoHandler, VideoHandlerParams

log = logger_setup.Logger(__name__)


class FlowLensServiceParams:
    def __init__(self, token: str):
        self.token = token


class FlowLensService:
    def __init__(self, params: FlowLensServiceParams):
        self._request_handler = http_request.HttpRequestHandler(params.token)

    async def list_flows(self) -> dto.FlowList:
        response = await self._request_handler.get("flows", dto.FlowList)
        return response

    async def get_flow(self, flow_id: int) -> dto.FlowlensFlow:
        if await flow_registry.is_registered(flow_id):
            return await flow_registry.get_flow(flow_id)
        response: dto.FullFlow = await self._request_handler.get(f"flow/{flow_id}", dto.FullFlow)
        timeline_overview = await timeline_registry.register_timeline(response)
        await self._load_video(response)
        flow = dto.FlowlensFlow(
            id=response.id,
            title=response.title,
            description=response.description,
            created_at=response.created_at,
            system_id=response.system_id,
            tags=response.tags,
            comments=response.comments,
            reporter=response.reporter,
            events_count=timeline_overview.events_count,
            duration_ms=timeline_overview.duration_ms,
            network_requests_count=timeline_overview.network_requests_count,
            event_type_summaries=timeline_overview.event_type_summaries,
            request_status_code_summaries=timeline_overview.request_status_code_summaries,
            network_request_domain_summary=timeline_overview.network_request_domain_summary,
        )
        await flow_registry.register_flow(flow)
        return flow.truncate()

    async def get_flow_full_comments(self, flow_id: int) -> List[dto.FlowComment]:
        flow = await self.get_flow(flow_id)
        return flow.comments

    async def delete_flow(self, flow_id: int) -> dto.DeleteResponse:
        response = await self._request_handler.delete(f"flow/{flow_id}", dto.DeleteResponse)
        return response

    async def update_flow(self, flow_id: int, update_data: dto.FlowUpdate) -> dto.FullFlow:
        response = await self._request_handler.patch(f"flow/{flow_id}", 
                                                    update_data.model_dump(), dto.FullFlow)
        return response

    async def list_tags(self) -> dto.FlowTagList:
        response = await self._request_handler.get("tags", dto.FlowTagList)
        return response

    async def create_tag(self, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        response = await self._request_handler.post("tag", data.model_dump(), dto.FlowTag)
        return response
    
    async def update_tag(self, tag_id: int, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        response = await self._request_handler.patch(f"tag/{tag_id}", data.model_dump(), dto.FlowTag)
        return response
    
    async def delete_tag(self, tag_id: int) -> dto.DeleteResponse:
        response = await self._request_handler.delete(f"tag/{tag_id}", dto.DeleteResponse)
        return response
    
    async def get_flow_sequence_diagram(self, flow_id: int) -> dto.FlowSequenceDiagramResponse:
        response = await self._request_handler.get(f"flow/{flow_id}/sequence_diagram", dto.FlowSequenceDiagramResponse)
        return response

    async def create_shareable_link(self, flow_id: int) -> dto.FlowShareLink:
        response = await self._request_handler.post(f"flow/{flow_id}/share", {}, dto.FlowShareLink)
        return response

    async def take_screenshot(self, flow_id: int, timestamp: float) -> str:
    
        flow = await self.get_flow(flow_id)
        params = VideoHandlerParams(flow.id, flow.duration_ms)
        handler = VideoHandler(params)
        image_base64 = await handler.take_screenshot_base64(timestamp)
        return image_base64
    
    async def save_screenshot(self, flow_id: int, timestamp: float) -> str:
        flow = await self.get_flow(flow_id)
        params = VideoHandlerParams(flow.id, flow.duration_ms)
        handler = VideoHandler(params)
        image_path = await handler.save_screenshot(timestamp)
        return image_path

    async def _load_video(self, flow: dto.FullFlow):
        if not flow.video_url:
            return
        params = VideoHandlerParams(flow.id, flow.video_url)
        handler = VideoHandler(params)
        await handler.load_video()
