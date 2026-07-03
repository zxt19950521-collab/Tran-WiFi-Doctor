"""
WiFi Doctor 更新脚本

自动拉取最新代码并更新依赖。
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(args: list[str], cwd: Path = PROJECT_ROOT) -> tuple[int, str, str]:
    """执行命令"""
    result = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_git_status() -> bool:
    """检查是否有未提交的更改"""
    rc, stdout, _ = run_command(["git", "status", "--porcelain"])
    if rc != 0:
        print("警告: 无法检查 git 状态")
        return False
    return bool(stdout)


def pull_latest() -> bool:
    """拉取最新代码"""
    print("正在拉取最新代码...")
    rc, stdout, stderr = run_command(["git", "pull", "origin", "main"])
    if rc != 0:
        print(f"拉取失败: {stderr}")
        return False

    if "Already up to date" in stdout:
        print("已是最新版本")
        return True

    print(f"更新成功:\n{stdout}")
    return True


def update_dependencies() -> bool:
    """更新 Python 依赖"""
    print("正在更新依赖...")
    rc, stdout, stderr = run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    )
    if rc != 0:
        # requirements.txt 可能不存在，尝试安装基本依赖
        rc, stdout, stderr = run_command(
            [sys.executable, "-m", "pip", "install", "requests", "mcp"]
        )
        if rc != 0:
            print(f"依赖更新失败: {stderr}")
            return False

    print("依赖更新完成")
    return True


def show_changelog():
    """显示最近的更新日志"""
    print("\n最近更新:")
    rc, stdout, _ = run_command(["git", "log", "--oneline", "-5"])
    if rc == 0 and stdout:
        for line in stdout.split("\n"):
            print(f"  {line}")


def main():
    print("=" * 50)
    print("WiFi Doctor 更新程序")
    print("=" * 50)
    print()

    # 检查是否有未提交的更改
    if check_git_status():
        print("警告: 检测到未提交的更改")
        print("建议先提交或暂存更改再更新")
        response = input("是否继续更新? (y/N): ").strip().lower()
        if response != "y":
            print("更新已取消")
            return

    # 拉取最新代码
    if not pull_latest():
        print("\n更新失败，请检查网络连接或 git 配置")
        return

    # 更新依赖
    update_dependencies()

    # 显示更新日志
    show_changelog()

    print("\n" + "=" * 50)
    print("更新完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
