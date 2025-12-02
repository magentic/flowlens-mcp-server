# Imports required modules and utilities used across the FlowLens system
from typing import Optional

from flowlens_mcp_server.utils.recording.dom_snapshot_handler import DomSnapshotHandler
from ..dto import dto
from ..utils import logger_setup
from ..utils.flow import http_client, local_zip
from ..utils.flow.registry import flow_registry
from .timeline import load_process_and_register_timeline, summarize_timeline
from ..utils.settings import settings
from ..utils.recording.video_handler import VideoHandler

# Initialize a logger for this service
log = logger_setup.Logger(__name__)


# Holds parameters needed to initialize FlowLensService
class FlowLensServiceParams:
    def __init__(self, flow_uuid: Optional[str] = None, local_flow_zip_path: Optional[str] = None):
        # Auth token for communicating with FlowLens backend
        self.token = settings.flowlens_mcp_token
        # ID of the remote flow (if fetching from server)
        self.flow_uuid = flow_uuid
        # Path for local ZIP file flow (if loading locally)
        self.local_flow_zip_path = local_flow_zip_path


# Core service class that interacts with remote/local flows
class FlowLensService:
    def __init__(self, params: FlowLensServiceParams):
        # Store service params
        self.params = params
        # Build base API URL
        base_url = f"{settings.flowlens_url}/flowlens"
        # HTTP client configured with token + base URL
        self._client = http_client.HttpClient(params.token, base_url)
        # Local ZIP client for reading offline flow data
        self._zip_client = local_zip.LocalZipClient(params.local_flow_zip_path)

    # Return already-loaded flow from cache
    async def get_cached_flow(self) -> Optional[dto.FlowlensFlow]:
        cached_flow = await flow_registry.get_flow(self.params.flow_uuid)
        # Error if cache is empty
        if not cached_flow:
            raise RuntimeError(f"Flow with id {self.params.flow_uuid} not found in cache. Must get the flow first before accessing it.")
        return cached_flow
    
    # Fetch the flow (remote or local)
    async def get_flow(self) -> dto.FlowlensFlow:
        flow = await self._request_flow()
        # Error if flow not found
        if not flow:
            raise RuntimeError(f"Flow with id {self.params.flow_uuid} not found")
        return flow

    # Take a screenshot from WEBM video flow at a given second
    async def save_screenshot(self, second: int) -> str:
        flow = await self.get_cached_flow()
        # Screenshots only allowed for WEBM (video-based) recording
        if flow.recording_type != dto.enums.RecordingType.WEBM:
            raise RuntimeError("Screenshots can only be taken from WEBM recorded flows")
        # Use VideoHandler to save the screenshot
        handler = VideoHandler(flow)
        image_path = await handler.save_screenshot(second)
        return image_path
    
    # Save a DOM snapshot from RRWEB events at a given second
    async def save_snapshot(self, second: int) -> str:
        flow = await self.get_cached_flow()
        # Snapshots only work for RRWEB (DOM event-based) recordings
        if flow.recording_type != dto.enums.RecordingType.RRWEB:
            raise RuntimeError("Snapshots can only be taken from RRWEB recorded flows")
        renderer = DomSnapshotHandler(flow)
        return await renderer.save_snapshot(second)
        

    # Decides whether to fetch flow from UUID (remote) or ZIP (local)
    async def _request_flow(self):
        if self.params.flow_uuid:
            return await self._request_flow_by_uuid()
        elif self.params.local_flow_zip_path:
            return await self._request_flow_by_zip()
        else:
            raise RuntimeError("Either flow_uuid or local_flow_zip_path must be provided to request a flow")
        
    # Fetch flow from remote server using UUID
    async def _request_flow_by_uuid(self) -> dto.FlowlensFlow:
        response = await self._get_remote_flow()
        # Load remote video if needed
        await self._load_video(response)
        return await self._create_flow(response)

    # Make HTTP GET request to server to fetch flow data
    async def _get_remote_flow(self):
        qparams = {
            "session_uuid": settings.flowlens_session_uuid,
            "mcp_version": settings.flowlens_mcp_version
            }
        # Return FullFlow object
        response: dto.FullFlow = await self._client.get(
            f"flow/{self.params.flow_uuid}", 
            qparams=qparams, 
            response_model=dto.FullFlow
        )
        return response
    
    # Logs flow usage to backend analytics
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
            # Ignore logging errors silently
            pass
    
    # Load flow from a local ZIP file
    async def _request_flow_by_zip(self) -> dto.FlowlensFlow:
        response: dto.FullFlow = await self._zip_client.get()
        flow = await self._create_flow(response)
        await self._log_flow_usage(response)
        return flow
    
    # Builds an internal FlowlensFlow object and registers timeline
    async def _create_flow(self, base_flow: dto.FullFlow) -> dto.FlowlensFlow:
        # Load timeline events and register them in flow registry
        timeline = await load_process_and_register_timeline(
            flow_id=base_flow.id,
            is_local=base_flow.is_local,
            source=base_flow.local_files_data.timeline_file_path if base_flow.is_local else base_flow.timeline_url
        )
        # Generate a small summary of the timeline
        summary = summarize_timeline(timeline)

        # Create final Flow object used by MCP
        flow = dto.FlowlensFlow(
            uuid=base_flow.id,
            title=base_flow.title,
            description=base_flow.description,
            created_at=base_flow.created_at,
            system_id=base_flow.system_id,
            tags=base_flow.tags,
            comments=base_flow.comments if base_flow.comments else [],
            recording_type=base_flow.recording_type,
            are_screenshots_available=base_flow.are_screenshots_available,
            is_local=base_flow.is_local,
            local_files_data=base_flow.local_files_data,
            video_url=base_flow.video_url,

            timeline_summary=summary,
        )
        # Save flow in registry cache for future use
        await flow_registry.register_flow(flow)
        return flow

    # Load video file for WEBM flows (only if screenshots are available)
    async def _load_video(self, flow: dto.FullFlow):
        if not flow.are_screenshots_available:
            return
        handler = VideoHandler(flow)
        await handler.load_video()
