# FlowLens MCP Server
An open-source MCP server that fetches your recorded user flows and bug reports from the <a href="https://www.magentic.ai/?utm_source=gh_flowlens" target="_blank" rel="noopener noreferrer">FlowLens platform</a> and exposes them to your AI coding agents for *context-aware debugging*.


## Getting Started

### Prerequisites

1. **Install Chrome Extension**
   - Download and install the extension from
  <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=pypi-package">the chrome web store</a>.
   - Pin it to your toolbar for quick access.

2. **Set Up Your Account**
   - Login to the extension using your Gmail account
   - Record and create your first flow using the extension:
     - Start recording from the extension popup
     - Stop recording from the overlay or extension popup
     - Click "Create flow"
   - You'll be automatically redirected to the Flowlens webapp to view flow details

3. **Generate MCP Token**
   - From the <a href="https://flowlens.magentic.ai/?utm_source=gh_flowlens" target="_blank" rel="noopener noreferrer">FlowLens platform</a>, generate your MCP access token

## Agent Configuration

### For Claude Code, Cursor, VS Code Copilot

Add the following configuration to the relevant MCP servers section, or use the shortcut below for Claude Code:

- **Claude Code**: Add to `~/.claude.json` under `mcpServers`
- **Cursor**: Add to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-specific) under `mcpServers`
- **VS Code with Copilot**: Add to `.vscode/mcp.json` (repository) or VS Code `settings.json` (personal) under `mcpServers`

*Replace `<your-token>` with the MCP access token generated in step 3.*

```json
"flowlens-mcp": {
    "command": "pipx",
    "args": [
        "run",
        "--spec",
        "flowlens-mcp-server==0.2.2",
        "flowlens-server",
        "<your-token>"
    ],
    "type": "stdio"
}
```

### Claude Code Shortcut

```bash
claude mcp add flowlens-mcp --transport stdio -- pipx run --spec "flowlens-mcp-server==0.2.2" flowlens-server <your-token>
```
