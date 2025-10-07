import argparse
from datetime import datetime
from local_mcp_server.flowlens_mcp import server_instance


flowlens_mcp = server_instance.flowlens_mcp

@flowlens_mcp.tool
def get_current_datetime_iso_format() -> str:
    return datetime.utcnow().isoformat()


def main():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server.")
    parser.add_argument("--stdio", action="store_true", help="Run server using stdio transport instead of HTTP.")
    parser.add_argument("--token", type=str, help="Token for authentication.")
    args = parser.parse_args()

    server_instance.set_token(args.token)

    if args.stdio:
        flowlens_mcp.run(transport="stdio")
    else:
        flowlens_mcp.run(transport="http", path="/mcp_stream/mcp/", port=8001)

def run_stdio():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server using stdio transport.")
    parser.add_argument("--token", type=str, help="Token for authentication.")
    args = parser.parse_args()
    server_instance.set_token(args.token)
    flowlens_mcp.run(transport="stdio")

def run_http():
    parser = argparse.ArgumentParser(description="Run the Flowlens MCP server using HTTP transport.")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the HTTP server on.")
    args = parser.parse_args()
    server_instance.set_token(None)
    flowlens_mcp.run(transport="http", path="/mcp_stream/mcp/", port=args.port)

if __name__ == "__main__":
    main()
