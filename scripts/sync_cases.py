"""从 GitHub 远端同步案例库到本地（无需 git）"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "zxt19950521-collab/Tran-WiFi-Doctor"
BRANCH = "main"
REMOTE_PREFIX = ".claude/skills/bug-analysis/cases"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / ".claude" / "skills" / "bug-analysis" / "cases"


def raw_url(rel_path: str) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in rel_path.split("/"))
    return (
        f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
        f"/{REMOTE_PREFIX}/{encoded}"
    )


def download(url: str, retries: int = 3) -> bytes:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WiFi-Doctor-sync"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                print(f"  retry {attempt + 1}/{retries - 1}: {e}")
                time.sleep(2)
    raise last_err  # type: ignore[misc]


def sync_cases() -> None:
    index_url = raw_url("index.json")
    print(f"Fetching index from {index_url}")
    index_data = json.loads(download(index_url).decode("utf-8"))

    local_index = CASES_DIR / "index.json"
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    local_index.write_bytes(download(index_url))
    print(f"Updated {local_index.relative_to(PROJECT_ROOT)}")

    synced = 0
    skipped = 0
    for case in index_data.get("cases", []):
        rel_path = case["file_path"].removeprefix("cases/").replace("\\", "/")
        local_path = CASES_DIR / rel_path
        remote_url = raw_url(rel_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        content = download(remote_url)
        if local_path.exists() and local_path.read_bytes() == content:
            skipped += 1
            print(f"  skip (unchanged): {rel_path}")
        else:
            local_path.write_bytes(content)
            synced += 1
            print(f"  synced: {rel_path}")

    readme_path = CASES_DIR / "README.md"
    readme_path.write_bytes(download(raw_url("README.md")))
    print(f"Updated {readme_path.relative_to(PROJECT_ROOT)}")

    total = len(index_data.get("cases", []))
    print()
    print(f"Done: {total} cases total, {synced} updated, {skipped} unchanged")
    print(f"Last updated: {index_data.get('last_updated', 'unknown')}")


if __name__ == "__main__":
    sync_cases()
