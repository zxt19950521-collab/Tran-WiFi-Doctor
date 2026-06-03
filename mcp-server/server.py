"""WiFi Doctor MCP Server

Provides tools and resources for WiFi problem analysis.
Designed to work with any MCP-compatible agent (Cursor, Trae, VS Code, Claude Code).

Usage:
    python mcp-server/server.py          # stdio transport (default)
    python mcp-server/server.py --help   # show help
"""

import sys
from pathlib import Path

# Project root is the parent of mcp-server/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER_DIR = Path(__file__).resolve().parent

# Add both to sys.path
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MCP_SERVER_DIR))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wifi-doctor")

# Import and register tools
from tools.jira import register as register_jira
from tools.kernel_time import register as register_kernel_time
from tools.cases import register as register_cases
from tools.tags import register as register_tags
from tools.guide import register as register_guide
from tools.prompt import register as register_prompt
from tools.cases_commit import register as register_cases_commit

register_jira(mcp)
register_kernel_time(mcp)
register_cases(mcp)
register_tags(mcp)
register_guide(mcp)
register_prompt(mcp)
register_cases_commit(mcp)

# Import and register resources
from resources.cases_index import register as register_cases_index
from resources.tags_knowledge import register as register_tags_knowledge
from resources.report_template import register as register_report_template

register_cases_index(mcp)
register_tags_knowledge(mcp)
register_report_template(mcp)

if __name__ == "__main__":
    mcp.run()  # stdio transport by default
