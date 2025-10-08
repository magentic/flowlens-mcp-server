import argparse
from local_mcp_server.flowlens_mcp import server_instance


flowlens_mcp = server_instance.flowlens_mcp


def run_stdio():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server using stdio transport.")
    parser.add_argument("token", type=str, help="Token for authentication.")
    args = parser.parse_args()
    server_instance.set_token(args.token)
    flowlens_mcp.run(transport="stdio")

def run_http():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server using HTTP transport.")
    parser.add_argument("port", type=int, nargs="?", default=8001, help="Port to run the HTTP server on.")
    args = parser.parse_args()
    server_instance.set_token(None)
    flowlens_mcp.run(transport="http", path="/mcp_stream/mcp/", port=args.port)

if __name__ == "__main__":
    run_stdio()
