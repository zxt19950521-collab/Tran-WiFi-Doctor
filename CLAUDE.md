# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

WiFi Doctor 是一个基于 Claude Code 的 WiFi 问题自动分析系统。支持从 Jira 单号、日志文件或自然语言描述触发分析，自动匹配历史案例并生成分析报告。

## 常用命令

### 更新版本
```bash
# 一键更新
python scripts/update.py

# 或手动更新
git pull origin main
pip install -r requirements.txt
```

### 初始化数据目录
```bash
python config.py
```

### 拉取 Jira 工单
```bash
python jira_fetch_issue.py <ISSUE_KEY>
# 例如: python jira_fetch_issue.py OS162-40436
```

### MTK Kernel Log 时间转换
```bash
# Python 版本
python scripts/kernel_time_convert.py <kernel_log_file_or_directory>

# PowerShell 版本
.\scripts\kernel_time_convert.ps1 -Path "<kernel_log_path>"
```

### 数据迁移（项目内 → 外部数据目录）
```bash
python scripts/migrate_data.py
```

### MCP Server（供 Cursor/Trae/VS Code 使用）
```bash
# 安装依赖
pip install mcp requests

# 启动服务器（stdio 模式）
python mcp-server/server.py
```

### 提交案例到远程仓库
```bash
# 在 MCP 客户端中调用 commit_cases 工具
# 或手动执行：
cd .claude/skills/bug-analysis/cases
git add -A
git commit -m "feat: add new case"
git push -u origin main
```

## 架构说明

### 数据存储结构

分析数据存放在项目根目录下的 `AI-result` 目录：

```
AI-result/
├── logs/          # 下载的日志文件
├── reports/       # 生成的分析报告
└── issues/        # 工单数据
    └── <ISSUE_KEY>/
        ├── <ISSUE_KEY>.json      # 工单元数据
        ├── <ISSUE_KEY>-analysis.md  # 分析报告
        └── logs/                 # 日志文件
```

### 核心组件

- **config.py**: 配置管理，定义数据目录、Jira 凭据、MTK 工具路径
- **jira_fetch_issue.py**: Jira API 集成，拉取工单信息和日志
- **mcp-server/**: 通用 MCP Server，支持 Cursor/Trae/VS Code 等任何 MCP 客户端
  - `server.py`: 入口，FastMCP 实例
  - `tools/`: 7 个工具（jira、kernel_time、cases、tags、guide、prompt、cases_commit）
  - `resources/`: 3 个资源（案例索引、TAG 知识库、报告模板）

### 技能系统 (.claude/skills/)

#### bug-analysis - 完整 Bug 分析系统

支持从 Jira 单号、日志文件或自然语言描述触发分析，自动匹配历史案例，生成分析报告并推送到飞书。

- **SKILL.md**: 技能主定义，描述触发方式和执行流程
- **modules/**: 功能模块（jira-fetch、log-analysis、case-matching、knowledge-distill、report-generate）
- **cases/**: 案例库，按问题类型分类（p2p-connection、dhcp-failure、auth-failure 等）
- **knowledge/**: 知识库（TAG 定义、日志模式、规则库）
- **templates/**: 报告模板

#### wifi-common - WiFi 问题快速分析

遇到 WiFi 问题时，先初步分析，优先匹配案例仓库，如果没有匹配案例则根据 TAG 知识库进行独立分析并输出结论。

- **SKILL.md**: 技能主定义，快速分析流程
- **tags-knowledge.md**: WiFi 问题 TAG 知识库（8大类，30+ TAG）
- **analysis-guide.md**: 详细分析指南
- **quick-reference.md**: 快速参考卡

### 案例命名规则

```
CASE-{序号}_{Jira单号}_{简短标题}.md
```

## 环境变量

| 变量名 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| `JIRA_USERNAME` | 是 | Jira 用户名 | - |
| `JIRA_PASSWORD` | 是 | Jira 密码 | - |
| `WIFI_DOCTOR_DATA_DIR` | 否 | 数据存储目录 | `项目根目录/AI-result` |
| `KERNEL_TIME_CONVERT_EXE` | 否 | MTK 工具路径 | `D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe` |

## 系统要求

- Windows 10/11
- Python 3.10+
- Node.js 18+（Claude Code 依赖）

## 开发注意事项

- Python 依赖：`requests`（Jira API 调用）
- 可选依赖：`playwright`（FRBox 网盘日志下载需要）
- MTK Kernel Log 转换依赖联发科 Kernel log converter 工具
- Jira 认证支持 basic auth 和 session 两种模式，自动尝试
- 案例入库需要用户确认，知识库更新需要人工审核
- 分析报告默认使用中文
