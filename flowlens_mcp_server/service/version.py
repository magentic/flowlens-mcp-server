import asyncio
from ..dto import dto
from ..utils.http_request import HttpClient
from ..utils.settings import settings


class VersionService:
    _latest_version: dto.McpVersionResponse = None
    def __init__(self):
        self._client = HttpClient(token=settings.flowlens_api_token)
        
    @property
    def latest_version(self) -> dto.McpVersionResponse:
        if not self._latest_version:
            self.check_version()
        return self._latest_version
    
    def check_version(self) -> dto.McpVersionResponse:
        response = self._check_version()
        self._latest_version = response
        return response
    
    def assert_supported_version(self):
        if self.latest_version.is_supported:
            return
        raise Exception(
            f"Current MCP version {settings.flowlens_mcp_version} is not supported.\n"
            f"Please, upgrade flowlens-mcp-server to latest version using command \"pipx upgrade flowlens-mcp-server\""
        )

    def _check_version(self):
        return asyncio.run(self._client.get(f"version/check/{settings.flowlens_mcp_version}", response_model=dto.McpVersionResponse))

