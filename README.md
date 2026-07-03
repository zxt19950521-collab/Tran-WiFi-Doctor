# WiFi Doctor - 智能 WiFi 问题诊断系统

基于 Claude Code 的 WiFi 问题自动分析工具，支持从 Jira 单号、日志文件或自然语言描述触发分析，自动匹配历史案例并生成分析报告。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [更新版本](#更新版本)
- [详细配置](#详细配置)
  - [1. Python 环境](#1-python-环境)
  - [2. Claude Code 配置](#2-claude-code-配置)
  - [3. Jira 配置](#3-jira-配置)
  - [4. 飞书配置](#4-飞书配置)
  - [5. MTK Kernel Log 转换工具](#5-mtk-kernel-log-转换工具)
- [使用说明](#使用说明)
- [集成方式](#集成方式)
  - [方式一：Claude Code](#方式一claude-code)
  - [方式二：Cursor](#方式二cursor)
  - [方式三：Trae](#方式三trae)
  - [MCP Tools 说明](#mcp-tools-说明)
- [项目结构](#项目结构)
- [常见问题](#常见问题)

---

## 系统要求


| 项目          | 要求                   |
| ----------- | -------------------- |
| 操作系统        | Windows 10/11        |
| Python      | 3.10+                |
| Claude Code | 最新版本                 |
| Node.js     | 18+ (Claude Code 依赖) |


---

## 快速开始

### 方式一：克隆项目（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git Claude-Wifi-doctor
cd Claude-Wifi-doctor

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 配置环境变量（见下方详细说明）
# 4. 配置 Jira 账号（见下方详细说明）
# 5. 初始化数据目录
python config.py

# 6. 启动 Claude Code
claude
```

### 方式二：Fork 后克隆（需要提交案例的用户）

1. 在 GitHub 上 Fork 仓库：https://github.com/zxt19950521-collab/Tran-WiFi-Doctor
2. 克隆你 Fork 的仓库：

```bash
git clone https://github.com/<你的用户名>/Tran-WiFi-Doctor.git Claude-Wifi-doctor
cd Claude-Wifi-doctor

# 添加上游仓库（用于同步更新）
git remote add upstream https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git

# 安装依赖
pip install -r requirements.txt
python config.py
```

## 更新版本

```bash
# 一键更新（拉取最新代码 + 更新依赖）
python scripts/update.py

# 或手动更新
git pull origin main
pip install -r requirements.txt
```

### Fork 用户同步上游更新

```bash
# 拉取上游最新代码
git fetch upstream
git merge upstream/main

# 或使用更新脚本
python scripts/update.py
```

## 权限说明

| 目录 | 权限 | 说明 |
|------|------|------|
| 整个项目 | 仅管理员 | 代码、配置、文档等 |
| `.claude/skills/bug-analysis/cases/` | 所有人 | 通过 PR 提交案例（自动合入） |

**案例提交流程（自动合入）：**
1. Fork 仓库
2. 在 `cases/` 目录添加新案例
3. 提交 Pull Request
4. **自动合入**（仅限 cases 目录的修改）

**其他文件提交流程（需审批）：**
1. Fork 仓库
2. 修改代码
3. 提交 Pull Request
4. 管理员审核后手动合并

---

## 详细配置

### 1. Python 环境

#### 安装依赖

```bash
pip install requests
```

如果需要从 FRBox 下载日志，还需要安装 Playwright：

```bash
pip install playwright
python -m playwright install chromium
```

#### 验证安装

```bash
python -c "import requests; print('requests OK')"
python --version  # 确认 Python 3.10+
```

### 2. 数据目录配置

分析数据（日志、报告、工单）存放在项目根目录下的 `AI-result` 目录。

#### 默认位置

```
项目根目录/AI-result/
```

#### 自定义位置（可选）

设置环境变量：

```powershell
[Environment]::SetEnvironmentVariable("WIFI_DOCTOR_DATA_DIR", "D:\wifi-data", "User")
```

#### 目录结构

```
AI-result/
├── logs/          # 下载的日志文件
├── reports/       # 生成的分析报告
└── issues/        # 工单数据
    ├── TOS163-25603/
    │   ├── TOS163-25603.json
    │   └── logs/
    └── OS162-34615/
        ├── OS162-34615.json
        └── logs/
```

#### 初始化目录

```bash
python config.py
```

#### 迁移已有数据

如果项目中已有分析数据，可以使用迁移脚本：

```bash
python scripts/migrate_data.py
```

迁移完成后，原目录可以手动删除。

---

### 2. Claude Code 配置

#### 安装 Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

#### 项目配置文件

项目包含以下配置文件，**不要删除**：


| 文件                             | 说明              |
| ------------------------------ | --------------- |
| `.claude/settings.local.json`  | 本地权限配置          |
| `.mcp.json`                    | MCP 服务器配置（飞书集成） |
| `.claude/skills/bug-analysis/` | Bug 分析技能定义      |


---

### 3. Jira 配置

Jira 用于自动拉取 Bug 单和日志。

#### 方式一：环境变量（推荐）

设置系统环境变量：

```powershell
# Windows PowerShell
[Environment]::SetEnvironmentVariable("JIRA_USERNAME", "your_username", "User")
[Environment]::SetEnvironmentVariable("JIRA_PASSWORD", "your_password", "User")
```

或通过系统设置：

1. 右键"此电脑" → 属性 → 高级系统设置
2. 环境变量 → 用户变量 → 新建
3. 添加 `JIRA_USERNAME` 和 `JIRA_PASSWORD`

#### 方式二：修改脚本

编辑 `jira_fetch_issue.py` 文件顶部：

```python
USERNAME = os.environ.get("JIRA_USERNAME", "your_username")
PASSWORD = os.environ.get("JIRA_PASSWORD", "your_password")
```

#### 验证配置

```bash
python jira_fetch_issue.py --help
```

---

### 4. 飞书配置

飞书用于推送分析报告。项目已配置 MCP 服务器，如需更换：

#### 获取飞书 MCP 地址

1. 登录飞书开放平台 [https://open.feishu.cn/page/mcp/7647042464067357905](https://open.feishu.cn/page/mcp/7647042464067357905)
2. 创建应用并获取 MCP 流式接口地址

#### 更新配置

编辑 `.mcp.json` 文件：

```json
{
  "mcpServers": {
    "feishu-mcp": {
      "type": "streamable-http",
      "url": "https://open.feishu.cn/mcp/stream/YOUR_MCP_ID"
    }
  }
}
```

---

### 5. MTK Kernel Log 转换工具

用于将联发科平台的 kernel_log 时间戳转换为可读格式。**首次运行自动检测安装位置**。

#### 自动检测

工具会按以下顺序查找：
1. 环境变量 `KERNEL_TIME_CONVERT_EXE`
2. 缓存文件记录的路径（`~/.wifi-doctor-data/.kernel_converter_path`）
3. 搜索常见安装路径（8 个默认位置）

找到后自动缓存路径，后续运行直接使用。

#### 安装联发科工具

1. 下载联发科 Kernel log converter
2. 安装到默认路径：`D:\Program Files (x86)\Mediatek\Kernel log converter\`

#### 自定义路径（可选）

如果安装到其他位置，设置环境变量：

```powershell
[Environment]::SetEnvironmentVariable("KERNEL_TIME_CONVERT_EXE", "D:\your\path\kernel_time_convert.exe", "User")
```

#### 验证工具

```powershell
# Python（自动检测）
python scripts/kernel_time_convert.py ".\test\kernel_log"

# PowerShell
.\scripts\kernel_time_convert.ps1 -Path ".\test\kernel_log"
```

---

## 使用说明

### 方式一：Jira 单号触发

```
分析 TOS163-25603
```

系统会自动：

1. 从 Jira 拉取工单信息
2. 下载/拷贝日志文件
3. 分析日志并匹配历史案例
4. 生成分析报告
5. 推送到飞书

### 方式二：日志文件触发

```
分析这个日志 D:\logs\wifi-log.txt
```

### 方式三：自然语言描述

```
P2P连接总是失败，GC加入GO超时
```

---

## 集成方式

本项目支持两种使用方式：**Claude Code**（原生技能系统）和 **MCP Server**（通用，支持 Cursor/Trae/VS Code）。

### 方式一：Claude Code

Claude Code 直接使用项目内置的技能系统，功能最完整。

#### 安装

```bash
npm install -g @anthropic-ai/claude-code
```

#### 使用

```bash
cd Claude-Wifi-doctor
claude
```

直接在对话中输入：

- `分析 TOS163-25603`
- `分析这个日志 D:\logs\wifi-log.txt`
- `P2P连接总是失败，GC加入GO超时`

Claude Code 会自动调用 `bug-analysis` 和 `wifi-common` 技能完成分析。

---

### 方式二：Cursor

Cursor 通过 MCP Server 调用分析功能。

#### 步骤 1：安装依赖

```bash
pip install mcp requests
```

#### 步骤 2：配置环境变量

```powershell
# Windows PowerShell
[Environment]::SetEnvironmentVariable("JIRA_USERNAME", "your_username", "User")
[Environment]::SetEnvironmentVariable("JIRA_PASSWORD", "your_password", "User")
```

#### 步骤 3：配置 MCP

在项目根目录创建 `.cursor/mcp.json`（或在 Cursor Settings → MCP 中添加）：

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

> `cwd` 填项目的实际绝对路径。

#### 步骤 4：验证

Cursor Settings → MCP 页面应显示 `wifi-doctor` 服务，5 个 tools 状态为绿色。

#### 步骤 5：使用

在 Cursor Chat 中直接说：

- `分析 OS162-40436`
- `搜索 DHCP 相关案例`
- `P2P 连接失败怎么分析`

Cursor 会自动调用 MCP tools 完成分析。

---

### 方式三：Trae

Trae 的 MCP 配置方式与 Cursor 类似。

#### 步骤 1-2：同 Cursor（安装依赖 + 配置环境变量）

#### 步骤 3：配置 MCP

在 Trae 的 MCP 设置中添加：

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

#### 步骤 4：使用

在 Trae Chat 中直接描述问题即可。

---

### MCP Tools 说明


| Tool                  | 功能                  | 示例                    |
| --------------------- | ------------------- | --------------------- |
| `get_analysis_prompt` | **分析流程提示词（首先调用）**   | 获取完整分析流程和硬规则          |
| `fetch_jira_issue`    | 拉取 Jira 工单          | `拉取 OS162-40436 工单`   |
| `kernel_time_convert` | MTK 日志时间转换          | `转换这个 kernel_log 的时间` |
| `search_cases`        | 搜索历史案例              | `搜索 DHCP 失败的案例`       |
| `search_tags`         | 搜索 TAG 知识库          | `P2P 相关的 TAG 有哪些`     |
| `get_analysis_guide`  | 获取分析指南              | `DHCP 问题怎么分析`         |
| `commit_cases`        | **提交案例到远程仓库（自动同步）** | `把新案例提交到 GitHub`      |


#### 新增功能说明

**1. 案例自动同步提交 (`commit_cases`)**

提交案例到 GitHub 时，自动检查远程仓库是否有其他人的更新：

- 先 `fetch` 远程最新状态
- 如果有新提交，自动 `pull --rebase` 同步
- 同步完成后再提交本地更改
- 如有冲突会自动报告

案例库远程仓库：`https://github.com/zxt19950521-collab/Tran-WiFi-Doctor.git`

**2. 飞书推送保密级别**

推送到飞书的报告自动设置保密级别为 **S2-内部公开**，无需手动修改。

**3. 分析流程标准化 (`get_analysis_prompt`)**

首次调用可获取完整的分析流程提示词，包含：

- 6 个标准分析步骤
- 5 条硬规则（案例必须入库、必须用户确认等）
- 报告输出格式模板

---

## 项目结构

```
Claude-Wifi-doctor/
├── .claude/
│   ├── settings.local.json      # 本地权限配置
│   └── skills/
│       ├── bug-analysis/        # Bug 分析技能（Claude Code）
│       │   ├── SKILL.md         # 技能定义
│       │   ├── modules/         # 功能模块
│       │   ├── cases/           # 案例库
│       │   ├── knowledge/       # 知识库
│       │   └── templates/       # 报告模板
│       └── wifi-common/         # WiFi 快速分析技能
├── mcp-server/                  # MCP Server（Cursor/Trae/VS Code 通用）
│   ├── server.py                # 入口
│   ├── tools/                   # 7 个 MCP 工具
│   └── resources/               # 3 个 MCP 资源
├── .mcp.json                    # MCP 服务器配置
├── jira_fetch_issue.py          # Jira 工单拉取工具
├── config.py                    # 配置管理
├── scripts/
│   ├── kernel_time_convert.ps1  # MTK 日志转换工具 (PowerShell)
│   ├── kernel_time_convert.py   # MTK 日志转换工具 (Python)
│   └── README.md                # 工具说明
├── docs/                        # 文档目录
└── README.md                    # 本文件
```

---

## 常见问题

### Q1: Jira 登录失败

**现象**：`Jira Session 登录失败`

**解决**：

1. 检查用户名密码是否正确
2. 确认 Jira 服务器地址是否可达
3. 尝试在浏览器中登录 Jira 验证账号状态

### Q2: kernel_time_convert.exe 找不到

**现象**：`kernel_time_convert.exe not found`

**解决**：

1. 确认已安装联发科 Kernel log converter
2. 检查环境变量 `KERNEL_TIME_CONVERT_EXE` 是否设置正确
3. 或将工具安装到默认路径

### Q3: 飞书推送失败

**现象**：报告生成成功但未推送到飞书

**解决**：

1. 检查 `.mcp.json` 中的飞书 MCP 地址是否有效
2. 确认飞书应用权限配置正确
3. 检查网络连接

### Q4: Python 依赖缺失

**现象**：`ModuleNotFoundError: No module named 'requests'`

**解决**：

```bash
pip install requests
```

### Q5: 案例库为空

**现象**：分析时提示无历史案例匹配

**解决**：
这是正常的，案例库需要逐步积累。每次分析完成后，系统会询问是否将本次分析入库。

---

## 环境变量汇总


| 变量名                       | 必需  | 说明       | 默认值                                                                            |
| ------------------------- | --- | -------- | ------------------------------------------------------------------------------ |
| `JIRA_USERNAME`           | 是   | Jira 用户名 | -                                                                              |
| `JIRA_PASSWORD`           | 是   | Jira 密码  | -                                                                              |
| `WIFI_DOCTOR_DATA_DIR`    | 否   | 数据存储目录   | `项目根目录/AI-result`                                                          |
| `KERNEL_TIME_CONVERT_EXE` | 否   | MTK 工具路径 | `D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe` |


---

## 联系方式

如有问题，请联系项目维护者。

---

## 许可证

内部工具，仅供团队使用。