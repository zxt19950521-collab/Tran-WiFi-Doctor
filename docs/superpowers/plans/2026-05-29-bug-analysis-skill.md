# Bug 单分析系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个智能 Bug 单分析系统（skill），替代现有的 wifi-log-diagnosis，支持案例匹配、知识库管理和持续学习。

**Architecture:** 模块化设计，包含 5 个核心模块（jira-fetch、log-analysis、case-matching、knowledge-distill、report-generate），案例库和知识库独立存储，支持持续更新。

**Tech Stack:** Markdown（skill 文件）、JSON（数据存储）、Python（现有脚本复用）

---

## 文件结构

```
.claude/skills/bug-analysis/
├── SKILL.md                    # 主 skill（编排逻辑）
├── modules/
│   ├── jira-fetch.md           # Jira拉取模块
│   ├── log-analysis.md         # 日志分析模块
│   ├── case-matching.md        # 案例匹配模块
│   ├── knowledge-distill.md    # 知识蒸馏模块
│   └── report-generate.md      # 报告生成模块
├── cases/
│   ├── index.json              # 案例索引
│   └── p2p-connection/         # P2P连接失败案例目录
├── knowledge/
│   ├── tags.json               # TAG定义
│   ├── patterns/               # 日志模式
│   ├── rules/                  # 规则库
│   └── docs/                   # 文档知识
└── templates/
    └── report-template.md      # 报告模板
```

---

## Task 1: 创建目录结构

**Files:**
- Create: `.claude/skills/bug-analysis/` 目录结构

- [ ] **Step 1: 创建主目录**

```bash
mkdir -p .claude/skills/bug-analysis/modules
mkdir -p .claude/skills/bug-analysis/cases/p2p-connection
mkdir -p .claude/skills/bug-analysis/cases/dhcp-failure
mkdir -p .claude/skills/bug-analysis/cases/auth-failure
mkdir -p .claude/skills/bug-analysis/cases/scan-failure
mkdir -p .claude/skills/bug-analysis/cases/disconnect
mkdir -p .claude/skills/bug-analysis/cases/performance
mkdir -p .claude/skills/bug-analysis/knowledge/patterns
mkdir -p .claude/skills/bug-analysis/knowledge/rules
mkdir -p .claude/skills/bug-analysis/knowledge/docs
mkdir -p .claude/skills/bug-analysis/templates
```

- [ ] **Step 2: 验证目录创建**

```bash
ls -la .claude/skills/bug-analysis/
```

Expected output:
```
total 0
drwxr-xr-x  1 user  staff  0 May 29 10:00 .
drwxr-xr-x  1 user  staff  0 May 29 10:00 ..
drwxr-xr-x  1 user  staff  0 May 29 10:00 cases
drwxr-xr-x  1 user  staff  0 May 29 10:00 knowledge
drwxr-xr-x  1 user  staff  0 May 29 10:00 modules
drwxr-xr-x  1 user  staff  0 May 29 10:00 templates
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/bug-analysis/
git commit -m "feat: create bug-analysis skill directory structure"
```

---

## Task 2: 创建案例索引文件

**Files:**
- Create: `.claude/skills/bug-analysis/cases/index.json`

- [ ] **Step 1: 创建案例索引文件**

```json
{
  "version": "1.0",
  "last_updated": "2026-05-29",
  "cases": [],
  "categories": {
    "p2p-connection": "P2P连接失败",
    "dhcp-failure": "DHCP失败",
    "auth-failure": "认证失败",
    "scan-failure": "扫描失败",
    "disconnect": "断开连接",
    "performance": "性能问题"
  }
}
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat .claude/skills/bug-analysis/cases/index.json | python -m json.tool
```

