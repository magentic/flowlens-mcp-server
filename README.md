# FlowLens MCP Server
A local MCP server that fetches your recorded user flows and bug reports from the <a href="https://www.magentic.ai/?utm_source=pypi-pkg_flowlens" target="_blank" rel="noopener noreferrer">FlowLens platform</a> and exposes them to your AI coding agents for *context-aware debugging*.


## Getting Started
*Install flowlens-mcp-server*
```bash
pipx install flowlens-mcp-server
```

**IMPORTANT NOTE: If your version is not supported anymore, please, upgrade to the latest version**
```bash
pipx upgrade flowlens-mcp-server
```

## Agent Configuration

### MCP server json configuration

```json
"flowlens-mcp": {
    "command": "pipx",
    "args": [
        "run",
        "flowlens-mcp-server"
    ],
    "type": "stdio",
    "env" : {
        "FLOWLENS_MCP_TOKEN" : "<YOUR_FLOWLENS_MCP_TOKEN>"
    }
}
```

### Claude Code Shortcut
```bash
claude mcp add flowlens-mcp --transport stdio --env FLOWLENS_MCP_TOKEN=<YOUR_FLOWLENS_MCP_TOKEN> -- pipx run "flowlens-mcp-server"
```



