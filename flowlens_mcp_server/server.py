import argparse
from flowlens_mcp_server.flowlens_mcp import server_instance
from flowlens_mcp_server.utils.settings import settings
from flowlens_mcp_server.service import version

flowlens_mcp = server_instance.flowlens_mcp

    
def run_stdio():
    version.VersionService().check_version()
    flowlens_mcp.run(transport="stdio")

def run_http():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server using HTTP transport.")
    parser.add_argument("port", type=int, nargs="?", default=8001, help="Port to run the HTTP server on.")
    args = parser.parse_args()
    version.VersionService().check_version()
    flowlens_mcp.run(transport="http", path="/mcp_stream/mcp/", port=args.port)

if __name__ == "__main__":
    
    run_http()
