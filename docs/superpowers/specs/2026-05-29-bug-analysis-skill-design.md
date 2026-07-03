# Bug 单分析系统设计文档

**创建日期**：2026-05-29
**版本**：1.0
**状态**：设计完成

---

## 1. 概述

### 1.1 目标

设计一个智能 Bug 单分析系统（skill），用于替代现有的 `wifi-log-diagnosis` skill，提供更完整的功能：

- 从历史 Jira 单自动提取案例
- 每次分析新问题时，报告中提供案例匹配
- 用户决定是否添加进案例仓库
- 可以根据成员提供的文档信息自动生成知识库
- 通过知识库的蒸馏学习 TAG 和案例

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| **案例驱动** | 从历史 Jira 单自动提取案例，用户审核后存入案例库 |
| **知识蒸馏** | 支持多种知识来源（文档、Wiki、代码仓库），自动提取 TAG |
| **智能匹配** | TAG + 关键词 + 语义混合匹配，提高匹配准确率 |
| **持续学习** | 案例库和知识库可独立更新，不影响 skill 流程 |
| **多触发方式** | 支持 Jira 单号、日志文件、自然语言描述触发 |

### 1.3 与现有系统的关系

```
现有系统：
├── jira-wifi-issue-pipeline (复用 Jira 拉取)
└── wifi-log-diagnosis (被替代)

新系统：
└── bug-analysis (替代 wifi-log-diagnosis)
    ├── 复用 jira-wifi-issue-pipeline 的 Jira 拉取逻辑
    ├── 增加案例匹配功能
    ├── 增加知识库功能
    └── 增加知识蒸馏功能
```

---

## 2. 整体架构

### 2.1 目录结构

```
.claude/skills/bug-analysis/
├── SKILL.md                    # 主 skill（编排逻辑）
├── modules/
│   ├── jira-fetch.md           # Jira拉取模块
│   ├── log-analysis.md         # 日志分析模块
│   ├── case-matching.md        # 案例匹配模块
│   ├── knowledge-distill.md    # 知识蒸馏模块
│   └── report-generate.md      # 报告生成模块
├── cases/                      # 案例库
│   ├── index.json              # 案例索引
│   └── ...                     # 按问题类型分类的案例文件
├── knowledge/                  # 知识库
│   ├── tags.json               # TAG定义
│   └── ...                     # 知识文件
└── templates/
    └── report-template.md      # 报告模板
```

### 2.2 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| jira-fetch | 拉取 Jira 单信息 | Jira 单号 | JSON 数据 |
| log-analysis | 分析日志，提取关键信息 | 日志文件 | 分析结果 |
| case-matching | 匹配历史案例 | 问题描述、TAG | 匹配结果 |
| knowledge-distill | 蒸馏知识，提取 TAG | 案例、文档 | TAG、模式 |
| report-generate | 生成分析报告 | 分析结果、匹配结果 | Markdown 报告 |

---

## 3. 案例库设计

### 3.1 案例索引文件 (cases/index.json)

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

### 3.2 案例文件命名规则

**命名格式**：`CASE-{序号}_{Jira单号或一句话总结}_{简短标题}.md`

- **有 Jira 单号**：`CASE-001_TOS163-25603_P2P冲突导致极速互传失败.md`
- **无 Jira 单号**：`CASE-002_GC加入GO超时10秒.md`

### 3.3 案例文件格式

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

---

## 4. 知识库与 TAG 设计

### 4.1 TAG 定义文件 (knowledge/tags.json)

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

### 4.2 知识库目录结构

```
knowledge/
├── tags.json                   # TAG定义
├── patterns/                   # 日志模式
│   ├── mtk-wifi.json          # MTK WiFi日志模式
│   ├── qcom-wifi.json         # 高通WiFi日志模式
│   └── windows-wifi.json      # Windows WiFi日志模式
├── rules/                      # 规则库
│   ├── diagnosis-rules.json   # 诊断规则
│   └── severity-rules.json    # 严重程度规则
└── docs/                       # 文档知识
    ├── wifi-standards.md       # WiFi标准知识
    └── common-issues.md        # 常见问题知识
```

---

## 5. 模块详细设计

### 5.1 jira-fetch.md (Jira拉取模块)

**职责**：拉取 Jira 单信息，提取日志路径

**复用现有逻辑**：从 `jira-wifi-issue-pipeline` 复用

**输入**：
- Jira 单号（如 `TOS163-25603`）

**输出**：
- `<ISSUE_KEY>/<ISSUE_KEY>.json`
- `<ISSUE_KEY>/logs/` 目录

**关键步骤**：
1. 执行 `python jira_fetch_issue.py <ISSUE_KEY>`
2. 读取 JSON，提取 `extracted_log_paths`
3. 下载/拷贝日志到本地

### 5.2 log-analysis.md (日志分析模块)

**职责**：分析日志，提取关键信息

**复用现有逻辑**：从 `wifi-log-diagnosis` 复用

**输入**：
- 日志文件路径
- 问题类型（可选）

**输出**：
- 时间线分析
- 关键事件提取
- 失败模式识别

**关键步骤**：
1. 日志预处理（如 MTK kernel_log 时间转换）
2. 按问题类型选择分析策略
3. 提取关键事件和时间线
4. 识别失败模式

### 5.3 case-matching.md (案例匹配模块)

**职责**：匹配历史案例，返回相似案例

**输入**：
- 问题描述
- 日志关键信息
- TAG（可选）

