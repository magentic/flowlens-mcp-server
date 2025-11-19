from typing import List, Optional

from flowlens_mcp_server.utils.video.dom_snapshot_handler import DomSnapshotHandler
from ..dto import dto
from ..utils import http_request, logger_setup, local_zip
from ..utils.flow_registry import flow_registry
from ..utils.settings import settings
from ..utils.timeline.processor import TimelineProcessor
from ..utils.timeline.registry import timeline_registry
from ..utils.video.handler import VideoHandler

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
        self._zip_client = local_zip.LocalZipClient(params.local_flow_zip_path)

    async def get_cached_flow(self) -> Optional[dto.FlowlensFlow]:
        cached_flow = await flow_registry.get_flow(self.params.flow_uuid)
        if not cached_flow:
            raise RuntimeError(f"Flow with id {self.params.flow_uuid} not found in cache. Must get the flow first before accessing it.")
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

    async def save_screenshot(self, second: int) -> str:
        flow = await self.get_cached_flow()
        if flow.recording_type != dto.enums.RecordingType.WEBM:
            raise RuntimeError("Screenshots can only be taken from WEBM recorded flows")
        handler = VideoHandler(flow)
        image_path = await handler.save_screenshot(second)
        return image_path
    
    async def save_snapshot(self, second: int) -> str:
        flow = await self.get_cached_flow()
        if flow.recording_type != dto.enums.RecordingType.RRWEB:
            raise RuntimeError("Snapshots can only be taken from RRWEB recorded flows")
        renderer = DomSnapshotHandler(flow)
        return await renderer.save_snapshot(second)
        

    async def _request_flow(self):
        if self.params.flow_uuid:
            return await self._request_flow_by_uuid()
        elif self.params.local_flow_zip_path:
            return await self._request_flow_by_zip()
        else:
            raise RuntimeError("Either flow_uuid or local_flow_zip_path must be provided to request a flow")
        
    async def _request_flow_by_uuid(self) -> dto.FlowlensFlow:
        response = await self._get_remote_flow()
        await self._load_video(response)
        return await self._create_flow(response)

    async def _get_remote_flow(self):
        qparams = {
            "session_uuid": settings.flowlens_session_uuid,
            "mcp_version": settings.flowlens_mcp_version
            }
        response: dto.FullFlow = await self._client.get(f"flow/{self.params.flow_uuid}", qparams=qparams, response_model=dto.FullFlow)
        return response
    
    async def _log_flow_usage(self, flow: dto.FullFlow):
        body = {
            "flow_id": flow.id,
            "anonymous_user_id": flow.anonymous_user_id,
            "recording_type": flow.recording_type.value,
            "is_mcp_usage": True
        }
        try:
            await self._client.post("log", body)
        except Exception:
            pass
    
    async def _request_flow_by_zip(self) -> dto.FlowlensFlow:
        response: dto.FullFlow = await self._zip_client.get()
        flow = await self._create_flow(response)
        await self._log_flow_usage(response)
        return flow
    
    async def _create_flow(self, base_flow: dto.FullFlow) -> dto.FlowlensFlow:
        # Process timeline using TimelineProcessor
        processor = TimelineProcessor(base_flow)
        timeline_overview = await processor.process()

        # Register the processed timeline in the registry
        await timeline_registry.register_timeline(base_flow.id, timeline_overview)

        flow = dto.FlowlensFlow(
            uuid=base_flow.id,
            title=base_flow.title,
            description=base_flow.description,
            created_at=base_flow.created_at,
            system_id=base_flow.system_id,
            tags=base_flow.tags,
            comments=base_flow.comments if base_flow.comments else [],
            events_count=timeline_overview.events_count,
            duration_ms=timeline_overview.duration_ms,
            http_requests_count=timeline_overview.http_requests_count,
            event_type_summaries=timeline_overview.event_type_summaries,
            http_request_status_code_summaries=timeline_overview.http_request_status_code_summaries,
            http_request_domain_summary=timeline_overview.http_request_domain_summary,
            recording_type=base_flow.recording_type,
            are_screenshots_available=base_flow.are_screenshots_available,
            websockets_overview=timeline_overview.websockets_overview,
            is_local=base_flow.is_local,
            local_files_data=base_flow.local_files_data,
            video_url=base_flow.video_url
        )
        await flow_registry.register_flow(flow)
        return flow

    async def _load_video(self, flow: dto.FullFlow):
        if not flow.are_screenshots_available:
            return
        handler = VideoHandler(flow)
        await handler.load_video()
        
