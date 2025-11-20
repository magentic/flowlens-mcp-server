import argparse
import asyncio
from flowlens_mcp_server.flowlens_mcp import server_instance
from flowlens_mcp_server.service import version

flowlens_mcp = server_instance.flowlens_mcp

    
def run_stdio():
    version.VersionService().check_version()
    asyncio.run(flowlens_mcp.run_async(transport="stdio"))

def run_http(port: int = 8001):
    version.VersionService().check_version()
    flowlens_mcp.run(transport="http", path="/mcp_stream/mcp/", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server.")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode to use (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to run the HTTP server on (only used with --transport http, default: 8001)"
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        run_stdio()
    else:
        run_http(port=args.port)