**输出**：
- 匹配到的案例列表
- 相似度评分
- 匹配依据

**匹配逻辑**：
1. **TAG 匹配**：提取当前问题的 TAG，与案例库 TAG 比对
2. **关键词匹配**：从日志/描述中提取关键词，与案例关键日志比对
3. **语义匹配**：使用 LLM 理解问题语义，与案例描述比对

**匹配算法**：
```
相似度 = TAG匹配权重(0.4) + 关键词匹配权重(0.3) + 语义匹配权重(0.3)
```

### 5.4 knowledge-distill.md (知识蒸馏模块)

**职责**：从案例/文档中提取 TAG 和模式

**输入**：
- 案例文件
- 文档文件
- 日志文件

**输出**：
- 新发现的 TAG
- 新的日志模式
- 更新的知识库

**蒸馏方式**：
1. **规则提取**：基于预定义规则提取（如错误码、关键词）
2. **LLM 提取**：使用 AI 从描述中提取关键特征
3. **人工审核**：新提取的内容需要人工确认

### 5.5 report-generate.md (报告生成模块)

**职责**：生成分析报告，推送到飞书

**输入**：
- 分析结果
- 案例匹配结果
- 知识库引用

**输出**：
- Markdown 报告
- 飞书云文档 URL

**报告结构**：
1. 项目匹配
2. 总体统计
3. 每次连接尝试详细分析
4. 失败原因分类
5. 关键日志
6. 问题原因
7. 流程总结
8. 建议措施
9. 案例素材（可追加到案例库）

---

## 6. SKILL.md 主文件设计

### 6.1 触发方式

**方式 1：Jira 单号触发**
```
用户：分析 TOS163-25603
```

**方式 2：日志文件触发**
```
用户：分析这个日志 D:\logs\wifi-log.txt
```

**方式 3：自然语言描述触发**
```
用户：P2P连接总是失败，GC加入GO超时
```

### 6.2 执行流程

```
步骤 1：识别输入类型
├── Jira 单号 → 执行 jira-fetch 模块
├── 日志文件 → 执行 log-analysis 模块
└── 自然语言 → 执行 case-matching 模块

步骤 2：拉取数据（如有 Jira 单号）
├── 执行 `python jira_fetch_issue.py <ISSUE_KEY>`
├── 读取 JSON，提取日志路径
└── 下载/拷贝日志到本地

步骤 3：分析日志
├── 日志预处理（MTK kernel_log 时间转换）
├── 按问题类型选择分析策略
├── 提取关键事件和时间线
└── 识别失败模式

步骤 4：匹配历史案例
├── 提取当前问题的 TAG
├── 执行 TAG 匹配
├── 执行关键词匹配
├── 执行语义匹配
└── 返回匹配结果

步骤 5：生成报告
├── 按报告模板生成 Markdown
├── 插入案例匹配结果
├── 插入知识库引用
└── 保存到本地

步骤 6：推送到飞书
├── 调用飞书 API 推送报告
└── 返回飞书云文档 URL

步骤 7：案例入库（用户确认）
├── 提取案例素材
├── 询问用户是否入库
└── 用户确认后追加到案例库
```

### 6.3 硬规则

1. **每次分析必须重新拉取 Jira**（如有 Jira 单号）
2. **案例匹配结果必须出现在报告中**
3. **新案例必须用户确认后才能入库**
4. **知识库更新必须人工审核**

---

## 7. 实现计划

### 7.1 实现阶段

| 阶段 | 内容 | 预计工作量 |
|------|------|-----------|
| **阶段 1** | 基础框架 | 2-3 天 |
| | - SKILL.md 主文件 | |
| | - jira-fetch 模块（复用现有） | |
| | - log-analysis 模块（复用现有） | |
| | - 报告模板 | |
| **阶段 2** | 案例系统 | 2-3 天 |
| | - 案例库结构 | |
| | - case-matching 模块 | |
| | - 案例入库流程 | |
| **阶段 3** | 知识系统 | 2-3 天 |
| | - TAG 系统 | |
| | - knowledge-distill 模块 | |
| | - 知识库结构 | |
| **阶段 4** | 集成测试 | 1-2 天 |
| | - 端到端测试 | |
| | - 案例匹配调优 | |
| | - 文档完善 | |

**总计**：约 7-11 天

### 7.2 扩展性设计

**存储扩展**
```
当前：本地文件系统（JSON + Markdown）
未来：可扩展到
├── SQLite 数据库（轻量级）
├── 云端存储（如飞书多维表格）
└── 专业知识图谱
```

**匹配算法扩展**
```
当前：TAG + 关键词 + 语义混合匹配
未来：可扩展到
├── 向量数据库（语义搜索）
├── 图神经网络（关系推理）
└── 联邦学习（跨团队知识共享）
```

**知识来源扩展**
```
当前：团队文档、Wiki、代码仓库
未来：可扩展到
├── 自动抓取外部技术论坛
├── 集成 AI 问答系统
└── 接入厂商技术支持知识库
```

**输出渠道扩展**
```
当前：飞书云文档
未来：可扩展到
├── Jira 评论自动回填
├── 邮件报告
├── 企业微信/钉钉通知
└── 可视化仪表板
```

---

## 8. 总结

本设计文档详细描述了 Bug 单分析系统的架构、模块设计、案例库设计、知识库设计和实现计划。系统采用模块化设计，具有良好的扩展性和可维护性，能够满足团队对 Bug 单分析的需求，并支持持续学习和知识积累。
