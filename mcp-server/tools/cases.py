"""案例库搜索工具"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

CASES_DIR = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "cases"


def register(mcp: FastMCP):
    @mcp.tool()
    def search_cases(
        query: str = "",
        category: str = "",
        tags: list[str] = [],
        include_content: bool = False,
    ) -> str:
        """Search the WiFi problem case library. Returns matching cases with metadata.
        Supports filtering by keyword, category, and tags.
        Categories: p2p-connection, dhcp-failure, auth-failure, scan-failure, disconnect, performance.
        Optionally includes full case markdown content.
        IMPORTANT: Case matching results MUST appear in the final report, even if no match found."""
        try:
            index_path = CASES_DIR / "index.json"
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)

            results = []
            query_lower = query.lower()

            for case in index.get("cases", []):
                if category and case["category"] != category:
                    continue
                if tags and not set(tags) & set(case.get("tags", [])):
                    continue
                if query_lower:
                    searchable = " ".join([
                        case.get("title", ""),
                        case.get("symptom", ""),
                        case.get("root_cause", ""),
                        " ".join(case.get("tags", [])),
                    ]).lower()
                    if query_lower not in searchable:
                        continue

                entry = dict(case)
                if include_content:
                    case_file = CASES_DIR / case["file_path"]
                    if case_file.exists():
                        entry["content"] = case_file.read_text(encoding="utf-8")
                results.append(entry)

            return json.dumps(results, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
