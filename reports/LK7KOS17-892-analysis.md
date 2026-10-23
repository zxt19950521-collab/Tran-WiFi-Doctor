# LK7KOS17-892 复杂待机 WiFi 底电流超标 — 分析报告（结论更新）

**工单**：LK7KOS17-892（Verified / Fixed，Blocker）
**现象**：复杂待机 11.47h 掉电 15%，平均电流 100.47 mA
**测试设备**：TECNO POVA CURVE 2 5G / LK7K，Dimensity 7100
**复现版本**：LK7k-17.0.0.032SP01(OP002PF001AZ)
**修复版本**：LK7k-17.0.0.041(OP001PF001AZ)
**日志来源**：https://sgbox.transsion.com/disk/s/agtVMK7UiMN?pwd=587951
**本次更新依据**：Jira 字段「原因分析」= `mtk的powermoniter功能未打开`；「BUG来源」= 设计方案缺失；余力睿在 .041 按原步骤验证通过

---

## 【结论先行】
> 本版相对 2026-10-08 评论做了结论对齐：机制仍是 WFSYS PSE 卡包导致整晚不睡；**产品侧根因是 PowerMonitor 默认关闭、本项目未用 cfg 打开**。修复分两层，缺一不可。

- **问题定性**：复杂待机功耗超标。软件/配置问题（设计方案缺失）。不是射频，也不是 Host 持有 driver own。
- **根本原因**：PSE 队列里有包卡住，FW 不能进 sleep。MTK 在**固件**里加了 workaround：PSE 非空持续 **60s** 则丢掉卡包。该检测**默认关闭**，必须用 `wifi.cfg` 的 `PowerMonitorEnable 1` 打开。LK7K 没开这个开关，workaround 不跑，卡包一直在，WFSYS 整晚 0 次 HW sleep，conn 堵住系统 LPM，待机约 100 mA。
- **修复原文（10-14 工单备注）**：
  > Add workaround to detect PSE non-empty case (keep 60s) to drop the packet which stuck at PSE queue  
  > 在偵測到 PSE 佇列為非空的狀況時（持續 60 秒），丟棄卡在 PSE 佇列中的封包。  
  > **修改是在固件里的，默认不打开，所以需要使用 cfg 开关将其打开。**
