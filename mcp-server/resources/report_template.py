"""报告模板资源"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

TEMPLATE_FILE = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "templates" / "report-template.md"


def register(mcp: FastMCP):
    @mcp.resource("wifi://templates/report", description="WiFi problem analysis report template")
    def report_template() -> str:
        """WiFi problem analysis report template. Use this format when generating analysis reports."""
        return TEMPLATE_FILE.read_text(encoding="utf-8")
