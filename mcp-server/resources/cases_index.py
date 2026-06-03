"""案例库索引资源"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

CASES_INDEX = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "cases" / "index.json"


def register(mcp: FastMCP):
    @mcp.resource("wifi://cases/index", description="WiFi problem case library index")
    def cases_index() -> str:
        """WiFi problem case library index. Contains all case metadata, categories, and tags."""
        return CASES_INDEX.read_text(encoding="utf-8")
