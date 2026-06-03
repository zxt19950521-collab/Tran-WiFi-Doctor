"""Jira 工单拉取工具"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP):
    @mcp.tool()
    def fetch_jira_issue(issue_key: str, download_logs: bool = False) -> str:
        """Fetch a Jira issue by key. Returns structured JSON with issue metadata,
        description, comments, and extracted log paths (UNC/URL).
        Optionally downloads log files from URLs/UNC paths found in the issue.
        Requires JIRA_USERNAME and JIRA_PASSWORD environment variables.
        IMPORTANT: Always call get_analysis_prompt first to follow the required workflow."""
        try:
            from jira_fetch_issue import (
                try_fetch_with_auth,
                build_output,
                enrich_output_with_log_paths,
                all_text_for_log_extraction,
                try_download_logs_from_description,
            )
            from config import JIRA_USERNAME, JIRA_PASSWORD, ensure_dirs, get_issue_dir

            if not JIRA_USERNAME or not JIRA_PASSWORD:
                return json.dumps(
                    {"error": "JIRA_USERNAME and JIRA_PASSWORD environment variables are required"},
                    ensure_ascii=False,
                )

            ensure_dirs()
            issue_data = try_fetch_with_auth(issue_key, JIRA_USERNAME, JIRA_PASSWORD)
            output = build_output(issue_data)
            enrich_output_with_log_paths(output)

            if download_logs:
                issue_dir = get_issue_dir(issue_key)
                logs_dir = issue_dir / "logs"
                try:
                    downloaded = try_download_logs_from_description(
                        all_text_for_log_extraction(output), logs_dir
                    )
                    output["downloaded_files"] = [str(p) for p in downloaded]
                except Exception as e:
                    output["download_error"] = str(e)

            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