- **关键证据**：① 原因分析：`mtk的powermoniter功能未打开`；产品 CL 只改 cfg：[1618607](https://gerrit.transsion.com/c/TRAN_CODE/vendor/transsion/projects/+/1618607) `PowerMonitorEnable 1`。② 原日志 6 份 `<FW>PWR INFO` 全部 `HW enter sleep count = 0`，`REASON_PSE_NOT_EMPTY` 占 97%～99.9%；SPM 486/486 次 `System LPM is blocked by conn`。
- **影响范围**：WiFi 复杂待机底电流约 100 mA。dup：LK7KOS17-893/894/895/896/897。`.041` 已 Verified PASS。
- **首要建议**：FW 补丁和 `PowerMonitorEnable 1` 必须一起合。只合固件、不开 cfg，本单会原样复现。`.041` 已两项到位并验证，不必再把 ALPS11689618 当未修项。

---

## 【日志完整性】
- [ ] main log: **本次未重新下载**（原分析已用，日志在 sgbox 链接中）
- [ ] kernel log: **本次未重新下载**（原分析已用）
- [ ] tcpdump: **未提供**
- [ ] 空口 log / picus: **未提供**

**分析局限性**：本次是按问题单「原因分析 / 验证结果」更新结论，不再重跑 kernel 时间转换和曲线图。机制数据来自 2026-10-08 对原包的提取。无 picus，无法指出 PSE 卡在哪个队列/端口；不影响「开关未打开」这一产品根因。

---

## 【项目匹配】
- **匹配项目**：LK7K / MTK Connsys，复杂待机 WiFi 子系统不睡眠
- **匹配案例**：
  | 案例 | 相似度 | 说明 |
  |------|--------|------|
  | **CN6OS16-241**（未入库） | **高（同机理）** | 同样 WFSYS 整段 0 睡眠、`REASON_PSE_NOT_EMPTY`；合入 FW [gerrit 1518741](https://gerrit.transsion.com/c/MTK_CODE/alps/vendor/mediatek/proprietary/hardware/connectivity/firmware/wlan/+/1518741) + `PowerMonitorEnable 1` 后，电流 34.81 mA → 21.57 mA PASS |
  | PWR-001 / CASE-031（LJ9OS16-81） | 中（约 40%） | 同为 `LPM is blocked by conn` + `26M_off_pct=0`，但是 **BT 扫描** 阻塞，WiFi 侧正常 |
  | PWR-002 / CASE-036（CN6OS16-2328） | 低（约 30%） | WiFi 阻塞休眠，但是 **Zoom 下行包唤醒**，不是 PSE 卡包 |
- **分析依据**：Jira 原因分析字段、Fix Link、Verify Version；原日志 SPM / consys_power_state / `<FW>PWR INFO`

---

## 【总体统计】

口径：原包灭屏待机窗口约 21:30:54～08:58:49（约 11.5h）。`.041` 复测按原步骤，测试结论 PASS，本表不再重复电流。

| 指标 | 数值 |
|------|------|
| 复现版本平均电流 | 100.47 mA（11.47h 掉电 15%） |
| SPM：AP 挂起被 conn 阻塞 | 486/486 次，`26M_off_pct = 0`，`vcore_off_pct = 0` |
| AP 挂起占比 | 97.4%（不是 AP 频繁唤醒） |
| consys `[total] wf` | 首尾不变：`wf:151105.974,98587`（整段 0 睡眠） |
| consys bt / gps | bt 睡眠约 95.4%，gps 约 100%，正常 |
| `<FW>PWR INFO` | 6 份，全部 `HW enter sleep count = 0` |
| `REASON_PSE_NOT_EMPTY` 占比 | 97.0%～99.9%（例：00:34:08 份 99.25%） |
| SETSUSPENDMODE | 21:30:54 已下发 |
| FW OWN:1 | 1304 次，正常归还；conn_wakeup 成对，最长 4.3 ms |
| scan-only 期间流量 | wlan0 / ccmni 0 包；仅 2 次单次扫描，约 1.2 s，无 PNO |
| 修复版本 | LK7k-17.0.0.041，Verified PASS（2026-10-21，余力睿） |

---

## 【工单备注对齐（本次修订要点）】

问题单已填字段，与 10-08 评论的差异如下。

| 字段 | 问题单取值 | 对结论的含义 |
|------|------------|--------------|
| 原因分析 | `mtk的powermoniter功能未打开` | **产品根因是配置开关，不是「FW 尚未修复」** |
| BUG来源 | 设计方案引入 / 设计方案缺失 | 方案里漏了打开 PowerMonitor |
| Fix Way | 修改代码 | `wifi.cfg` 增加 `PowerMonitorEnable 1` |
| Fix Link/s | [gerrit 1618607](https://gerrit.transsion.com/c/TRAN_CODE/vendor/transsion/projects/+/1618607) | 只改 cfg，不改 Host driver |
| 自检结果 | PASS | 修复者自检通过 |
| Fix Version / Verify Version | LK7k-17.0.0.041(OP001PF001AZ) | 原步骤复测 Verified |
| 状态 | Verified / resolution=Fixed | 关闭态，无需继续跟 eService 作为未修项 |

10-08 评论把责任方向写成「WiFi FW（MTK）」，并列出「先核对是否已合 FW + cfg」。后续合入和验证证明：**FW workaround 已在固件中，缺的是 cfg 开关**。因此结论改为与「原因分析」一致。

---

## 【每次尝试详细分析】

### 1) 复现包（.032SP01）机制链

```
灭屏复杂待机（WiFi + 数据）
    ↓
USF 夜间优化 22:09:52 setWifiEnabled(false)
但 GMS wifi_scan_always_enabled=1
    ↓
wlan0 进入 ROLE_CLIENT_SCAN_ONLY，WFSYS 未下电复位
    ↓
FW PSE 包缓冲区长期不空（REASON_PSE_NOT_EMPTY）
PowerMonitor 未开 → 60s 卡包丢弃 workaround 不跑
    ↓
HW enter sleep count = 0（整晚）
    ↓
consys wf 累计睡眠 0；SPM: LPM blocked by conn
    ↓
待机 ~100 mA
```

### 2) 修复：固件 workaround + cfg 开关（两项缺一不可）

工单 10-14 备注（修复说明原文）：

> Add workaround to detect PSE non-empty case (keep 60s) to drop the packet which stuck at PSE queue  
> 在偵測到 PSE 佇列為非空的狀況時（持續 60 秒），丟棄卡在 PSE 佇列中的封包。  
> 修改是在固件里的，默认不打开，所以需要使用 cfg 开关将其打开。

| 层 | 改什么 | 作用 | 本单状态 |
|----|--------|------|----------|
| 固件 | PSE 非空保持 60s → 丢弃卡包 | 自愈睡眠条件 | 已在 WLAN FW 中（同 CN6 的 gerrit 1518741 一类）；**默认关闭** |
| 配置 | `wifi.cfg`：`PowerMonitorEnable 1` | 把上述检测打开 | .032SP01 **未开**（根因）；[1618607](https://gerrit.transsion.com/c/TRAN_CODE/vendor/transsion/projects/+/1618607) 合入后 .041 **已开** |

2026-10-21 余力睿：`LK7k-17.0.0.041(OP001PF001AZ)` 按原问题步骤验证 → Verified。

---

## 【失败原因分类】

| 模式 | 次数 | 特征 |
|------|------|------|
| PowerMonitor 未打开导致 PSE 卡包无法自愈 | 整晚 1 段 | `HW sleep=0` + `REASON_PSE_NOT_EMPTY` 主导 + consys wf 0 睡眠 |
| Host/驱动持有 own | 0 | FW OWN 正常归还，排除 |
| 灭屏后仍有业务流量 | 0 | scan-only 期间 0 包，排除 PWR-002 类 |
| BT/GPS 阻塞 conn | 0 | bt/gps 睡眠正常，排除 PWR-001 类 |

---

## 【关键日志】

来自 2026-10-08 原包提取（本次未重抓）。

**SPM（系统被 conn 静态堵住，不是频繁唤醒）**

```
System LPM is blocked by conn     # 486/486
26M_off_pct = 0, vcore_off_pct = 0
AP suspend 占比 97.4%
scan-only 期间 CONN2AP 唤醒 = 0
```

**conninfra（wf 整段 0 睡眠，bt/gps 正常）**

```
consys_power_state  21:30:56 ~ 08:58:48  共 578 条
每轮 wf / conninfra = 0.000,0
[total] wf:151105.974,98587
        conninfra:150745.151,107052   # 首尾不变
bt 睡眠 95.4%，gps ~100%
```

**WiFi FW（睡眠条件不满足，主因 PSE 非空）**

```
<FW>PWR INFO  6 份，覆盖 21:30:54 ~ 08:58:49
每份 HW enter sleep count = 0
REASON_PSE_NOT_EMPTY 占 97.0% ~ 99.9%
例 00:34:08：Total wake 10,993,894 ms，PSE_NOT_EMPTY 10,911,433 ms（99.25%）
ePwrMode=2 Fast PS，LowLatency CAM:0x0
SETSUSPENDMODE 已于 21:30:54 下发
```

**放大因素（不是根因）**

```
22:09:52 USF setWifiEnabled(false)
wifi_scan_always_enabled=1 → ROLE_CLIENT_SCAN_ONLY
WFSYS 未下电，异常被带到整晚
```

---

## 【PSE 队列怎么理解】

**PSE 队列是 WiFi 芯片里面的包中转仓库。** 包还堆在仓库里，固件就不让芯片睡觉。

在 MTK 的 WFSYS 里，PSE（Packet Switch Engine，包交换引擎）是一块硬件：Host、MAC、MCU 之间的包不直送，先在 PSE 里按**页（page）**占用缓冲区，再从不同端口/队列转出去。可以把它想成芯片内部的快递分拣中心：

```
手机 AP（Host）  ←→  HIF 口  ←→  PSE 仓库  ←→  LMAC 口  ←→  空口
                                      ↑
                                   MCU/固件也从这里取包
```

队列「非空」= 仓库里还有页没释放：包收进来了，但没被送走、也没被丢掉。固件进 sleep 的条件之一就是 **PSE 必须空**。所以 `<FW>PWR INFO` 里会报 `REASON_PSE_NOT_EMPTY`：不是外面还有流量，而是**芯片内部还压着包**。

本单对得上这一点：

- Host 已经 `SETSUSPENDMODE`，`FW OWN` 也还回去了，wlan0 在 scan-only 下 **0 包**。
- 外面看起来该闲了，但 6 份 PWR INFO 全是 `HW enter sleep count = 0`，醒着的时间 97%～99.9% 都记在 `REASON_PSE_NOT_EMPTY` 上。
- 同类 CN6OS16-241，MTK 确认过：加密包解密后没送给 Host，滞留在 WFSYS，PSE 就空不了。

所以「卡在 PSE 队列」不是 Android 的 socket 队列，也不是 `wlan0` 的内核 qdisc，而是 **WiFi 固件/硬件内部的缓冲页没释放**。没有 picus/coredump 时，只能知道「仓库非空」，指不出是哪个口、哪条队列。

PowerMonitor 那 60 秒 workaround 做的就是：仓库持续非空满 60 秒，把卡住的包丢掉，页才能还回去，固件才允许 sleep。这个检测写在固件里，**默认关**；`PowerMonitorEnable 1` 只是把这扇清理门打开。

---

## 【问题原因】

**根本原因（与问题单备注对齐）**：卡包在 PSE 队列，FW 不能睡。固件 workaround 是「PSE 非空持续 60s 则丢弃卡包」，但**默认不打开**。LK7K 未在 `wifi.cfg` 写 `PowerMonitorEnable 1`，检测不跑，卡包不丢，整晚 `REASON_PSE_NOT_EMPTY`。

**机制（10-08 日志，仍然成立）**：

1. 直接阻塞点是 **WFSYS 不睡眠**，不是 AP、不是 BT、不是 modem。
2. FW 自报主因是 **PSE 缓冲区长期不空**（`REASON_PSE_NOT_EMPTY`），Host 无收发、own 已归还，说明卡包在 WFSYS 内部。
3. 同机理 CN6OS16-241 已用「FW 补丁 + PowerMonitorEnable 1」修过。本单产品动作只合了 cfg，是因为对应 FW 已带 workaround、缺的是开关。
4. scan-always 把异常从「关 WiFi 应下电」放大成「scan-only 整晚挂着」，是放大因素，不是根因。

**具体分析**：10-08 评论把责任写成 WiFi FW（MTK），并挂 eService ALPS11689618，是当时还没确认 cfg 是否打开。10-19 填写原因分析、合入 1618607 之后，产品结论应改为 **设计方案缺失：PowerMonitor 未打开**。`.041` 已验证，eService 不再作为本单打开项。

---

## 【链路质量曲线图】

本次为结论更新，未重新下载 kernel/main log，**不生成** `LK7KOS17-892_link_quality.png` / `_kernel_metrics.png` / `_timeline.png`。本单是灭屏待机 0 吞吐场景，曲线图对根因（PowerMonitor 开关）帮助有限。

---

## 【流程总结】

**失败路径（.032SP01）**

```
复杂待机灭屏 → scan-always 保持 WFSYS → PSE 卡包
→ PowerMonitor 关闭，60s 丢包不执行
→ HW 永不 sleep → conn 阻塞 LPM → ~100 mA
```

**成功路径（.041）**

```
固件已含：PSE 非空 keep 60s → drop stuck packet
+ wifi.cfg PowerMonitorEnable 1（把默认关闭的检测打开）
→ 卡包被丢掉 → WFSYS 可睡眠 → conn 释放 → 系统可 LPM
→ 原步骤复测 PASS / Verified
```

---

## 【建议措施】

1. **本单**：已在 LK7k-17.0.0.041 Verified，关闭即可。
2. **防回归**：MTK 平台新项目 `wifi.cfg` 默认带 `PowerMonitorEnable 1`，与 FW 补丁（gerrit 1518741 一类）一起合入，不要只合固件。
3. **排查口令**：复杂待机 `LPM blocked by conn` 且 `wf` 累计睡眠为 0 时，先看 `<FW>PWR INFO` 是否 `REASON_PSE_NOT_EMPTY`，再查 `adb shell cat /vendor/firmware/wifi.cfg | grep PowerMonitor`。
4. **同类 dup**：LK7KOS17-893/894/895/896/897 与本单重复，随 .041 一起关闭。

---

## 【案例素材】

以下内容已按功耗专题格式整理，确认后可追加为 PWR-003。

**标题**：LK7K 复杂待机 PowerMonitor 未打开导致 WFSYS 整晚不睡
**现象描述**：WiFi 复杂待机 11.47h 掉电 15%，平均 100.47 mA；SPM 全部 `LPM blocked by conn`，consys wf 0 睡眠
**根因结论**：固件 workaround（PSE 非空持续 60s 丢弃卡包）默认关闭；`wifi.cfg` 未开 `PowerMonitorEnable 1`，卡包不丢，`REASON_PSE_NOT_EMPTY` 导致 HW 永不 sleep
**排查步骤**：SPM → consys_power_state 看 wf 是否 0 睡眠 → `<FW>PWR INFO` 看 PSE_NOT_EMPTY → 查 wifi.cfg PowerMonitorEnable
**关键日志**：`HW enter sleep count = 0`；`REASON_PSE_NOT_EMPTY` 占 99%；`[total] wf` 首尾不变
**相关案例**：CN6OS16-241（同机理已修）；PWR-001（conn 阻塞但在 BT 侧）；PWR-002（WiFi 阻塞但是应用下行）
**修复**：gerrit 1618607；验证版本 LK7k-17.0.0.041

---

## 【同步记录】

- 本地报告：`AI-result/issues/LK7KOS17-892/LK7KOS17-892-analysis.md`
- Jira 评论：结论更新 id=23253125；workaround 原文补发见本次新评论
- 飞书：当前仓库没有 `scripts/feishu_import_docx.py`，本次未推送云文档
