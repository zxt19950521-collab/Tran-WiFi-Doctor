"""WiFi 分析指南工具"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

WIFI_COMMON_DIR = PROJECT_ROOT / ".claude" / "skills" / "wifi-common"

PROBLEM_TYPE_MAP = {
    "p2p": "P2P",
    "dhcp": "DHCP",
    "auth": "认证",
    "disconnect": "断开",
    "performance": "性能",
    "dns": "DNS",
}


def _extract_section(content: str, problem_type: str) -> str:
    """从分析指南中提取特定问题类型的部分"""
    keyword = PROBLEM_TYPE_MAP.get(problem_type.lower(), problem_type)
    lines = content.split("\n")
    result_lines = []
    capturing = False
    header_level = 0

    for line in lines:
        # Match h2 or h3 headers
        h3_match = re.match(r"^(###)\s", line)
        h2_match = re.match(r"^(##)\s", line)

        if h3_match or h2_match:
            current_level = 3 if h3_match else 2
            if capturing:
                # Stop at same or higher level header
                if current_level <= header_level:
                    break
            if keyword in line:
                capturing = True
                header_level = current_level
        if capturing:
            result_lines.append(line)

    return "\n".join(result_lines).strip() if result_lines else ""


def register(mcp: FastMCP):
    @mcp.tool()
    def get_analysis_guide(problem_type: str = "") -> str:
        """Get WiFi problem analysis guide. Returns analysis strategies, TAG knowledge,
        matching rules, and output format templates.
        Filter by problem type: p2p, dhcp, auth, disconnect, performance, dns.
        If empty, returns the quick reference card."""
        try:
            if problem_type:
                guide_file = WIFI_COMMON_DIR / "analysis-guide.md"
                guide = guide_file.read_text(encoding="utf-8")
                section = _extract_section(guide, problem_type)
                if section:
                    return section
                available = ", ".join(PROBLEM_TYPE_MAP.keys())
                return f"No specific guide found for '{problem_type}'. Available: {available}"

            ref_file = WIFI_COMMON_DIR / "quick-reference.md"
            return ref_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error loading analysis guide: {e}"
