import os
import sys
from mcp.server.fastmcp import FastMCP

# Ensure local 'src' is importable in both local run and Functions
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
	sys.path.insert(0, SRC)

from mcp_twotruths.server import create_server

# BYO: Functions custom handler requires the server to listen on FUNCTIONS_CUSTOMHANDLER_PORT
mcp_port = int(os.environ.get("FUNCTIONS_CUSTOMHANDLER_PORT", 8080))

# Create our MCP server configured for stateless HTTP at the Functions port
mcp = create_server(port=mcp_port)
# Run using streamable-http transport per BYO guidance
mcp.run(transport="streamable-http")
