"""
WiFi Doctor 配置文件

将分析数据（日志、报告、工单数据）存放到项目外部，防止提交到版本库。
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """
    获取数据分析目录路径

    优先级：
    1. 环境变量 WIFI_DOCTOR_DATA_DIR
    2. 项目根目录下的 AI-result
    """
    env_dir = os.environ.get("WIFI_DOCTOR_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    return PROJECT_ROOT / "AI-result"


# 数据目录配置
DATA_DIR = get_data_dir()

# 子目录结构
LOGS_DIR = DATA_DIR / "logs"
REPORTS_DIR = DATA_DIR / "reports"
ISSUES_DIR = DATA_DIR / "issues"

# Jira 配置
JIRA_BASE_URL = "http://jira.transsion.com"
JIRA_USERNAME = os.environ.get("JIRA_USERNAME", "")
JIRA_PASSWORD = os.environ.get("JIRA_PASSWORD", "")

# MTK Kernel Log 转换工具
KERNEL_TIME_CONVERT_EXE = os.environ.get(
    "KERNEL_TIME_CONVERT_EXE",
    r"D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe"
)


def ensure_dirs():
    """确保所有必要的目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)


def get_issue_dir(issue_key: str) -> Path:
    """获取指定工单的数据目录"""
    issue_dir = ISSUES_DIR / issue_key
    issue_dir.mkdir(parents=True, exist_ok=True)
    (issue_dir / "logs").mkdir(parents=True, exist_ok=True)
    return issue_dir


if __name__ == "__main__":
    ensure_dirs()
    print(f"数据目录: {DATA_DIR}")
    print(f"日志目录: {LOGS_DIR}")
    print(f"报告目录: {REPORTS_DIR}")
    print(f"工单目录: {ISSUES_DIR}")
