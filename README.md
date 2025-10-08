# Flowlens MCP Server

## Getting Started

### Prerequisites

1. **Install Chrome Extension**
   - Download and install the extension from [here](https://magentic.github.io/magentic_tab_recorder/)
   - Open the extension and pin it to your toolbar for easy access

2. **Set Up Your Account**
   - Login to the extension using your Gmail account
   - Record and create your first flow using the extension:
     - Start recording from the extension popup
     - Stop recording from the overlay or extension popup
     - Click "Create flow"
   - You'll be automatically redirected to the Flowlens webapp to view flow details

3. **Generate MCP Token**
   - From the [Flowlens web app home page](https://flowlens.magentic.ai), generate your MCP access token

## Agent Configuration

Replace `<your-token>` with the MCP access token generated in step 3.

### For Claude Code, Cursor, Copilot

Add the following configuration to the relevant MCP servers section, or use the shortcut below for Claude Code:

- **Claude Code**: Add to `~/.claude.json` under `mcpServers`
- **Cursor**: Add to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-specific) under `mcpServers`
- **VS Code with Copilot**: Add to `.vscode/mcp.json` (repository) or VS Code `settings.json` (personal) under `mcpServers`

```json
"flowlens-mcp": {
    "command": "pipx",
    "args": [
        "run",
        "--spec",
        "flowlens-mcp-server==0.1.1",
        "flowlens-server",
        "<your-token>"
    ],
    "type": "stdio"
}
```

### Claude Code Shortcut

```bash
claude mcp add flowlens-mcp --transport stdio -- pipx run --spec "flowlens-mcp-server==0.1.1" flowlens-server <your-token>
```