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

### 步骤 2.5：日志完整性检查 + MTK 时间转换（硬规则）

**日志下载完成后，必须先执行此步骤，再进入分析。不可跳过。**

#### 2.5.1 日志完整性检查

扫描下载目录，确认以下 4 类日志是否存在：

| 日志类型 | 目录/文件特征 | 必需 |
|----------|--------------|------|
| **main log** | `main_log*` 或 `APLog*/main_log*` | 是 |
| **kernel log** | `kernel_log*` 或 `APLog*/kernel_log*` | 是 |
| **tcpdump** | `tcpdump*`、`*.pcap`、`*.pcapng` | 否（有则分析） |
| **空口 log** | `air*`、`sniffer*`、`*.pcap`（802.11 帧）、`connsys_picus_log*` | 否（有则必须分析） |

**检查规则：**
1. 递归扫描日志目录（含子目录），匹配文件名模式
2. 生成日志清单，标注每类日志的路径和存在状态
3. **缺失日志必须在最终报告中明确指出**，格式：
   ```
   ## 日志完整性
   - [x] main log: `path/to/main_log`
   - [x] kernel log: `path/to/kernel_log`
   - [ ] tcpdump: **未提供**
   - [ ] 空口 log: **未提供**
   ```
4. 仅有 main log 或仅有 kernel log 时，**必须注明分析局限性**

#### 2.5.2 MTK 平台识别与 kernel log 时间转换

**判断是否为 MTK 平台：**
- 检查 kernel log 中是否包含 `[wlan]`、`wlanLinkQualityMonitor`、`kalPerMonUpdate`、`MTK` 等关键字
- 或检查日志目录名是否包含 `APLog_` 前缀（MTK 联发科平台典型命名）

**如果是 MTK 平台，必须执行 kernel log 时间转换：**
1. 找到所有 `kernel_log*` 文件（排除已有的 `.localtime` 文件）
2. 对每个 kernel_log 调用转换脚本：
   ```bash
   python scripts/kernel_time_convert.py <kernel_log_file>
   ```
   或 PowerShell 版本：
   ```powershell
   .\scripts\kernel_time_convert.ps1 -Path "<kernel_log_path>"
   ```
3. 转换后生成 `.localtime` 后缀文件，时间戳变为 `MM-DD HH:MM:SS.mmm` 格式
4. **后续所有 kernel log 分析必须使用 `.localtime` 文件**，以便与 main log 时间对齐

**硬规则：**
1. **未完成日志检查不可进入分析步骤**
2. **MTK kernel_log 未转换时间不可开始分析**（log-analysis.md 硬规则 #1）
3. **缺失日志必须在报告中标注**，不可忽略

### 步骤 3：分析日志
- 按问题类型选择分析策略
- 提取关键事件和时间线
- 识别失败模式

### 步骤 3.5：加载知识文档（硬规则）

**在分析日志过程中，遇到以下关键字时必须先 Read 对应知识文档，再按文档中的规则进行量化分析。不可跳过此步骤。**

#### MTK 驱动日志（kernel log）

| 触发关键字 | 必须加载的知识文档 | 用途 |
|-----------|-------------------|------|
| `wlanLinkQualityMonitor` | `knowledge/docs/mtk-link-quality-monitor.md` | 解析 Tx/Rx/PER/Congestion 各字段，按公式计算指标，匹配场景模板 A~F |
| `scnFsmDumpScanDoneInfo` / `IdleTime` / `MdrdyCnt` / `BAndPCnt` / `CU Value` | `knowledge/docs/mtk-scan-done-info.md` | 解析扫描结果，评估信道质量，用于 ACS/P2P 选信道/拥塞排查 |
| `roamingFsm` / `apsSearchBssDesc` / `roamingFsmRunEventFail` | `knowledge/docs/mtk-roaming.md`（待建） | 漫游触发原因与流程分析 |

#### WiFi 通用分析（任何 WiFi 问题均需加载）

| 分析阶段 | 必须加载的知识文档 | 用途 |
|----------|-------------------|------|
| **TAG 提取阶段** | `knowledge/docs/wifi-tags-knowledge.md` | 按 8 大类 30+ TAG 定义和提取规则，从日志中准确提取 TAG |
| **问题分析阶段** | `knowledge/docs/wifi-analysis-guide.md` | 确定问题类型后，按文档中的详细步骤逐步分析 |
| **关键字速查** | `knowledge/docs/wifi-quick-reference.md` | 遇到不确定含义的日志关键字时快速查阅 |

#### 加载方式

