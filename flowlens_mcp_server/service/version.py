from ..dto import dto
from ..utils.http_request import HttpClient
from ..utils.settings import settings


class VersionService:
    _latest_version_check: dto.McpVersionResponse = None
    def __init__(self):
        base_url = f"{settings.flowlens_url}/mcp"
        self._client = HttpClient(settings.flowlens_mcp_token, base_url)

    @property
    def latest_version_check(self) -> dto.McpVersionResponse:
        if VersionService._latest_version_check is None:
            self.check_version()
        return VersionService._latest_version_check
    
    def check_version(self) -> dto.McpVersionResponse:
        response = self._check_version()
        VersionService._latest_version_check = response
        settings.flowlens_session_uuid = response.session_uuid
        return response
    
    def assert_supported_version(self):
        if self.latest_version_check.is_supported:
            return
        raise Exception(
            self.latest_version_check.recommendation
        )

    def _check_version(self) -> dto.McpVersionResponse:
        return self._client.get_sync(f"version/{settings.flowlens_mcp_version}", response_model=dto.McpVersionResponse)