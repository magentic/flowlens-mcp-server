# local-mcp-server

Minimal local MCP (Model Context Protocol) server used for development and testing.

This package provides a tiny server implementation for running a local MCP server with authentication middleware and basic tools.

## Features

- HTTP transport with custom endpoint path (`/mcp_stream/mcp/`)
- Bearer token authentication middleware
- Built-in tools:
  - `get_current_datetime_iso_format`: Returns current UTC datetime in ISO format
  - `list_flows`: Lists available flows for authenticated users

## Running the Server


### Method 1: Using Poetry (Recommended for Development)

```bash
# Install dependencies
poetry install

# Run directly with Python (HTTP transport)
poetry run python -m local_mcp_server.server

# Run with stdio transport
poetry run python -m local_mcp_server.server --stdio
```

### Method 2: Using pipx (For Distribution)

```bash
# Build the package
poetry build

# Run with pipx (HTTP transport, clears cache if needed)
rm -rf ~/.local/pipx/.cache/
pipx run --spec dist/magentic_mcp_server-x.x.x-py3-none-any.whl local-mcp-server

# Run with pipx using stdio transport
pipx run --spec dist/magentic_mcp_server-x.x.x-py3-none-any.whl local-mcp-server --stdio
```

## Server Configuration

By default, the server runs with HTTP transport:
- **Host**: `127.0.0.1` (localhost)
- **Port**: `8000` (default)
- **Endpoint**: `/mcp_stream/mcp/`
- **Full URL**: `http://127.0.0.1:8000/mcp_stream/mcp/`

To run the server using stdio transport (for integration with tools that require stdio), use the `--stdio` option. No HTTP server will be started in this mode.


## Client Configuration Example

### HTTP
```json
{
  "local_magentic": {
    "url": "http://127.0.0.1:8000/mcp_stream/mcp/",
    "type": "http",
    "headers": {
      "Authorization": "Bearer your-token-here"
    }
  }
}
```

### STDIO

```json
"pipx_magentic": {
  "command": "pipx",
  "args": ["run", "magentic-mcp-server==0.1.5", "--stdio", "--token", "your-token-here"],
  "type": "stdio"
}
```

## Troubleshooting

### 404 Not Found Error
If you get a 404 error, ensure:
1. The server is running on the correct port (8000)
2. Your client is accessing `/mcp_stream/mcp/` (not the default `/mcp/`)
3. If using pipx, clear the cache: `rm -rf ~/.local/pipx/.cache/`

### pipx Command Not Found
If `pipx` is not available, use the Poetry method or install pipx:
```bash
python -m pip install pipx
```

## Development

See `local_mcp_server/server.py` for the main entry point and server implementation.

# All in one 
```bash
poetry version patch && rm -R dist && poetry build && twine upload dist/* 
```