Expected output: 格式化的 JSON 输出

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/bug-analysis/cases/index.json
git commit -m "feat: create cases index.json"
```

---

## Task 3: 创建 TAG 定义文件

**Files:**
- Create: `.claude/skills/bug-analysis/knowledge/tags.json`

- [ ] **Step 1: 创建 TAG 定义文件**

```json
{
  "version": "1.0",
  "last_updated": "2026-05-29",
  "tags": [
    {
      "id": "TAG-001",
      "name": "P2P冲突",
      "category": "p2p-connection",
      "description": "WiFi Direct P2P连接过程中发生冲突",
      "patterns": ["p2p Conflict", "P2P-GROUP-FORMATION-FAILURE"],
      "auto_extract": true
    },
    {
      "id": "TAG-002",
      "name": "GC超时",
      "category": "p2p-connection",
      "description": "GC加入GO超时",
      "patterns": ["GC未加入", "10秒超时"],
      "auto_extract": true
    },
    {
      "id": "TAG-003",
      "name": "DHCP超时",
      "category": "dhcp-failure",
      "description": "DHCP获取IP地址超时",
      "patterns": ["DHCP timeout", "Failed to get DHCP lease"],
      "auto_extract": true
    },
    {
      "id": "TAG-004",
      "name": "认证失败",
      "category": "auth-failure",
      "description": "WiFi认证失败",
      "patterns": ["CTRL-EVENT-DISCONNECTED reason=2", "Authentication failure"],
      "auto_extract": true
    }
  ],
  "extraction_rules": {
    "log_patterns": {
      "P2P冲突": ["p2p Conflict", "_onDisconnected.*Conflict"],
      "GC超时": ["GC未加入", "10秒超时", "P2PGoCreatedEvent.*unregister"],
      "DHCP失败": ["DHCP timeout", "Failed to get DHCP lease"],
      "认证失败": ["CTRL-EVENT-DISCONNECTED reason=2", "Authentication failure"]
    }
  }
}
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat .claude/skills/bug-analysis/knowledge/tags.json | python -m json.tool
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/bug-analysis/knowledge/tags.json
git commit -m "feat: create tags.json with initial TAG definitions"
```

---

## Task 4: 创建报告模板

**Files:**
- Create: `.claude/skills/bug-analysis/templates/report-template.md`

- [ ] **Step 1: 创建报告模板**

```markdown
# {问题标题} 分析报告

**测试时间**：{测试时间}
**测试设备**：{测试设备}
**测试文件**：{测试文件}
**日志来源**：{日志来源}

---

## 【项目匹配】
- **匹配项目**：{项目名称}
- **匹配案例**：{匹配到的案例，或"未匹配到完全一致案例"}
- **分析依据**：{分析依据}

---

## 【总体统计】
| 指标 | 数值 |
|------|------|
| 总尝试次数 | {总数} |
| 成功次数 | {成功数} |
| 失败次数 | {失败数} |
| 成功率 | {成功率}% |

---

## 【每次尝试详细分析】
{逐次分析，包含时间、阶段、耗时、结果}

---

## 【失败原因分类】
{失败模式分类，包含模式名称、次数、特征}

---

## 【关键日志】
{关键日志片段}

---

## 【问题原因】
**根本原因**：{根本原因}
**具体分析**：{详细分析}

---

## 【流程总结】
{成功路径和失败路径描述}

---

## 【建议措施】
1. {建议1}
2. {建议2}
3. {建议3}

---

## 【案例素材】
以下内容已按案例库格式整理，确认后可直接追加到案例库。

**标题**：{案例标题}
**现象描述**：{现象描述}
**根因结论**：{根因结论}
**排查步骤**：{排查步骤}
**关键日志**：{关键日志}
**相关案例**：{相关案例}
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/templates/report-template.md
git commit -m "feat: create report template"
```

---

## Task 5: 创建 jira-fetch 模块

**Files:**
- Create: `.claude/skills/bug-analysis/modules/jira-fetch.md`

- [ ] **Step 1: 创建 jira-fetch 模块**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/modules/jira-fetch.md
git commit -m "feat: create jira-fetch module"
```

---

## Task 6: 创建 log-analysis 模块

**Files:**
- Create: `.claude/skills/bug-analysis/modules/log-analysis.md`

- [ ] **Step 1: 创建 log-analysis 模块**

