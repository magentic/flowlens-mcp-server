#!/bin/bash
# pipx run --no-cache --spec $mcp_repo_path local-mcp-server --stdio --token $mcp_token

PYTHON_CACHE="$HOME/.cache/pypoetry/virtualenvs"
source "$PYTHON_CACHE/$POETRY_PATH/bin/activate" && \
python -m flowlens_mcp_server.server


# For local development usage with claude code:
# run poetry install once inside this repo
# open a terminal anywhere and run:
#   export mcp_token=your_mcp_token && claude mcp add flowlens "${mcp_repo_path}/run.sh"