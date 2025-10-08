# Magentic MCP Server

# Faster Delivery. Smarter Observability. Built-In with AI.

### Agent configuration

You need to generate an access token from https://flowlens.magentic.ai

```json
"flowlens-mcp": {
    "command": "pipx",
    "args": [
        "run",
        "--spec",
        "flowlens-mcp-server==<version>",
        "flowlens-server",
        "your-token"
    ],
    "type": "stdio"
}
```

# Claude Code

```bash
claude mcp add flowlens-mcp --transport stdio -- pipx run --spec "flowlens-mcp-server==<version>" flowlens-server your-token
```