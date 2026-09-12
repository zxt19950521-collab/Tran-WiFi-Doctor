"""Post a comment to a Jira issue."""

import argparse
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import JIRA_BASE_URL, JIRA_PASSWORD, JIRA_USERNAME


def build_session() -> requests.Session:
    session = requests.Session()
    session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
    session.headers.update(
        {"Accept": "application/json", "Content-Type": "application/json"}
    )
    return session


def add_comment(issue_key: str, body: str) -> dict:
    session = build_session()
    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/2/issue/{issue_key}/comment"
    response = session.post(url, json={"body": body}, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"评论发布失败，status={response.status_code}，response={response.text[:500]}"
        )
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Add comment to Jira issue")
    parser.add_argument("issue_key", help="Jira issue key, e.g. LK7KOS17-159")
    parser.add_argument(
        "--file", "-f", help="Read comment body from file (utf-8)"
    )
    parser.add_argument(
        "--body", "-b", help="Comment body text (Jira wiki markup)"
    )
    args = parser.parse_args()

    if args.file:
        body = open(args.file, encoding="utf-8").read()
    elif args.body:
        body = args.body
    else:
        body = sys.stdin.read()

    if not body.strip():
        print("评论内容为空", file=sys.stderr)
        return 1

    result = add_comment(args.issue_key, body)
    print(f"已发布评论 id={result.get('id')} created={result.get('created')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
