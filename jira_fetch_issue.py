import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from config import (
    JIRA_BASE_URL,
    JIRA_USERNAME,
    JIRA_PASSWORD,
    get_issue_dir,
    ensure_dirs,
)

ISSUE_API = "/rest/api/2/issue/{issue_key}"
LEGACY_SESSION_API = "/rest/auth/1/session"
LOG_DIR_NAME = "logs"
URL_RE = re.compile(r"https?://\S+")
FRBOX_URL_RE = re.compile(r"https://frbox\.transsion\.com/\S+")
UNC_PATH_RE = re.compile(r"\\\\[^\r\n]+")
FRBOX_PASSWORD_RE = re.compile(r"(?:Password|密码)[：:]\s*([A-Za-z0-9]+)", re.IGNORECASE)
ARCHIVE_SUFFIXES = (
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
)

BASE_URL = JIRA_BASE_URL
USERNAME = JIRA_USERNAME
PASSWORD = JIRA_PASSWORD


def build_basic_auth_session(username: str, password: str) -> requests.Session:
    session = requests.Session()
    session.auth = (username, password)
    session.headers.update({"Accept": "application/json"})
    return session


def build_legacy_session(base_url: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    response = session.post(
        f"{base_url.rstrip('/')}{LEGACY_SESSION_API}",
        json={"username": username, "password": password},
        timeout=30,
        allow_redirects=True,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Jira Session 登录失败，status={response.status_code}，response={response.text[:300]}"
        )
    return session


def fetch_issue(base_url: str, issue_key: str, session: requests.Session) -> dict:
    response = session.get(
        f"{base_url.rstrip('/')}{ISSUE_API.format(issue_key=issue_key)}",
        params={"expand": "renderedFields"},
        timeout=30,
        allow_redirects=True,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"获取工单失败，status={response.status_code}，url={response.url}，response={response.text[:300]}"
        )
    return response.json()


def build_output(issue_data: dict) -> dict:
    fields = issue_data.get("fields", {})
    comments = ((fields.get("comment") or {}).get("comments") or [])
    return {
        "key": issue_data.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "priority": (fields.get("priority") or {}).get("name"),
        "reporter": (fields.get("reporter") or {}).get("displayName"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "labels": fields.get("labels") or [],
        "description": fields.get("description"),
        "comments": [
            {
                "author": (comment.get("author") or {}).get("displayName"),
                "created": comment.get("created"),
                "body": comment.get("body"),
            }
            for comment in comments
        ],
    }


def all_text_for_log_extraction(output: dict) -> str:
    """Merge description and comment bodies so UNC/http links in comments are included."""
    parts: list[str] = [output.get("description") or ""]
    for comment in output.get("comments") or []:
        if isinstance(comment, dict):
            parts.append(comment.get("body") or "")
    return "\n".join(parts)


def enrich_output_with_log_paths(output: dict) -> None:
    """Add extracted_log_paths (unc_paths, urls) for agents and local tooling."""
    text = all_text_for_log_extraction(output)
    output["extracted_log_paths"] = {
        "unc_paths": [str(p) for p in extract_unc_paths(text)],
        "urls": extract_all_urls(text),
    }


def try_fetch_with_auth(issue_key: str, username: str, password: str) -> dict:
    errors = []

    for mode in ("basic", "session"):
        try:
            if mode == "basic":
                session = build_basic_auth_session(username, password)
            else:
                session = build_legacy_session(BASE_URL, username, password)
            return fetch_issue(BASE_URL, issue_key, session)
        except Exception as error:
            errors.append(f"{mode}: {error}")

    raise RuntimeError("所有认证方式都失败：\n" + "\n".join(errors))


def extract_frbox_share_info(description: str) -> tuple[str, str | None] | None:
    if not description:
        return None

    url_match = FRBOX_URL_RE.search(description)
    if not url_match:
        return None

    share_url = url_match.group(0).rstrip(").,;")
    password = None

    query_password = parse_qs(urlparse(share_url).query).get("pwd")
    if query_password:
        password = query_password[0]

    if not password:
        password_match = FRBOX_PASSWORD_RE.search(description)
        if password_match:
            password = password_match.group(1)

    return share_url, password


def normalize_url(url: str) -> str:
    return url.rstrip(").,;]}>\"'")


def extract_all_urls(text: str) -> list[str]:
    if not text:
        return []

    urls: list[str] = []
    for match in URL_RE.finditer(text):
        normalized = normalize_url(match.group(0))
        if normalized not in urls:
            urls.append(normalized)
    return urls


def extract_unc_paths(text: str) -> list[Path]:
    if not text:
        return []

    unc_paths: list[Path] = []
    seen: set[str] = set()
    for match in UNC_PATH_RE.finditer(text):
        raw_path = normalize_url(match.group(0)).strip()
        if raw_path in seen:
            continue
        seen.add(raw_path)
        unc_paths.append(Path(raw_path))
    return unc_paths


def is_archive_file(path: Path) -> bool:
    file_name = path.name.lower()
    return any(file_name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def try_extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    if not is_archive_file(archive_path):
        return False

    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.unpack_archive(str(archive_path), str(extract_dir))
        return True
    except (shutil.ReadError, ValueError):
        return False


def filename_from_response(url: str, response: requests.Response) -> str:
    content_disposition = response.headers.get("content-disposition", "")
    filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition, re.IGNORECASE)
    if filename_match:
        return Path(filename_match.group(1)).name

    url_name = Path(urlparse(url).path).name
    if url_name:
        return url_name

    content_type = (response.headers.get("content-type") or "").split(";")[0].strip()
    guessed_ext = mimetypes.guess_extension(content_type) or ".bin"
    return f"downloaded_file{guessed_ext}"


def download_direct_file(url: str, download_dir: Path) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=120, allow_redirects=True) as response:
        if response.status_code != 200:
            raise RuntimeError(f"下载失败，status={response.status_code}，url={response.url}")

        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" in content_type:
            raise RuntimeError(f"该链接返回 HTML 页面，暂不支持自动处理：{response.url}")

        file_name = filename_from_response(url, response)
        target = download_dir / file_name
        with target.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
        return target


def download_frbox_archive(share_url: str, password: str | None, download_dir: Path) -> Path:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "检测到 FRBox 分享链接，但当前环境未安装 playwright。"
            "请先执行 `python -m pip install playwright` 和 "
            "`python -m playwright install chromium`。"
        ) from error

    download_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            page.goto(share_url, wait_until="domcontentloaded", timeout=60000)

            if password:
                try:
                    page.locator("input").first.fill(password)
                    page.get_by_role("button", name="确认").click()
                    page.wait_for_timeout(2000)
                except Exception:
                    # 链接可能已经带 pwd 或页面无需再次确认，直接继续尝试下载。
                    pass

            page.wait_for_timeout(3000)

            with page.expect_download(timeout=120000) as download_info:
                try:
                    page.get_by_role("button", name="下载全部").click()
                except Exception:
                    page.get_by_text("下载全部").click()

            download = download_info.value
            target = download_dir / download.suggested_filename
            if target.exists():
                target.unlink()
            download.save_as(str(target))
            return target
        except PlaywrightTimeoutError as error:
            raise RuntimeError(f"FRBox 页面等待超时：{error}") from error
        finally:
            browser.close()

