"""分析流程提示词工具"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

ANALYSIS_PROMPT = r"""# WiFi 问题分析流程

## 输入类型判断

根据用户输入选择分析路径：
- **Jira 单号**（如 `OS162-40436`）→ 步骤 1 开始
- **日志文件路径**（如 `D:\logs\wifi-log.txt`）→ 步骤 2 开始
- **自然语言描述**（如 `P2P连接失败`）→ 步骤 3 开始

## 步骤 1：拉取 Jira 工单

调用 `fetch_jira_issue` 获取工单数据。

**必须执行**：只要有 Jira 单号，每次都重新拉取，禁止使用缓存数据。

从返回的 JSON 中提取：
- `summary` - 问题标题
- `description` - 问题描述
- `comments` - 评论（可能包含日志路径）
- `extracted_log_paths` - 提取的 UNC 路径和 URL

## 步骤 2：分析日志

1. 如果是 MTK kernel_log，先调用 `kernel_time_convert` 转换时间戳
2. 读取日志文件，按以下顺序提取信息：
   - 识别问题类型（P2P/DHCP/认证/扫描/断开/性能）
   - 提取关键事件和时间点
   - 识别失败模式和失败阶段
3. 调用 `search_tags` 获取相关 TAG 定义和日志模式
4. 根据 TAG 匹配规则从日志中自动提取 TAG

## 步骤 3：匹配历史案例

调用 `search_cases` 搜索匹配案例：
- 用提取的 TAG 作为搜索条件
- 用问题关键词搜索

**匹配度判断**：
- 匹配度 > 70%：直接引用案例结论
- 匹配度 40-70%：引用案例并补充分析
- 匹配度 < 40%：进入独立分析

**必须执行**：案例匹配结果必须出现在最终报告中，无论是否匹配到。

## 步骤 4：独立分析（无匹配案例时）

调用 `get_analysis_guide` 获取对应问题类型的分析策略。

按指南中的检查清单逐项排查，构建问题链条定位根因。

## 步骤 5：生成报告

按以下格式输出分析报告：

```markdown
## 问题分析结论

### 问题现象
{问题现象描述}

### TAG 标识
- {TAG1}
- {TAG2}

### 根因分析
{根本原因和详细分析}

### 关键日志
{关键日志片段，包含时间戳}

### 匹配案例
- {案例ID}: {案例标题}（匹配度: XX%）
或"未匹配到历史案例"

### 建议措施
1. {建议1}
2. {建议2}
```

## 步骤 5.1：推送到飞书（如有飞书 MCP）

使用飞书 MCP 推送报告时，**必须设置保密级别为 S2-内部公开**。

推送参数要求：
- 保密级别：S2-内部公开
- 文档标题：`{问题标题} 分析报告`
- 文档内容：步骤 5 生成的报告

## 步骤 6：案例入库（用户确认）

分析完成后，询问用户是否将本次分析入库为新案例。

**必须执行**：新案例必须经用户确认后才能入库，禁止自动入库。

如果用户确认入库：
1. 按命名规则创建案例文件：`CASE-{序号}_{Jira单号}_{简短标题}.md`
2. 更新 `cases/index.json` 添加新案例元数据
3. 调用 `commit_cases` 将新案例推送到远程仓库

## 硬规则

1. **有 Jira 单号时必须重新拉取**（禁止缓存）
2. **案例匹配结果必须出现在报告中**（无论是否匹配到）
3. **新案例入库必须用户确认**（禁止自动入库）
4. **所有结论必须有日志支持**（禁止无依据的推测）
5. **输出使用中文**
"""


def register(mcp: FastMCP):
    @mcp.tool()
    def get_analysis_prompt() -> str:
        """Get the WiFi problem analysis workflow prompt. Call this first before
        starting any WiFi analysis. It defines the required steps, rules, and
        output format for a complete analysis."""
        return ANALYSIS_PROMPT
