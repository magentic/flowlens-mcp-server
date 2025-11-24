# FlowLens MCP Server
A local MCP server that connects your recorded web user flows via <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=github-repo" target="_blank" rel="noopener noreferrer">FlowLens Chrome extension</a> to your coding agent. 


## Getting Started
*Install FlowLens browser extension* 

Go to the <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=github-repo" target="_blank" rel="noopener noreferrer">chrome webstore</a>, add to chrome and pin it for ease of use 

*Install flowlens-mcp-server*
```bash
pipx install flowlens-mcp-server
```

You can install `pipx` via the [official installation guide](https://pipx.pypa.io/stable/installation/).

To upgrade to the latest version:
```bash
pipx upgrade flowlens-mcp-server
```

To check that the package is installed successfully:
```bash
flowlens-mcp-server
```

## Add the MCP server

### Claude Code quick setup cli command:
```bash
claude mcp add flowlens-mcp --transport stdio -- flowlens-mcp-server
```

### MCP server json configuration

Add the following to the mcp json config (ex: `~/.claude.json`) under `mcpServers`:

```json
"flowlens-mcp": {
  "command": "flowlens-mcp-server",
  "type": "stdio"
}
```

### Usecases:

#### Bug reporting
- Use FlowLens to quickly report bugs with full context to your coding agent. You no longer need to copy-paste console logs, take multiple screenshots, or have the agent spend tokens on reproducing the issue.


#### Regression testing
- Use FlowLens to record your crticial user flows and ask your coding agent to auto test these flows or generate corresponding playwright test scripts


#### Shareable flows
- Share captured flows with your teammates on the [FlowLens platform](https://flowlens.magentic.ai) and debug with your coding agent by adding a generated access token in the MCP config. More on this [here](https://flowlens.magentic.ai/flowlens/setup-wizard)