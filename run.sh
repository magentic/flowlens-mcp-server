#!/bin/bash
# pipx run --no-cache --spec $mcp_repo_path local-mcp-server --stdio --token $mcp_token

PYTHON_CACHE="$HOME/.cache/pypoetry/virtualenvs"
cd ${mcp_repo_path} && poetry run python -m flowlens_mcp_server.server


# For local development usage with claude code:
# run poetry install once inside this repo
# open a terminal anywhere and run:
#   export mcp_token=your_mcp_token && claude mcp add flowlens-local-stdio "${mcp_repo_path}/run.sh"