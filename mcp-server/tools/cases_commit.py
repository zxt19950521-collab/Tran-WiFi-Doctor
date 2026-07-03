"""案例提交工具 - 将新案例推送到远程仓库（最小提交：仅案例文件 + index.json）"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

CASES_DIR = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "cases"
REMOTE_URL = "https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git"

# 允许提交的文件模式（白名单）
ALLOWED_PATTERNS = [
    "index.json",                    # 案例索引
    "p2p-connection/CASE-*.md",      # P2P 案例
    "dhcp-failure/CASE-*.md",        # DHCP 案例
    "auth-failure/CASE-*.md",        # 认证案例
    "scan-failure/CASE-*.md",        # 扫描案例
    "disconnect/CASE-*.md",          # 断连案例
    "performance/CASE-*.md",         # 性能案例
]


def _is_allowed_file(file_path: str) -> bool:
    """检查文件是否在白名单内"""
    file_path = file_path.strip()
    if not file_path:
        return False
    # 去掉可能的 M/A/D 前缀（git status --porcelain 格式）
    clean_path = file_path.split()[-1] if file_path else ""
    for pattern in ALLOWED_PATTERNS:
        if clean_path == pattern or clean_path.endswith(pattern.replace("*", "")):
            return True
        # 通配符匹配
        if "*" in pattern:
            prefix = pattern.split("*")[0]
            if clean_path.startswith(prefix) and clean_path.endswith(".md"):
                return True
    return False


def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """执行 git 命令"""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def register(mcp: FastMCP):
    @mcp.tool()
    def commit_cases(message: str = "") -> str:
        """Commit and push new cases to the remote repository (minimal commit).
        Only commits case markdown files + index.json. Other files (knowledge docs,
        scripts, templates, SKILL.md, etc.) are automatically skipped to prevent
        merge conflicts when others sync.

        Use this after adding new case files to the cases directory.
        The cases directory is located at .claude/skills/bug-analysis/cases/.
        Remote: https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git

        IMPORTANT: Before committing, this tool will:
        1. Fetch latest changes from remote
        2. Check if remote has new commits
        3. Pull and rebase if needed (to sync with others' updates)
        4. Stage ONLY case-related files (whitelist: CASE-*.md + index.json)
        5. Commit and push

        Args:
            message: Optional commit message. If empty, uses a default message.

        Returns:
            Status message with git output details.
        """
        try:
            # Check if cases dir exists
            if not CASES_DIR.exists():
                return f"Error: Cases directory not found: {CASES_DIR}"

            # Check git status
            rc, stdout, stderr = _run_git(["status", "--porcelain"], CASES_DIR)
            if rc != 0:
                return f"Error checking git status: {stderr}"

            if not stdout:
                return "No changes to commit. Cases directory is up to date."

            # List changed files
            changed_files = stdout.split("\n")

            # Ensure remote exists
            rc, stdout, stderr = _run_git(["remote", "get-url", "origin"], CASES_DIR)
            if rc != 0:
                _run_git(["remote", "add", "origin", REMOTE_URL], CASES_DIR)

            # Ensure we're on main branch
            _run_git(["branch", "-M", "main"], CASES_DIR)

            # Step 1: Fetch latest from remote
            rc, stdout, stderr = _run_git(["fetch", "origin", "main"], CASES_DIR)
            if rc != 0:
                return f"Error fetching from remote: {stderr}"

            # Step 2: Check if remote has new commits
            rc, local_hash, _ = _run_git(["rev-parse", "HEAD"], CASES_DIR)
            rc2, remote_hash, _ = _run_git(["rev-parse", "origin/main"], CASES_DIR)

            remote_updated = False
            if rc == 0 and rc2 == 0 and local_hash != remote_hash:
                # Check how many commits remote is ahead
                rc3, count, _ = _run_git(
                    ["rev-list", "--count", f"{local_hash}..origin/main"], CASES_DIR
                )
                if rc3 == 0 and count.strip() != "0":
                    remote_updated = True

            # Step 3: Pull with rebase if remote has updates
            sync_message = ""
            if remote_updated:
                rc, stdout, stderr = _run_git(
                    ["pull", "origin", "main", "--rebase", "--allow-unrelated-histories"],
                    CASES_DIR,
                )
                if rc != 0:
                    # Rebase conflict - abort and report
                    _run_git(["rebase", "--abort"], CASES_DIR)
                    return f"Error: Merge conflict during sync. Please resolve manually.\n{stderr}"
                sync_message = f"Synced with remote ({count.strip()} new commit(s) from others).\n"

            # Step 4: Stage only case-related files (minimal commit)
            allowed_files = []
            skipped_files = []
            for f in changed_files:
                f = f.strip()
                if not f:
                    continue
                # git status --porcelain 格式: "XY filename"
                parts = f.split(None, 1)
                if len(parts) < 2:
                    continue
                filename = parts[1]
                if _is_allowed_file(filename):
                    allowed_files.append(filename)
                else:
                    skipped_files.append(filename)

            if not allowed_files:
                return f"No case-related files to commit.\nChanged files (skipped):\n" + "\n".join(f"  - {f}" for f in skipped_files)

            for f in allowed_files:
                rc, stdout, stderr = _run_git(["add", f], CASES_DIR)
                if rc != 0:
                    return f"Error staging file {f}: {stderr}"

            changes_summary = f"Staged {len(allowed_files)} case file(s):\n"
            for f in allowed_files:
                changes_summary += f"  + {f}\n"
            if skipped_files:
                changes_summary += f"Skipped {len(skipped_files)} non-case file(s):\n"
                for f in skipped_files:
                    changes_summary += f"  - {f}\n"

            # Step 5: Commit
            if not message:
                message = "feat: add new WiFi analysis cases"

            rc, stdout, stderr = _run_git(["commit", "-m", message], CASES_DIR)
            if rc != 0:
                return f"Error committing: {stderr}"

            # Step 6: Push
            rc, stdout, stderr = _run_git(["push", "-u", "origin", "main"], CASES_DIR)
            if rc != 0:
                return f"Error pushing to remote: {stderr}\n{stdout}"

            return f"""Successfully committed and pushed cases to remote!

Repository: {REMOTE_URL}
Branch: main

{sync_message}Changes committed:
{changes_summary}
Git output:
{stdout}
"""
        except Exception as e:
            return f"Error during commit: {e}"
