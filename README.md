# FlowLens MCP Server
An open-source MCP server that fetches your recorded user flows and bug reports from the <a href="https://www.magentic.ai/?utm_source=gh_flowlens" target="_blank" rel="noopener noreferrer">FlowLens platform</a> and exposes them to your AI coding agents for *context-aware debugging*.


## Getting Started
*Install flowlens-mcp-server*
```bash
pipx install flowlens-mcp-server
```

**IMPORTANT NOTE: If your version is not supported anymore, please, upgrade to latest version**
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
        "flowlens-mcp-server",
        "<YOUR_CODING_AGENT>",
        "<YOUR_FLOWLENS_MCP_TOKEN>"
    ],
    "type": "stdio"
}
```
*Replace `<YOUR_CODING_AGENT>` with your agen common name e.g. Claude Code, GitHub Copilot, Cursor, etc.*
*Replace `<YOUR_FLOWLENS_MCP_TOKEN>` with the MCP access token generated in step 3.*


### Claude Code Shortcut
```bash
claude mcp add flowlens-mcp --transport stdio -- pipx run "flowlens-mcp-server" "Claude Code" <YOUR_FLOWLENS_MCP_TOKEN> 
```
*Replace `<YOUR_FLOWLENS_MCP_TOKEN>` with the MCP access token generated in step 3.*



