"""
MTK Kernel Log 时间转换工具

调用联发科 Kernel log converter，为 kernel_log 生成 .localtime 文件。
将 kernel_log 的时间戳转换为 MM-DD HH:MM:SS.mmm 格式，便于与 Android main_log 按分秒对照。

依赖:
- 需要安装联发科 Kernel log converter 工具
- 首次运行自动检测安装位置
- 可通过环境变量 KERNEL_TIME_CONVERT_EXE 自定义路径
"""

import os
import subprocess
import sys
from pathlib import Path

# 常见安装路径列表
COMMON_PATHS = [
    r"D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"C:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"D:\Program Files\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"C:\Program Files\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"D:\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"C:\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"D:\tools\Mediatek\Kernel log converter\kernel_time_convert.exe",
    r"C:\tools\Mediatek\Kernel log converter\kernel_time_convert.exe",
]

# 缓存文件路径
CACHE_FILE = Path.home() / ".wifi-doctor-data" / ".kernel_converter_path"


def _read_cached_path() -> str | None:
    """读取缓存的工具路径"""
    try:
        if CACHE_FILE.exists():
            cached = CACHE_FILE.read_text(encoding="utf-8").strip()
            if cached and os.path.exists(cached):
                return cached
    except Exception:
        pass
    return None


def _write_cached_path(path: str) -> None:
    """缓存工具路径"""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(path, encoding="utf-8")
    except Exception:
        pass


def _search_common_paths() -> str | None:
    """搜索常见安装路径"""
    for path in COMMON_PATHS:
        if os.path.exists(path):
            return path
    return None


def get_converter_exe() -> str:
    """
    获取 kernel_time_convert.exe 的路径

    查找优先级：
    1. 环境变量 KERNEL_TIME_CONVERT_EXE
    2. 缓存文件记录的路径
    3. 搜索常见安装路径
    4. 抛出异常并提示安装
    """
    # 1. 检查环境变量
    exe = os.environ.get("KERNEL_TIME_CONVERT_EXE")
    if exe and os.path.exists(exe):
        _write_cached_path(exe)
        return exe

    # 2. 检查缓存
    cached = _read_cached_path()
    if cached:
        return cached

    # 3. 搜索常见路径
    found = _search_common_paths()
    if found:
        _write_cached_path(found)
        return found

    # 4. 未找到，提示安装
    raise FileNotFoundError(
        "未找到联发科 Kernel log converter 工具。\n\n"
        "请按以下步骤安装：\n"
        "1. 下载联发科 Kernel log converter 工具\n"
        "2. 安装到默认路径：D:\\Program Files (x86)\\Mediatek\\Kernel log converter\\\n"
        "3. 或设置环境变量 KERNEL_TIME_CONVERT_EXE 指向工具路径\n\n"
        "如果已安装到自定义位置，请设置环境变量：\n"
        "  [Environment]::SetEnvironmentVariable('KERNEL_TIME_CONVERT_EXE', 'D:\\your\\path\\kernel_time_convert.exe', 'User')"
    )


def convert_kernel_log(path: str) -> bool:
    """
    转换 kernel_log 文件的时间格式

    Args:
        path: kernel_log 文件或目录的路径

    Returns:
        bool: 转换是否成功
    """
    exe = get_converter_exe()
    target_path = Path(path)

    if not target_path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [exe, str(target_path)],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print(f"Successfully converted: {path}")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"Conversion failed with exit code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error running converter: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python kernel_time_convert.py <kernel_log_file_or_directory>")
        sys.exit(1)

    path = sys.argv[1]
    success = convert_kernel_log(path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
