from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from ..service import flow_lens
from ..utils.settings import settings

flowlens_mcp = FastMCP("Flowlens MCP")


class UserAuthMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        service = flow_lens.FlowLensService(flow_lens.FlowLensServiceParams())
        context.fastmcp_context.set_state("flowlens_service", service)
        return await call_next(context=context)

flowlens_mcp.add_middleware(UserAuthMiddleware())