```markdown
# 日志分析模块

## 职责
分析日志，提取关键信息，识别失败模式。

## 复用说明
本模块复用现有 `wifi-log-diagnosis` 的日志分析逻辑。

## 输入
- 日志文件路径
- 问题类型（可选）

## 输出
- 时间线分析
- 关键事件提取
- 失败模式识别

## 执行步骤

### 步骤 1: 日志预处理
- MTK kernel_log 时间转换（如适用）
- 日志格式标准化

### 步骤 2: 识别问题类型
根据日志内容自动识别问题类型：
- P2P连接失败
- DHCP失败
- 认证失败
- 扫描失败
- 断开连接
- 性能问题

### 步骤 3: 提取关键事件
根据问题类型提取关键事件：
- 时间戳
- 事件类型
- 事件结果
- 相关参数

### 步骤 4: 识别失败模式
分析失败模式：
- 失败阶段（scan/auth/assoc/eapol/post-RSNA）
- 失败原因
- 失败特征

### 步骤 5: 生成时间线
按时间顺序整理关键事件，生成时间线。

## 分析策略

### P2P连接失败
1. 定位 P2P 组形成失败
2. 检查 GC 是否加入 GO
3. 分析连接超时原因
4. 检查 P2P 冲突

### DHCP失败
1. 检查 DHCPDISCOVER 是否发送
2. 检查 DHCPOFFER 是否收到
3. 检查 DHCPACK 是否收到
4. 分析 IP 配置失败原因

### 认证失败
1. 检查认证类型（PSK/EAP/SAE）
2. 分析认证失败原因
3. 检查密码/证书配置

## 硬规则
1. **MTK kernel_log 必须先转换时间**
2. **每个失败时间点都必须单独分析**
3. **区分 802.11 四次握手与应用层握手**
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/modules/log-analysis.md
git commit -m "feat: create log-analysis module"
```

---

## Task 7: 创建 case-matching 模块

**Files:**
- Create: `.claude/skills/bug-analysis/modules/case-matching.md`

- [ ] **Step 1: 创建 case-matching 模块**

```markdown
# 案例匹配模块

## 职责
匹配历史案例，返回相似案例。

## 输入
- 问题描述
- 日志关键信息
- TAG（可选）

## 输出
- 匹配到的案例列表
- 相似度评分
- 匹配依据

## 匹配算法

### 混合匹配策略
```
相似度 = TAG匹配权重(0.4) + 关键词匹配权重(0.3) + 语义匹配权重(0.3)
```

### 1. TAG 匹配（权重 0.4）
- 提取当前问题的 TAG
- 与案例库 TAG 比对
- 计算 TAG 重叠率

### 2. 关键词匹配（权重 0.3）
- 从日志/描述中提取关键词
- 与案例关键日志比对
- 计算关键词匹配率

### 3. 语义匹配（权重 0.3）
- 使用 LLM 理解问题语义
- 与案例描述比对
- 计算语义相似度

## 执行步骤

### 步骤 1: 提取当前问题特征
- 从日志中提取 TAG
- 从描述中提取关键词
- 生成问题摘要

### 步骤 2: 加载案例库
- 读取 `cases/index.json`
- 加载案例索引

### 步骤 3: 执行匹配
- TAG 匹配
- 关键词匹配
- 语义匹配
- 计算综合相似度

### 步骤 4: 返回结果
- 按相似度排序
- 返回 Top N 匹配结果
- 包含匹配依据

## 匹配结果格式
```json
{
  "matches": [
    {
      "case_id": "CASE-001",
      "title": "案例标题",
      "similarity": 0.85,
      "match_basis": {
        "tag_match": ["P2P冲突", "GC超时"],
        "keyword_match": ["p2p Conflict", "10秒超时"],
        "semantic_match": "P2P连接失败问题"
      }
    }
  ]
}
```

## 硬规则
1. **案例匹配结果必须出现在报告中**
2. **相似度低于 0.3 的不显示**
3. **最多显示 5 个匹配结果**
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/modules/case-matching.md
git commit -m "feat: create case-matching module"
```

---

## Task 8: 创建 knowledge-distill 模块

**Files:**
- Create: `.claude/skills/bug-analysis/modules/knowledge-distill.md`

- [ ] **Step 1: 创建 knowledge-distill 模块**

