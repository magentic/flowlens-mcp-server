from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from ..service import flow_lens

flowlens_mcp = FastMCP("Flowlens MCP")

_TOKEN = None

def set_token(token: str):
    global _TOKEN
    _TOKEN = token

def get_token() -> str:
    return _TOKEN

class UserAuthMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token = get_token()
        if token is None:
            request: Request = get_http_request()
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                raise Exception("Authorization header missing")
            
            token = auth_header.split(" ")[1]
        service = flow_lens.FlowLensService(flow_lens.FlowLensServiceParams(token))
        context.fastmcp_context.set_state("flowlens_service", service)
        return await call_next(context=context)

flowlens_mcp.add_middleware(UserAuthMiddleware())
