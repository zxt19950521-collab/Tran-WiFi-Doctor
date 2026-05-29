---
name: bug-analysis
description: >-
  智能 Bug 单分析系统，支持从 Jira 单号、日志文件或自然语言描述触发分析。
  自动匹配历史案例，生成分析报告并推送到飞书。
  案例库持续更新，支持知识蒸馏和 TAG 学习。
---

# Bug 单分析系统

## 触发方式

### 方式 1：Jira 单号触发
```
用户：分析 TOS163-25603
```

### 方式 2：日志文件触发
```
用户：分析这个日志 D:\logs\wifi-log.txt
```

### 方式 3：自然语言描述触发
```
用户：P2P连接总是失败，GC加入GO超时
```

## 执行流程

### 步骤 1：识别输入类型
- Jira 单号 → 执行 jira-fetch 模块
- 日志文件 → 执行 log-analysis 模块
- 自然语言 → 执行 case-matching 模块

### 步骤 2：拉取数据（如有 Jira 单号）
- 执行 `python jira_fetch_issue.py <ISSUE_KEY>`
- 读取 JSON，提取日志路径
- 下载/拷贝日志到本地

### 步骤 3：分析日志
- 日志预处理（MTK kernel_log 时间转换）
- 按问题类型选择分析策略
- 提取关键事件和时间线
- 识别失败模式

### 步骤 4：匹配历史案例
- 提取当前问题的 TAG
- 执行 TAG 匹配
- 执行关键词匹配
- 执行语义匹配
- 返回匹配结果

### 步骤 5：生成报告
- 按报告模板生成 Markdown
- 插入案例匹配结果
- 插入知识库引用
- 保存到本地

### 步骤 6：推送到飞书
- 调用飞书 API 推送报告
- 返回飞书云文档 URL

### 步骤 7：案例入库（用户确认）
- 提取案例素材
- 询问用户是否入库
- 用户确认后追加到案例库

## 模块引用

### jira-fetch 模块
详见 `modules/jira-fetch.md`

### log-analysis 模块
详见 `modules/log-analysis.md`

### case-matching 模块
详见 `modules/case-matching.md`

### knowledge-distill 模块
详见 `modules/knowledge-distill.md`

### report-generate 模块
详见 `modules/report-generate.md`

## 案例库

### 案例索引
`cases/index.json`

### 案例分类
- p2p-connection：P2P连接失败
- dhcp-failure：DHCP失败
- auth-failure：认证失败
- scan-failure：扫描失败
- disconnect：断开连接
- performance：性能问题

### 案例命名规则
`CASE-{序号}_{Jira单号或一句话总结}_{简短标题}.md`

## 知识库

### TAG 定义
`knowledge/tags.json`

### 日志模式
`knowledge/patterns/`

### 规则库
`knowledge/rules/`

### 文档知识
`knowledge/docs/`

## 硬规则

1. **每次分析必须重新拉取 Jira**（如有 Jira 单号）
2. **案例匹配结果必须出现在报告中**
3. **新案例必须用户确认后才能入库**
4. **知识库更新必须人工审核**

## 输出目标

### 飞书云文档
- 完整报告推送到飞书
- 返回云文档 URL

### 本地文件
- `<ISSUE_KEY>/<ISSUE_KEY>-analysis.md`
- `<ISSUE_KEY>/<ISSUE_KEY>.json`
- `<ISSUE_KEY>/logs/`
