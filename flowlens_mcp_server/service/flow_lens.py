from typing import List, Optional
from ..dto import dto
from ..utils import http_request, logger_setup
from ..utils.flow_registry import flow_registry
from ..utils.settings import settings
from ..utils.timeline.registry import timeline_registry
from ..utils.video.handler import VideoHandler, VideoHandlerParams

log = logger_setup.Logger(__name__)


class FlowLensServiceParams:
    def __init__(self, flow_uuid: Optional[str] = None, local_flow_zip_path: Optional[str] = None):
        self.token = settings.flowlens_mcp_token
        self.flow_uuid = flow_uuid
        self.local_flow_zip_path = local_flow_zip_path

class FlowLensService:
    def __init__(self, params: FlowLensServiceParams):
        self.params = params
        base_url = f"{settings.flowlens_url}/flowlens"
        self._client = http_request.HttpClient(params.token, base_url)

    async def get_cached_flow(self) -> Optional[dto.FlowlensFlow]:
        cached_flow = await flow_registry.get_flow(self.params.flow_uuid)
        if not cached_flow:
            raise RuntimeError(f"Flow with id {self.params.flow_uuid} not found in cache. Must get the flow first before accessing its timeline.")
        return cached_flow
    
    async def get_flow(self) -> dto.FlowlensFlow:
        flow = await self._request_flow()

        if not flow:
            raise RuntimeError(f"Flow with id {self.params.flow_uuid} not found")
        return flow
    
    async def get_truncated_flow(self) -> dto.FlowlensFlow:
        flow = await self.get_flow()
        return flow.truncate()


    async def get_flow_full_comments(self) -> List[dto.FlowComment]:
        flow = await self.get_cached_flow()
        return flow.comments

    async def save_screenshot(self, timestamp: float) -> str:
        flow = await self.get_cached_flow()
        if not flow.are_screenshots_available:
            raise RuntimeError("Screenshots are not available for this flow")
        params = VideoHandlerParams(flow.uuid, flow.duration_ms)
        handler = VideoHandler(params)
        image_path = await handler.save_screenshot(timestamp)
        return image_path

    async def _request_flow(self):
        qparams = {
            "session_uuid": settings.flowlens_session_uuid,
            "mcp_version": settings.flowlens_mcp_version
            }
        response: dto.FullFlow = await self._client.get(f"flow/{self.params.flow_uuid}", qparams=qparams, response_model=dto.FullFlow)
        timeline_overview = await timeline_registry.register_timeline(response)
        await self._load_video(response)
        flow = dto.FlowlensFlow(
            uuid=response.id,
            title=response.title,
            description=response.description,
            created_at=response.created_at,
            system_id=response.system_id,
            tags=response.tags,
            comments=response.comments if response.comments else [],
            reporter=response.reporter,
            events_count=timeline_overview.events_count,
            duration_ms=timeline_overview.duration_ms,
            http_requests_count=timeline_overview.http_requests_count,
            event_type_summaries=timeline_overview.event_type_summaries,
            http_request_status_code_summaries=timeline_overview.http_request_status_code_summaries,
            http_request_domain_summary=timeline_overview.http_request_domain_summary,
            recording_type=response.recording_type,
            are_screenshots_available=response.are_screenshots_available,
            websockets_overview=timeline_overview.websockets_overview
        )
        await flow_registry.register_flow(flow)
        return flow

    async def _load_video(self, flow: dto.FullFlow):
        if not flow.are_screenshots_available:
            return
        params = VideoHandlerParams(flow.id, flow.video_url)
        handler = VideoHandler(params)
        await handler.load_video()
