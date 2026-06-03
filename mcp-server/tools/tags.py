"""TAG 知识库搜索工具"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

TAGS_FILE = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "knowledge" / "tags.json"


def register(mcp: FastMCP):
    @mcp.tool()
    def search_tags(query: str = "", category: str = "") -> str:
        """Search the WiFi problem TAG knowledge base. Returns TAG definitions with
        descriptions, log patterns, and extraction rules.
        Categories: p2p-connection, dhcp-failure, auth-failure, scan-failure, disconnect, performance.
        Useful for identifying log patterns and diagnosing WiFi issues."""
        try:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            results = []
            query_lower = query.lower()

            for tag in data.get("tags", []):
                if category and tag.get("category") != category:
                    continue
                if query_lower:
                    searchable = " ".join([
                        tag.get("name", ""),
                        tag.get("description", ""),
                        tag.get("category", ""),
                        " ".join(tag.get("patterns", [])),
                    ]).lower()
                    if query_lower not in searchable:
                        continue

                entry = dict(tag)
                extraction = (
                    data.get("extraction_rules", {})
                    .get("log_patterns", {})
                    .get(tag.get("name", ""))
                )
                if extraction:
                    entry["extraction_patterns"] = extraction
                results.append(entry)

            return json.dumps(results, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
