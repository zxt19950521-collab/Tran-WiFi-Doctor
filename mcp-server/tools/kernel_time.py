"""MTK Kernel Log 时间转换工具"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP):
    @mcp.tool()
    def kernel_time_convert(path: str) -> str:
        """Convert MTK kernel_log timestamps to human-readable format (MM-DD HH:MM:SS.mmm).
        Generates a .localtime file alongside the original kernel_log.
        Auto-detects tool installation location on first run.
        Requires Mediatek Kernel log converter tool installed."""
        try:
            from scripts.kernel_time_convert import convert_kernel_log, get_converter_exe

            # 先检测工具是否存在
            try:
                exe_path = get_converter_exe()
                tool_status = f"工具位置: {exe_path}"
            except FileNotFoundError as e:
                return str(e)

            result = convert_kernel_log(path)
            if result:
                return f"Successfully converted: {path}\n{tool_status}\nOutput: {path}.localtime"
            else:
                return f"Conversion failed for: {path}\n{tool_status}\nCheck the tool installation."
        except FileNotFoundError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error during conversion: {e}"
