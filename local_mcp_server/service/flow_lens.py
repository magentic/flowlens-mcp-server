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
        """
        Get a specific flow by its ID.
        Args:
            flow_id (int): The ID of the flow to retrieve.
        Returns:
            dto.FlowlensFlow: The FlowlensFlow dto object.
        """
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
            reporter=response.reporter,
            events_count=timeline_overview.events_count,
            duration_ms=timeline_overview.duration_ms,
            network_requests_count=timeline_overview.network_requests_count,
            event_type_summaries=timeline_overview.event_type_summaries,
            request_status_code_summaries=timeline_overview.request_status_code_summaries,
            network_request_domain_summary=timeline_overview.network_request_domain_summary,
        )
        return flow

    async def delete_flow(self, flow_id: int) -> dto.DeleteResponse:
        """
        Delete a specific flow by its ID.
        Args:
            flow_id (int): The ID of the flow to delete.
        Returns:
            dto.DeleteFlowResponse: The response object containing the result of the delete operation.
        """
        response = await self._request_handler.delete(f"flow/{flow_id}", dto.DeleteResponse)
        return response

    async def update_flow(self, flow_id: int, update_data: dto.FlowUpdate) -> dto.FullFlow:
        """
        Update a specific flow by its ID.
        Args:
            flow_id (int): The ID of the flow to update.
            update_data (dto.FlowUpdate): The data to update the flow with.
        Returns:
            dto.FullFlow: The updated FullFlow dto object.
        """
        response = await self._request_handler.patch(f"flow/{flow_id}", 
                                                    update_data.model_dump(), dto.FullFlow)
        return response

    async def list_tags(self) -> dto.FlowTagList:
        """
        List all tags.
        Returns:
            dto.FlowTagList: List of FlowTag dto objects.
        """
        response = await self._request_handler.get("tags", dto.FlowTagList)
        return response

    async def create_tag(self, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        """
        Create a new tag.
        Args:
            data (dto.FlowTagCreateUpdate): The data to create the tag with.
        Returns:
            dto.FlowTag: The created FlowTag dto object.
        """
        response = await self._request_handler.post("tag", data.model_dump(), dto.FlowTag)
        return response
    
    async def update_tag(self, tag_id: int, data: dto.FlowTagCreateUpdate) -> dto.FlowTag:
        """
        Update a specific tag by its ID.
        Args:
            tag_id (int): The ID of the tag to update.
            data (dto.FlowTagCreateUpdate): The data to update the tag with.
        Returns:
            dto.FlowTag: The updated FlowTag dto object.
        """
        response = await self._request_handler.patch(f"tag/{tag_id}", data.model_dump(), dto.FlowTag)
        return response
    
    async def delete_tag(self, tag_id: int) -> dto.DeleteResponse:
        """
        Delete a specific tag by its ID.
        Args:
            tag_id (int): The ID of the tag to delete.
        Returns:
            dto.DeleteResponse: The response object containing the result of the delete operation.
        """
        response = await self._request_handler.delete(f"tag/{tag_id}", dto.DeleteResponse)
        return response
    
    async def get_flow_sequence_diagram(self, flow_id: int) -> dto.FlowSequenceDiagramResponse:
        """
        Get the sequence diagram for a specific flow.
        Args:
            flow_id (int): The ID of the flow to retrieve the sequence diagram for.
        Returns:
            dto.FlowSequenceDiagramResponse: The response object containing the sequence diagram information.
        """
        response = await self._request_handler.get(f"flow/{flow_id}/sequence_diagram", dto.FlowSequenceDiagramResponse)
        return response

    async def create_shareable_link(self, flow_id: int) -> dto.FlowShareLink:
        """
        Create a shareable link for a specific flow.
        Args:
            flow_id (int): The ID of the flow to create a shareable link for.
        Returns:
            dto.FlowShareLink: The response object containing the shareable link information.
        """
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
