# FlowLens MCP

[![PyPI version](https://img.shields.io/pypi/v/flowlens-mcp-server.svg)](https://pypi.org/project/flowlens-mcp-server/)

`flowlens-mcp-server` lets your coding agent (Claude Code, Cursor, Copilot, Gemini) inspect your recorded user web flows (video, network activity, console logs, and DOM events) via <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=github-repo" target="_blank" rel="noopener noreferrer">FlowLens Chrome extension</a>. It acts as an MCP (Model Context Protocol) server, giving your coding agent full browser context for in-depth debugging and regression testing.

## Requirements

- <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=github-repo" target="_blank" rel="noopener noreferrer">FlowLens browser extension</a> add to chrome and pin for ease of use 
- [pipx](https://pipx.pypa.io/stable/installation/) 

## Getting Started

To install:
```bash
pipx install flowlens-mcp-server
```

To upgrade to the latest version:
```bash
pipx upgrade flowlens-mcp-server
```

To check that the installation was successfully:
```bash
flowlens-mcp-server
```

## Add FlowLens MCP server

Add the following config to your MCP client (ex: `~/.claude.json`) under `mcpServers`:

```json
"flowlens-mcp": {
  "command": "flowlens-mcp-server",
  "type": "stdio"
}
```

### MCP Client configuration
<details>
  <summary>Claude Code</summary>
    Use the Claude Code CLI to add the FlowLens MCP server (<a href="https://docs.anthropic.com/en/docs/claude-code/mcp">guide</a>):

```bash
claude mcp add flowlens-mcp --transport stdio -- flowlens-mcp-server
```
</details>

## Usecases:

### Bug reporting
- Use FlowLens to quickly report bugs with full context to your coding agent. You no longer need to copy-paste console logs, take multiple screenshots, or have the agent spend tokens on reproducing the issue.


### Regression testing
- Use FlowLens to record your crticial user flows and ask your coding agent to auto test these flows or generate corresponding playwright test scripts


### Shareable flows
- Share captured flows with your teammates on the [FlowLens platform](https://flowlens.magentic.ai) and debug with your coding agent by adding a generated access token in the MCP config. More on this [here](https://flowlens.magentic.ai/flowlens/setup-wizard)