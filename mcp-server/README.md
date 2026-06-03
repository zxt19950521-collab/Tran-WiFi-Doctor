# WiFi Doctor MCP Server

通用 MCP Server，让任何支持 MCP 的智能体都能使用 WiFi 问题分析功能。

## 支持的客户端

| 客户端 | 传输方式 | 说明 |
|--------|----------|------|
| Claude Code | stdio | 通过 `.mcp.json` 自动加载 |
| Cursor | stdio | 通过 `.cursor/mcp.json` 或 Settings 配置 |
| Trae | stdio | 通过 MCP 设置配置 |
| VS Code | stdio | 通过 Copilot MCP 配置 |

## 安装依赖

```bash
pip install -r requirements.txt
```

## 更新版本

```bash
# 一键更新
python scripts/update.py

# 或手动更新
git pull origin main
pip install -r requirements.txt
```

## 环境变量

| 变量名 | 必需 | 说明 | 默认值 |
|--------|------|------|--------|
| `JIRA_USERNAME` | 是（Jira 功能） | Jira 用户名 | - |
| `JIRA_PASSWORD` | 是（Jira 功能） | Jira 密码 | - |
| `WIFI_DOCTOR_DATA_DIR` | 否 | 数据存储目录 | `项目根目录/AI-result` |
| `KERNEL_TIME_CONVERT_EXE` | 否 | MTK 工具路径 | 自动检测 |

## 客户端配置

### Claude Code

项目根目录的 `.mcp.json` 已配置好，直接启动即可：

```bash
cd Claude-Wifi-doctor
claude
```

### Cursor

在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "wifi-doctor": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "D:/path/to/Claude-Wifi-doctor"
    }
  }
}
```

或在 Cursor Settings → MCP → Add new MCP server 中配置。

### Trae

在 Trae MCP 设置中添加：

```json
{
  "mcpServers": {
    "wifi-doctor": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "D:/path/to/Claude-Wifi-doctor"
    }
  }
}
```

### VS Code (Copilot)

在 `.vscode/mcp.json` 中添加：

```json
{
  "servers": {
    "wifi-doctor": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## MCP Tools

| Tool | 说明 | 示例 |
|------|------|------|
| `get_analysis_prompt` | **分析流程提示词（首先调用）** | 获取完整分析流程和硬规则 |
| `fetch_jira_issue` | 拉取 Jira 工单 | `拉取 OS162-40436 工单` |
| `kernel_time_convert` | MTK 日志时间转换（自动检测安装位置） | `转换这个 kernel_log 的时间` |
| `search_cases` | 搜索案例库 | `搜索 DHCP 失败的案例` |
| `search_tags` | 搜索 TAG 知识库 | `P2P 相关的 TAG 有哪些` |
| `get_analysis_guide` | 获取分析指南 | `DHCP 问题怎么分析` |
| `commit_cases` | **提交案例到远程仓库（自动同步）** | `把新案例提交到 GitHub` |

### 工具详细说明

#### `kernel_time_convert` - MTK 日志时间转换

自动检测联发科 Kernel log converter 工具安装位置：

**查找优先级：**
1. 环境变量 `KERNEL_TIME_CONVERT_EXE`
2. 缓存文件 `~/.wifi-doctor-data/.kernel_converter_path`
3. 常见安装路径（8 个默认位置）

找到后自动缓存，后续运行直接使用。未找到会提示安装步骤。

#### `get_analysis_prompt` - 分析流程提示词

首次分析前调用，获取完整的分析流程和硬规则：
- 6 个标准分析步骤（识别输入 → 拉取数据 → 分析日志 → 匹配案例 → 生成报告 → 案例入库）
- 5 条硬规则（必须重新拉取 Jira、案例必须入库等）
- 报告输出格式模板
- 飞书推送保密级别要求（S2-内部公开）

#### `commit_cases` - 案例自动同步提交

提交案例到 GitHub 远程仓库，**自动同步其他人更新**：

```
fetch 远程 → 检查更新 → 有更新则 pull --rebase → add → commit → push
```

特性：
- 提交前自动 fetch 远程最新状态
- 如果远程有新提交，自动 pull --rebase 同步
- 同步完成后再提交本地更改
- 如有冲突自动 abort 并报告错误

远程仓库：`https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git`

**权限说明：**
- 整个项目：仅管理员可直接推送
- `cases/` 目录：所有人可通过 PR 提交案例

#### 飞书推送保密级别

推送到飞书的报告自动设置保密级别为 **S2-内部公开**，无需手动修改。

## MCP Resources

| Resource | 说明 |
|----------|------|
| `wifi://cases/index` | 案例库索引 |
| `wifi://knowledge/tags` | TAG 知识库 |
| `wifi://templates/report` | 报告模板 |

## 使用示例

### 基础分析

```
分析 OS162-40436
```

智能体会自动：调用 `get_analysis_prompt` → `fetch_jira_issue` → `search_tags` → `search_cases` → 生成报告

### 搜索案例

```
搜索 DHCP 相关的案例
```

### 获取分析指南

```
P2P 连接失败怎么分析
```

### 提交新案例

分析完成后，智能体会询问是否入库。确认后说：

```
把这次分析结果入库
```

或直接说：

```
提交新案例到 GitHub
```

智能体会自动调用 `commit_cases`，检查远程更新并同步后提交。