```markdown
# 知识蒸馏模块

## 职责
从案例/文档中提取 TAG 和模式，更新知识库。

## 输入
- 案例文件
- 文档文件
- 日志文件

## 输出
- 新发现的 TAG
- 新的日志模式
- 更新的知识库

## 蒸馏方式

### 1. 规则提取
基于预定义规则提取：
- 错误码（如 reason=2、status_code=17）
- 关键词（如 "P2P冲突"、"GC超时"）
- 日志模式（如 "CTRL-EVENT-DISCONNECTED"）

### 2. LLM 提取
使用 AI 从描述中提取：
- 问题特征
- 失败模式
- 根因关键词

### 3. 人工审核
新提取的内容需要人工确认：
- TAG 是否准确
- 模式是否有效
- 是否需要合并/拆分

## 执行步骤

### 步骤 1: 分析输入内容
- 读取案例/文档/日志
- 提取关键信息

### 步骤 2: 规则提取
- 匹配预定义规则
- 提取已知模式

### 步骤 3: LLM 提取
- 分析问题描述
- 提取新特征

### 步骤 4: 生成候选 TAG
- 合并规则提取和 LLM 提取结果
- 去重和归类

### 步骤 5: 人工审核
- 展示候选 TAG
- 用户确认/修改
- 更新知识库

## 知识库更新

### 更新 tags.json
```json
{
  "id": "TAG-XXX",
  "name": "新TAG名称",
  "category": "问题分类",
  "description": "TAG描述",
  "patterns": ["模式1", "模式2"],
  "auto_extract": true
}
```

### 更新案例索引
```json
{
  "id": "CASE-XXX",
  "title": "案例标题",
  "category": "问题分类",
  "tags": ["TAG1", "TAG2"],
  "symptom": "症状描述",
  "root_cause": "根因结论",
  "file_path": "cases/xxx/CASE-XXX_xxx.md",
  "source": "来源",
  "created_at": "2026-05-29",
  "match_count": 0
}
```

## 硬规则
1. **知识库更新必须人工审核**
2. **新 TAG 必须有明确的描述和模式**
3. **避免重复 TAG**
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/modules/knowledge-distill.md
git commit -m "feat: create knowledge-distill module"
```

---

## Task 9: 创建 report-generate 模块

**Files:**
- Create: `.claude/skills/bug-analysis/modules/report-generate.md`

- [ ] **Step 1: 创建 report-generate 模块**

```markdown
# 报告生成模块

## 职责
生成分析报告，推送到飞书。

## 输入
- 分析结果
- 案例匹配结果
- 知识库引用

## 输出
- Markdown 报告
- 飞书云文档 URL

## 报告结构

### 1. 项目匹配
- 匹配项目
- 匹配案例
- 分析依据

### 2. 总体统计
- 总尝试次数
- 成功/失败次数
- 成功率

### 3. 每次尝试详细分析
- 时间
- 阶段
- 耗时
- 结果

### 4. 失败原因分类
- 模式名称
- 次数
- 特征

### 5. 关键日志
- 失败日志
- 成功日志（对比）

### 6. 问题原因
- 根本原因
- 具体分析

### 7. 流程总结
- 成功路径
- 失败路径

### 8. 建议措施
- 排查建议
- 优化建议

### 9. 案例素材
- 可追加到案例库的格式

## 执行步骤

### 步骤 1: 加载报告模板
- 读取 `templates/report-template.md`

### 步骤 2: 填充数据
- 替换模板中的占位符
- 插入分析结果
- 插入案例匹配结果

### 步骤 3: 保存报告
- 保存到 `<ISSUE_KEY>/<ISSUE_KEY>-analysis.md`

### 步骤 4: 推送到飞书
- 调用飞书 API
- 返回云文档 URL

### 步骤 5: 更新报告
- 在报告末尾添加飞书链接

## 飞书推送

### 推送命令
```bash
python scripts/feishu_import_docx.py --file <报告路径> --title "<标题>"
```

### 推送内容
- 完整报告原文
- 不生成精简版

## 硬规则
1. **案例匹配结果必须出现在报告中**
2. **报告必须保存到本地**
3. **飞书推送必须执行**
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/modules/report-generate.md
git commit -m "feat: create report-generate module"
```

---

## Task 10: 创建主 SKILL.md 文件

**Files:**
- Create: `.claude/skills/bug-analysis/SKILL.md`

- [ ] **Step 1: 创建主 SKILL.md 文件**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/bug-analysis/SKILL.md
git commit -m "feat: create main SKILL.md for bug-analysis"
```

---

## Task 11: 创建初始案例（可选）

**Files:**
- Create: `.claude/skills/bug-analysis/cases/p2p-connection/CASE-001_TOS163-25603_P2P冲突导致极速互传失败.md`

- [ ] **Step 1: 创建示例案例**

```markdown
# CASE-001: Windows PC接收端P2P冲突导致极速互传连接失败率高

## 基本信息
- **案例ID**: CASE-001
- **分类**: p2p-connection
- **来源**: TOS163-25603
- **创建时间**: 2026-05-29
- **匹配次数**: 0