```
分析 kernel log 时：
  遇到 wlanLinkQualityMonitor → Read knowledge/docs/mtk-link-quality-monitor.md
  遇到 scnFsmDumpScanDoneInfo → Read knowledge/docs/mtk-scan-done-info.md

分析任何 WiFi 问题时：
  提取 TAG 前 → Read knowledge/docs/wifi-tags-knowledge.md
  确定问题类型后 → Read knowledge/docs/wifi-analysis-guide.md
  遇到不确定关键字 → Read knowledge/docs/wifi-quick-reference.md
```

#### 硬规则

1. **不可凭记忆分析** — 必须先 Read 知识文档，再按文档中的公式/规则/模板进行分析
2. **量化指标必须计算** — 如重传率、失败率、Rx 错误率等，必须按公式计算并填入报告
3. **场景模板必须匹配** — 如 wlanLinkQualityMonitor 的场景 A~F，必须匹配并注明
4. **TAG 提取必须查表** — 按 wifi-tags-knowledge.md 的提取规则逐项匹配，不遗漏

### 步骤 3.6：绘制链路质量曲线图（硬规则）

**分析 kernel log 时，必须调用绘图脚本生成曲线图，作为报告附件插入。**

#### 脚本 1：链路质量四象限图
- **路径**: `scripts/plot_wifi_link_quality.py`
- **功能**: 从 kernel log 提取 Tput、Tx(rate)、Rx(rate)、RSSI、PER 数据，绘制四象限时间序列曲线图
- **输出**: PNG 图片（300dpi）

#### 脚本 2：Kernel Metrics 图
- **路径**: `scripts/plot_kernel_metrics.py`
- **功能**: 从 kernel log 提取 kalPerMonUpdate 吞吐量和 halDumpMsduReportStats TX 延迟，绘制三象限图（LQ / Throughput / PER）
- **输出**: PNG 图片（150dpi）

#### 文件命名规则

**必须按工单号命名，输出到工单目录：**

```bash
# 脚本 1：链路质量四象限图
python scripts/plot_wifi_link_quality.py <kernel_log.localtime> <output_dir> <ISSUE_KEY>_link_quality.png

# 脚本 2：Kernel Metrics 图
python scripts/plot_kernel_metrics.py <kernel_log.localtime> <output_dir> <ISSUE_KEY>_kernel_metrics.png

# 示例
python scripts/plot_wifi_link_quality.py AI-result/issues/TOS170-2812/logs/kernel_log.localtime AI-result/issues/TOS170-2812/ TOS170-2812_link_quality.png
python scripts/plot_kernel_metrics.py AI-result/issues/TOS170-2812/logs/kernel_log.localtime AI-result/issues/TOS170-2812/ TOS170-2812_kernel_metrics.png
```

#### 执行时机
- 步骤 3 分析日志完成后，**必须**执行此步骤
- 对每个 kernel log 文件（.localtime）各调用两个脚本
- 生成的曲线图**必须插入报告**（使用 Markdown 图片语法）

#### 报告中插入方式
```markdown
## 【链路质量曲线图】

### 链路质量四象限图
![链路质量曲线](<ISSUE_KEY>_link_quality.png)

### Kernel Metrics
![Kernel Metrics](<ISSUE_KEY>_kernel_metrics.png)
```

#### 硬规则
1. **不可跳过** — 有 kernel log 时必须绘图
2. **图片必须插入报告** — 使用 `![描述](文件名)` 语法嵌入报告正文
3. **文件名按工单号命名** — 格式 `{ISSUE_KEY}_link_quality.png` / `{ISSUE_KEY}_kernel_metrics.png`
4. **多文件分别绘制** — 如有多个 kernel log，每个单独绘制，文件名加序号 `_1` `_2`

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

## 辅助工具

### kernel_time_convert
- **路径**: `scripts/kernel_time_convert.ps1` / `scripts/kernel_time_convert.py`
- **功能**: MTK Kernel Log 时间转换
- **用途**: 将联发科平台的 kernel_log 时间戳转换为人类可读格式
- **文档**: 详见 `scripts/README.md`

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
5. **日志下载后必须执行完整性检查**（步骤 2.5）— 确认 main log / kernel log / tcpdump / 空口 log 存在状态，缺失日志必须在报告中标注
6. **MTK 平台 kernel_log 必须先转换时间再分析** — 未转换时间的 kernel_log 不可进入分析步骤
7. **仅有单一类型日志时必须注明分析局限性** — 不可仅凭 kernel log 或 main log 下完整结论

## 输出目标

### 飞书云文档
- 完整报告推送到飞书
- 返回云文档 URL

### 本地文件
- `<ISSUE_KEY>/<ISSUE_KEY>-analysis.md`
- `<ISSUE_KEY>/<ISSUE_KEY>.json`
- `<ISSUE_KEY>/logs/`
