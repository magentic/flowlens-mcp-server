# FlowLens MCP

[![PyPI version](https://img.shields.io/pypi/v/flowlens-mcp-server.svg)](https://pypi.org/project/flowlens-mcp-server/)

`flowlens-mcp-server` gives your coding agent (Claude Code, Cursor, Copilot, Codex) full browser context for in-depth debugging and regression testing.

## How it works
- Record your browser flow using the <a href="https://chromewebstore.google.com/detail/jecmhbndeedjenagcngpdmjgomhjgobf?utm_source=github-repo" target="_blank" rel="noopener noreferrer">FlowLens Chrome extension</a> (user actions, network, console, storage, DOM events/screen recording).
- Share it with your coding agent via the FlowLens MCP server, giving the agent full access to the recording.
- Your agent inspects and analyzes the flow for debugging and insights — without spending time/tokens on reproducing the issue.

## Demo

<video src="https://github.com/user-attachments/assets/fd73f2e6-6a7d-4518-b0db-62b8c6e6c99a" autoplay loop muted playsinline></video>

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
"flowlens": {
  "command": "flowlens-mcp-server",
  "type": "stdio"
}
```

### MCP Client configuration
<details>
  <summary>Claude Code</summary>
    Use the Claude Code CLI to add the FlowLens MCP server (<a href="https://docs.anthropic.com/en/docs/claude-code/mcp" target="_blank" rel="noopener noreferrer">guide</a>):

```bash
claude mcp add flowlens --transport stdio -- flowlens-mcp-server
```
</details>

<details>
  <summary>Cursor</summary>

  **Click the button to install:**

[<img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install in Cursor">](https://cursor.com/en/install-mcp?name=flowlens&config=eyJjb21tYW5kIjoiZmxvd2xlbnMtbWNwLXNlcnZlciJ9)

**Or install manually:**

Go to `Cursor Settings` -> `MCP` -> `New MCP Server`. Use the config provided above.

</details>


<details>
  <summary>Copilot / VS Code</summary>
  Follow the MCP install <a href="https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server" target="_blank" rel="noopener noreferrer">guide</a>,
  with the standard config from above. You can also install the FlowLens MCP server using the VS Code CLI:
  
  ```bash
  code --add-mcp '{"name":"flowlens","command":"flowlens-mcp-server"}'
  ```
</details>

<details>
    <summary>Codex</summary>
    Use the Codex CLI to add the FlowLens MCP server <a href="https://github.com/openai/codex/blob/main/docs/advanced.md#model-context-protocol-mcp" target="_blank" rel="noopener noreferrer">configure MCP guide</a>:

```bash
codex mcp add flowlens -- flowlens-mcp-server
```
</details>

<details>
  <summary>Antigravity</summary>
Follow the <a href="https://antigravity.google/docs/mcp" target="_blank" rel="noopener noreferrer">Connecting Custom MCP Servers guide</a>. Add the following config to the MCP servers config:

```json
"flowlens": {
  "command": "flowlens-mcp-server"
}
```
</details>

### Note:
The above setup only works with local flows. If you want to also connect to shareable flows, get your `FLOWLENS_MCP_TOKEN` from the <a href="https://flowlens.magentic.ai/flowlens/setup-wizard?tool=vscode" target="_blank" rel="noopener noreferrer">FlowLens platform</a> and add it to your relevant MCP config file:

```json
"flowlens": {
  "command": "flowlens-mcp-server",
  "type": "stdio",
  "env": {
    "FLOWLENS_MCP_TOKEN": "YOUR_FLOWLENS_MCP_TOKEN"
  }
}
```

## Usecases:

### Bug reporting
- Use FlowLens to quickly report bugs with full context to your coding agent. You no longer need to copy-paste console logs, take multiple screenshots, or have the agent spend tokens on reproducing the issue.


### Regression testing
- Use FlowLens to record your crticial user flows and ask your coding agent to auto test these flows or generate corresponding playwright test scripts


### Shareable flows
- Share captured flows with your teammates on the [FlowLens platform](https://flowlens.magentic.ai) and debug with your coding agent by adding a generated access token in the MCP config. More on this [here](https://flowlens.magentic.ai/flowlens/setup-wizard)