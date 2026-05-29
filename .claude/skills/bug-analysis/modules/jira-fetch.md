# Jira 拉取模块

## 职责
拉取 Jira 单信息，提取日志路径，下载/拷贝日志到本地。

## 复用说明
本模块复用现有 `jira-wifi-issue-pipeline` 的 Jira 拉取逻辑。

## 输入
- Jira 单号（如 `TOS163-25603`）

## 输出
- `<ISSUE_KEY>/<ISSUE_KEY>.json`
- `<ISSUE_KEY>/logs/` 目录

## 执行步骤

### 步骤 1: 拉取 Jira 信息
在仓库根目录执行：
```bash
python jira_fetch_issue.py <ISSUE_KEY>
```

### 步骤 2: 读取 JSON
读取生成的 `<ISSUE_KEY>/<ISSUE_KEY>.json`，提取以下字段：
- `summary`：问题标题
- `description`：问题描述
- `status`：状态
- `priority`：优先级
- `comments`：评论
- `extracted_log_paths`：日志路径

### 步骤 3: 下载/拷贝日志
根据 `extracted_log_paths` 下载或拷贝日志到 `<ISSUE_KEY>/logs/` 目录。

## 硬规则
1. **每次分析必须重新拉取 Jira**
2. **禁止使用过期缓存**
3. **下载失败时在报告中注明**

## 错误处理
| 情况 | 处理 |
|------|------|
| 脚本 401/403/网络错误 | 提示检查 VPN、JIRA_USERNAME/JIRA_PASSWORD |
| 日志下载失败 | 仍用 JSON 的 extracted_log_paths 尝试 UNC |
| JSON 无 UNC 且无 logs 目录 | 在报告中列出「需补充附件」|
