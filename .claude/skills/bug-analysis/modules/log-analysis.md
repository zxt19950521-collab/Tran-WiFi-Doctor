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

## 必须分析的日志类型

**硬规则：必须充分分析以下所有可用日志后才能得出结论**

| 日志类型 | 必需 | 分析重点 |
|----------|------|----------|
| **main log** | 是 | Android 系统日志，WiFi 框架层事件、应用层行为 |
| **kernel log** | 是 | 驱动层事件、固件交互、底层错误码 |
| **tcpdump** | 是 | 网络抓包，DHCP/DNS/ARP 等协议交互 |
| **空口 log** | 否（有则必须分析） | 802.11 帧交互、认证关联过程、信号质量 |

**分析原则：**
1. **不能仅凭单一日志下结论** — 必须交叉验证多份日志
2. **有空口 log 时必须分析** — 空口日志是判断无线侧问题的关键依据
3. **时间线对齐** — 将不同日志的事件按时间戳对齐，还原完整问题现场
4. **结论必须有日志支撑** — 每个结论都必须引用具体的日志行

## 执行步骤

**前置条件：必须先完成 SKILL.md 步骤 2.5（日志完整性检查 + MTK 时间转换），再进入以下分析步骤。**

### 步骤 1: 日志预处理
- 确认步骤 2.5 已完成（日志完整性检查 + MTK 时间转换）
- 确认使用 `.localtime` 文件分析 kernel log
- 日志格式标准化
- 确认可用的日志类型清单

#### MTK Kernel Log 时间转换工具
- **脚本路径**: `scripts/kernel_time_convert.ps1`
- **功能**: 调用联发科 Kernel log converter，为 kernel_log 生成 .localtime 文件
- **用途**: 将 kernel_log 的时间戳转换为 MM-DD HH:MM:SS.mmm 格式，便于与 Android main_log 按分秒对照
- **依赖**: 需要安装联发科 Kernel log converter 工具
  - 默认路径: `D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe`
  - 可通过环境变量 `KERNEL_TIME_CONVERT_EXE` 自定义路径
- **用法**:
  ```powershell
  .\scripts\kernel_time_convert.ps1 -Path ".\logs\kernel_log_6__2026_0331_224424"
  ```
- **输出**: 在原文件同目录生成 `.localtime` 后缀的转换后文件

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

## 知识文档引用

分析 kernel 日志时，遇到以下关键字需加载对应知识文档：

### MTK 驱动日志知识

| kernel 日志关键字 | 知识文档 | 用途 |
|------------------|----------|------|
| `wlanLinkQualityMonitor` | `knowledge/docs/mtk-link-quality-monitor.md` | 解析 Tx/Rx/PER/Congestion 各字段，计算指标，匹配场景模板 |
| `scnFsmDumpScanDoneInfo` / `IdleTime` / `MdrdyCnt` / `BAndPCnt` / `CU Value` | `knowledge/docs/mtk-scan-done-info.md` | 解析扫描结果：信道空闲时间、帧计数、AP 密度、Channel Utilization，用于 ACS/P2P 选信道/拥塞排查 |
| `wpa_supplicant` EAPOL | `knowledge/docs/eapol-handshake.md`（待建） | 4 次握手流程分析 |
| `roamingFsm` / `apsSearchBssDesc` | `knowledge/docs/mtk-roaming.md`（待建） | 漫游触发原因与流程分析 |

### WiFi 通用分析知识（同步自 wifi-common）

| 知识文档 | 用途 | 使用时机 |
|----------|------|----------|
| `knowledge/docs/wifi-tags-knowledge.md` | 8 大类 30+ TAG 定义、提取规则、关联分析、问题链条 | 分析任何 WiFi 问题时，用于 TAG 提取与匹配 |
| `knowledge/docs/wifi-analysis-guide.md` | 按问题类型的详细分析步骤（P2P/DHCP/Auth/DNS/断连/性能） | 确定问题类型后，按指南逐步分析 |
| `knowledge/docs/wifi-quick-reference.md` | 常见日志关键字速查、断开原因代码速查 | 快速定位日志关键字含义 |

### TAG 知识库

| 文件 | 用途 |
|------|------|
| `knowledge/tags.json` | 87 个 TAG 定义 + 提取规则 + 7 条问题链条，用于案例匹配与 TAG 关联分析 |

### 绘图工具

| 工具 | 路径 | 用途 |
|------|------|------|
| WiFi Link Quality 绘图 | `scripts/plot_wifi_link_quality.py` | 从 kernel log 提取 Tput/Tx/Rx/RSSI/PER 绘制四象限曲线图，支持 `-m` 参数添加连接状态子图 |
| Kernel Metrics 绘图 | `scripts/plot_kernel_metrics.py` | 从 kernel log 提取 kalPerMonUpdate 吞吐量和 TX 延迟曲线 |
| 连接状态时间轴 | `scripts/plot_connection_timeline.py` | 从 main log 提取 wlan/P2P/softap 连接状态，绘制甘特图式时间轴（可单独使用） |

**多文件合并**：多个 kernel log 传入同一命令，自动按时间排序合并到一张图。

**调用方式**：
```bash
# 单文件（仅 link quality）
python scripts/plot_wifi_link_quality.py <kernel_log_file> -o <output_dir> -f <filename.png>

# 多文件合并
python scripts/plot_wifi_link_quality.py file1.localtime file2.localtime -o <output_dir> -f <filename.png>

# 带连接状态子图（推荐：一张图包含所有信息，时间对齐，线宽一致）
python scripts/plot_wifi_link_quality.py kernel.localtime -m main_log -o <output_dir> -f <filename.png>
python scripts/plot_wifi_link_quality.py kernel_1.localtime kernel_2.localtime -m main_log_1 main_log_2 -o <output_dir> -f <filename.png>

# 连接状态时间轴（单独生成）
python scripts/plot_connection_timeline.py <main_log_file> -o <output_dir> -f <filename.png>
python scripts/plot_connection_timeline.py main_log_1 main_log_2 -o <output_dir> -f <filename.png>
```

**加载方式**：
1. 分析 kernel 日志遇到 MTK 关键字时，读取对应 MTK 知识文档做量化分析
2. 提取 TAG 时，读取 `wifi-tags-knowledge.md` 或查询 `tags.json` 的提取规则
3. 确定问题类型后，读取 `wifi-analysis-guide.md` 按步骤分析
4. 遇到不确定关键字时，读取 `wifi-quick-reference.md`
5. **分析完成后，调用 `plot_wifi_link_quality.py` 生成曲线图**
6. **有 main_log 时，使用 `-m` 参数将连接状态图合并到 link quality 图中（推荐）**

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
4. **必须分析所有可用日志**（main log + kernel log + tcpdump + 空口 log），禁止仅凭单一日志下结论
5. **有空口 log 时必须分析** — 空口日志是判断无线侧问题的关键依据