def download_url_to_logs(url: str, description: str, logs_dir: Path) -> Path:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "frbox.transsion.com":
        share_info = extract_frbox_share_info(description)
        password = share_info[1] if share_info else None
        return download_frbox_archive(url, password, logs_dir)

    return download_direct_file(url, logs_dir)


def copy_shared_path_to_logs(source_path: Path, logs_dir: Path) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"共享路径不存在或当前账号无权限访问：{source_path}")

    logs_dir.mkdir(parents=True, exist_ok=True)

    if source_path.is_file():
        target = logs_dir / source_path.name
        shutil.copy2(source_path, target)
        return target

    target_dir = logs_dir / source_path.name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_path, target_dir)
    return target_dir


def extract_archives_in_path(target_path: Path, logs_dir: Path) -> None:
    if target_path.is_file():
        try_extract_archive(target_path, logs_dir)
        return

    for archive_file in target_path.rglob("*"):
        if archive_file.is_file():
            try_extract_archive(archive_file, archive_file.parent)


def try_download_logs_from_description(description: str, logs_dir: Path) -> list[Path]:
    downloaded_files: list[Path] = []
    urls = extract_all_urls(description)
    unc_paths = extract_unc_paths(description)

    for url in urls:
        file_path = download_url_to_logs(url, description, logs_dir)
        downloaded_files.append(file_path)
        extract_archives_in_path(file_path, logs_dir)

    for unc_path in unc_paths:
        copied_path = copy_shared_path_to_logs(unc_path, logs_dir)
        downloaded_files.append(copied_path)
        extract_archives_in_path(copied_path, logs_dir)

    return downloaded_files


def save_issue(issue_key: str, output: dict) -> Path:
    """保存工单数据到外部数据目录"""
    issue_output_dir = get_issue_dir(issue_key)
    output_file = issue_output_dir / f"{issue_key}.json"
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Jira issue JSON and optional logs (UNC/http).")
    parser.add_argument("issue_key", nargs="?", default=None, help="Jira key, e.g. K16SFA-334")
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only fetch and save JSON; skip copying/downloading logs",
    )
    args = parser.parse_args()

    issue_key = (args.issue_key or "").strip() or input("请输入 Jira 单号，例如 TOS163-25217: ").strip()
    if not issue_key:
        raise ValueError("issue_key 不能为空")

    if not USERNAME or not PASSWORD:
        raise ValueError("请先配置 JIRA_USERNAME 和 JIRA_PASSWORD 环境变量")

    # 确保数据目录存在
    ensure_dirs()

    issue_data = try_fetch_with_auth(issue_key, USERNAME, PASSWORD)
    output = build_output(issue_data)
    enrich_output_with_log_paths(output)
    output_file = save_issue(issue_key, output)
    logs_dir = output_file.parent / LOG_DIR_NAME

    downloaded_files: list[Path] = []
    download_error = None
    if not args.no_download:
        combined_text = all_text_for_log_extraction(output)
        try:
            downloaded_files = try_download_logs_from_description(combined_text, logs_dir)
        except Exception as error:
            download_error = error

    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n已保存到：{output_file}")
    if downloaded_files:
        for downloaded_file in downloaded_files:
            print(f"已下载日志/附件：{downloaded_file}")
    if download_error:
        print(f"日志下载失败：{download_error}", file=sys.stderr)


if __name__ == "__main__":
    main()
