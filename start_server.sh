#!/bin/bash
# Script to run the MTA Mini Metro server using UV

cd "$(dirname "$0")"
uv run python run_server.py
