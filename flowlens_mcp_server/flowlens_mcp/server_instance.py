from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from ..service import flow_lens
from ..utils.settings import settings

flowlens_mcp = FastMCP("Flowlens MCP")

_TOKEN = None

def set_token(token: str):
    global _TOKEN
    _TOKEN = token

def get_token() -> str:
    return _TOKEN or settings.flowlens_api_token

class UserAuthMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token = get_token()
        
        auth_header = self._extract_auth_header()
        if auth_header:
            token = auth_header.split(" ")[1]
        elif not token:
            raise Exception("Authorization header missing")
            
        service = flow_lens.FlowLensService(flow_lens.FlowLensServiceParams(token))
        context.fastmcp_context.set_state("flowlens_service", service)
        return await call_next(context=context)

    def _extract_auth_header(self):
        try:
            request: Request = get_http_request()
            auth_header = request.headers.get("Authorization", None)
            return auth_header
        except Exception as e:
            return None

flowlens_mcp.add_middleware(UserAuthMiddleware())
