# Scripts 目录

本目录包含 WiFi 问题诊断系统的辅助工具脚本。

## 工具列表

### migrate_data.py

**功能**: 数据迁移工具

**用途**: 将项目中的分析数据移动到外部数据目录，防止提交到版本库。

**用法**:
```bash
python scripts/migrate_data.py
```

**说明**: 
- 自动识别项目中的工单目录（包含 .json 文件的目录）
- 将数据复制到外部数据目录（默认 `~/.wifi-doctor-data/issues/`）
- 迁移完成后，原目录可以手动删除

---

### kernel_time_convert.ps1 / kernel_time_convert.py

**功能**: MTK Kernel Log 时间转换工具

**用途**: 将联发科平台的 kernel_log 时间戳转换为人类可读的格式（MM-DD HH:MM:SS.mmm），便于与 Android main_log 进行时间对照分析。

**依赖**:
- 联发科 Kernel log converter 工具
- 默认路径: `D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe`
- 可通过环境变量 `KERNEL_TIME_CONVERT_EXE` 自定义路径

**用法**:

PowerShell 版本:
```powershell
.\scripts\kernel_time_convert.ps1 -Path ".\logs\kernel_log_6__2026_0331_224424"
```

Python 版本:
```bash
python scripts/kernel_time_convert.py ".\logs\kernel_log_6__2026_0331_224424"
```

**输出**: 在原文件同目录生成 `.localtime` 后缀的转换后文件

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `KERNEL_TIME_CONVERT_EXE` | 联发科 Kernel log converter 工具路径 | `D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe` |

---

## 快速配置指南

将此工具提供给他人时，需要配置以下内容：

### 1. 复制项目文件

```bash
# 复制整个项目目录
xcopy /E /I "D:\AI\Claude-Wifi-doctor" "目标路径\Claude-Wifi-doctor"
```

### 2. 安装 Python 依赖

```bash
pip install requests
```

### 3. 配置环境变量

```powershell
# 必需：Jira 账号
[Environment]::SetEnvironmentVariable("JIRA_USERNAME", "username", "User")
[Environment]::SetEnvironmentVariable("JIRA_PASSWORD", "password", "User")

# 可选：MTK 工具路径（如果不是默认路径）
[Environment]::SetEnvironmentVariable("KERNEL_TIME_CONVERT_EXE", "D:\path\to\kernel_time_convert.exe", "User")
```

### 4. 安装 MTK 工具

下载并安装联发科 Kernel log converter 到默认路径：
`D:\Program Files (x86)\Mediatek\Kernel log converter\`

### 5. 验证配置

```bash
# 测试 Jira 连接
python jira_fetch_issue.py --help

# 测试 MTK 工具
python scripts/kernel_time_convert.py --help
```
