#!/bin/bash
# pipx run --no-cache --spec $mcp_repo_path local-mcp-server --stdio --token $mcp_token

PYTHON_CACHE="$HOME/.cache/pypoetry/virtualenvs"
source "$PYTHON_CACHE/flowlens-mcp-server-r5o-YNLt-py3.12/bin/activate" && \
python3 -m flowlens_mcp_server.server --stdio --token "$mcp_token"


# For local development usage with claude code:
# run poetry install once inside this repo
# open a terminal anywhere and run:
#   export mcp_token=your_mcp_token && claude mcp add flowlens "${mcp_repo_path}/run.sh"