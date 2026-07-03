"""TAG 知识库资源"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

TAGS_FILE = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "knowledge" / "tags.json"


def register(mcp: FastMCP):
    @mcp.resource("wifi://knowledge/tags", description="WiFi problem TAG knowledge base")
    def tags_knowledge() -> str:
        """WiFi problem TAG knowledge base. Contains TAG definitions, log patterns, and extraction rules."""
        return TAGS_FILE.read_text(encoding="utf-8")
