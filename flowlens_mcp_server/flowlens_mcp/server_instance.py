from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from ..service import version

flowlens_mcp = FastMCP("Flowlens MCP")


class UserAuthMiddleware(Middleware):
    async def on_call_tool(self, call_next):
        version.VersionService().assert_supported_version()
        return await call_next()

flowlens_mcp.add_middleware(UserAuthMiddleware())
