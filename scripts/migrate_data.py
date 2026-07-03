"""
数据迁移脚本

将项目中的分析数据移动到外部数据目录。
"""

import shutil
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_issue_dir, ensure_dirs, ISSUES_DIR


def migrate_issue(issue_key: str, source_dir: Path):
    """迁移单个工单数据"""
    if not source_dir.exists():
        print(f"跳过 {issue_key}: 源目录不存在")
        return

    target_dir = get_issue_dir(issue_key)
    print(f"迁移 {issue_key}: {source_dir} -> {target_dir}")

    # 复制文件
    for item in source_dir.iterdir():
        target_item = target_dir / item.name
        if item.is_dir():
            if target_item.exists():
                shutil.rmtree(target_item)
            shutil.copytree(item, target_item)
            print(f"  复制目录: {item.name}")
        else:
            shutil.copy2(item, target_item)
            print(f"  复制文件: {item.name}")


def main():
    """主函数"""
    project_dir = Path(__file__).parent.parent

    # 确保目标目录存在
    ensure_dirs()
    print(f"数据目录: {ISSUES_DIR}")

    # 查找所有工单目录
    for item in project_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # 检查是否是工单目录（包含 .json 文件）
            json_files = list(item.glob("*.json"))
            if json_files:
                issue_key = item.name
                migrate_issue(issue_key, item)

    print("\n迁移完成！")
    print(f"数据已移动到: {ISSUES_DIR}")
    print("\n提示：原目录可以手动删除")


if __name__ == "__main__":
    main()
