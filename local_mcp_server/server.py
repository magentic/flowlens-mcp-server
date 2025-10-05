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

if __name__ == "__main__":
    main()
