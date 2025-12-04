from typing import Optional

from flowlens_mcp_server.utils.recording.dom_snapshot_handler import DomSnapshotHandler
from ..dto import dto
from ..utils import logger_setup
from ..utils.flow import http_client, local_zip
from ..utils.flow.registry import flow_registry
from .timeline import load_process_and_register_timeline, summarize_timeline
from ..utils.settings import settings
from ..utils.recording.video_handler import VideoHandler
from ..utils.recording.download import download_recording

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
        self._client = http_client.HttpClient(params.token, base_url)
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
        if response.is_recording_available:
            await download_recording(
                flow_uuid=response.uuid,
                flow_type=response.recording_type,
                video_url=response.video_url,
            )
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
        timeline = await load_process_and_register_timeline(
            flow_id=base_flow.id,
            is_local=base_flow.is_local,
            source=base_flow.local_files_data.timeline_file_path if base_flow.is_local else base_flow.timeline_url
        )
        summary = summarize_timeline(timeline)

        flow = dto.FlowlensFlow(
            uuid=base_flow.id,
            title=base_flow.title,
            description=base_flow.description,
            created_at=base_flow.created_at,
            system_id=base_flow.system_id,
            tags=base_flow.tags,
            comments=base_flow.comments if base_flow.comments else [],
            recording_type=base_flow.recording_type,
            is_recording_available=base_flow.is_recording_available,
            is_local=base_flow.is_local,
            local_files_data=base_flow.local_files_data,
            video_url=base_flow.video_url,

            timeline_summary=summary,
        )
        await flow_registry.register_flow(flow)
        return flow