## 现象描述
- Windows PC作为接收端（GO），TECNO MEGAPAD 2作为发送端（GC）
- 14次传输尝试中7次失败，成功率仅50%
- 失败表现为两种模式：GC无法加入GO（10秒超时）或GC加入后P2P冲突断连
- 所有失败均标记 p2p Conflict: true

## 根因结论
Windows WiFi Direct P2P GO与系统WiFi管理器之间存在资源冲突，导致P2P GO不稳定（GC无法加入）或连接中途断开（p2p Conflict）。

## 排查步骤
1. 通过 _onDisconnected is p2p Conflict: true 和 _onTransportFail is p2p Conflict: true 定位所有失败事件
2. 区分两种失败模式：GC未加入（无 p2pConnect connected 日志）vs GC加入后断连
3. 对比成功和失败的时间间隔，确认失败通常发生在GO创建后10秒内或GC加入后10-27秒
4. 检查 channelId 配置，发现后半段使用 channelId=0（自动）时全部成功

## 关键日志
```
// PC接收端 - P2P冲突断连
17:45:18.194 _TransferBusinessManagerImpl,_onDisconnected is p2p Conflict : true
17:45:18.338 _TransferBusinessManagerImpl,_onTransportFail is p2p Conflict : true  wifi state : true
17:45:18.260 ReceiveController,listenReceiveStateChange : ReceiveState.failed
```

## TAG
- P2P冲突
- GC超时
- WiFi Direct
- 极速互传
- Windows
- 资源冲突

## 相关案例
- 无
```

- [ ] **Step 2: 更新案例索引**

更新 `cases/index.json`，添加新案例：

```json
{
  "version": "1.0",
  "last_updated": "2026-05-29",
  "cases": [
    {
      "id": "CASE-001",
      "title": "Windows PC接收端P2P冲突导致极速互传连接失败率高",
      "category": "p2p-connection",
      "tags": ["P2P冲突", "GC超时", "WiFi Direct", "极速互传", "Windows"],
      "symptom": "P2P连接失败，成功率50%",
      "root_cause": "Windows WiFi Direct P2P GO与系统WiFi管理器资源冲突",
      "file_path": "cases/p2p-connection/CASE-001_TOS163-25603_P2P冲突导致极速互传失败.md",
      "source": "TOS163-25603",
      "created_at": "2026-05-29",
      "match_count": 0
    }
  ],
  "categories": {
    "p2p-connection": "P2P连接失败",
    "dhcp-failure": "DHCP失败",
    "auth-failure": "认证失败",
    "scan-failure": "扫描失败",
    "disconnect": "断开连接",
    "performance": "性能问题"
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/bug-analysis/cases/
git commit -m "feat: add initial case CASE-001"
```

---

## Task 12: 验证和测试

**Files:**
- Verify: `.claude/skills/bug-analysis/` 完整结构

- [ ] **Step 1: 验证目录结构**

```bash
find .claude/skills/bug-analysis -type f -name "*.md" -o -name "*.json" | sort
```

Expected output:
```
.claude/skills/bug-analysis/SKILL.md
.claude/skills/bug-analysis/cases/index.json
.claude/skills/bug-analysis/cases/p2p-connection/CASE-001_TOS163-25603_P2P冲突导致极速互传失败.md
.claude/skills/bug-analysis/knowledge/tags.json
.claude/skills/bug-analysis/modules/case-matching.md
.claude/skills/bug-analysis/modules/jira-fetch.md
.claude/skills/bug-analysis/modules/knowledge-distill.md
.claude/skills/bug-analysis/modules/log-analysis.md
.claude/skills/bug-analysis/modules/report-generate.md
.claude/skills/bug-analysis/templates/report-template.md
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat .claude/skills/bug-analysis/cases/index.json | python -m json.tool
cat .claude/skills/bug-analysis/knowledge/tags.json | python -m json.tool
```

- [ ] **Step 3: 验证 Markdown 格式**

检查所有 .md 文件格式正确。

- [ ] **Step 4: 最终 Commit**

```bash
git add .claude/skills/bug-analysis/
git commit -m "feat: complete bug-analysis skill implementation"
```

---

## 完成

实现计划完成！所有文件已创建，目录结构已建立。

### 后续步骤
1. 测试 skill 触发方式
2. 测试案例匹配功能
3. 测试知识库更新功能
4. 完善文档
```
