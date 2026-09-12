# MTK MCC 时隙占比统计（NAF）

分析 **STA + P2P（或 SoftAP）软件 MCC** 时，必须用 kernel `qmHandleEventBssAbsencePresence` 的 **NAF** 统计 RF 占空比、时隙长度、切信道死时间。  
**禁止**仅凭「无 quota 日志」断言无时隙信息。

参考实战：`AIOT-260827-2`（传音互传信道测试）。

---

## 1. 触发关键字

| 关键字 | 说明 |
|--------|------|
| `qmHandleEventBssAbsencePresence` | NAF 事件入口 |
| `NAF:B=` / `NAF: B=` | 时隙占用/让出 |
| `kalMccBoostCheck` | MCC 吞吐 Boost（传输入口后倾斜 P2P） |
| `rlmFillSyncCmdParam` | STA/P2P 信道（`N=0` AIS/STA，`N≥1` P2P） |
| `cnmDbdc` / `DBDC Mode 0` | Mode 0 = 软件时分 MCC（非硬件 DBDC） |
| `p2pRoleFsmRunEventChnlGrant` | Grant Interval（授权窗口，≠ 100ms 级 slot） |

遇到上述关键字 → 按本文统计时隙，并打对应 TAG。

---

## 2. NAF 日志格式

```
qmHandleEventBssAbsencePresence:(QM DEBUG) NAF:B=0,A=1,F=2,T=8544
```

| 字段 | 含义 |
|------|------|
| **B** | BSS/interface 索引。须用邻近 `rlmFillSyncCmdParam` 校验：本批常见 **B=0→STA(AIS)，B=1→P2P**；勿写死，以场景为准 |
| **A** | `A=0`：该 BSS **开始占用** RF；`A=1`：该 BSS **让出** RF |
| **F / T** | 驱动附加字段；**占空比以时间戳累计为准，不以 T 代替占用时长** |

用户可读说明（投屏/互传 MCC）：NAF 持续打印，用于看当前是 STA 还是 P2P 占用射频。

---

## 3. 统计方法（硬规则）

### 3.1 占用时长（时隙）

对同一 `B`：

1. 记录 `A=0` 时刻为占用起点  
2. 到下一次同 `B` 的 `A=1`（或对端 `A=0` 抢占）为终点  
3. `occupy_ms = t_end - t_start`  
4. 丢弃异常超长段（建议 >2000ms，多为空闲/断档）与未闭合尾段  

**时隙长度**：对该 BSS 所有 `occupy_ms` 取 **中位数 / 均值**（报告至少给中位）。

### 3.2 占空比（STA:P2P）

```
STA_pct = STA_occupy_ms / (STA_occupy_ms + P2P_occupy_ms) * 100
P2P_pct = 100 - STA_pct
```

报告格式：`STA%:P2P%`（如 `50.0%:50.0%` 或 `25%:75%`）。

### 3.3 切信道死时间

一侧让出 → 对端占用之间的间隙：

- **STA→P2P**：`B=STA,A=1` 之后到 `B=P2P,A=0` 的间隔  
- **P2P→STA**：`B=P2P,A=1` 之后到 `B=STA,A=0` 的间隔  

报告两侧 **中位数**（单位 ms）。若对端 `A=0` 与本端 `A=1` 几乎同时，间隙≈0。

### 3.4 统计窗口

优先：

1. **双 B 交替** 的 dense NAF 段  
2. 与 `kalPerMonUpdate` **Tput≥1 Mbps**（或业务传输入口）时间交集  

避免把建链前长空闲、SCC 的 NoA/CTWindow 误当成跨信道 MCC duty。

### 3.5 SCC 注意

同信道（SCC）仍可能打 NAF（NoA/CTWindow），比值 **不能** 当作跨信道 MCC 时分；报告须标注 `SCC`，MCC 结论只采 **异信道** 设备。

---

## 4. 场景分类（分析时必须区分）

| 类型 | 判定 | 本批典型 |
|------|------|----------|
| **同频异信道 MCC** | STA/P2P 同 band、不同 channel | 2.4 ch6↔ch13；5G ch40↔ch48 |
| **异频 MCC** | STA/P2P 不同 band | 2.4 STA + 5G P2P |
| **SCC** | 主信道相同 | GO 侧 P2P 贴 STA 信道 |

信道来源：`rlmFillSyncCmdParam N=0/1` 的 `b=`(band) `c=`(channel) `CW_*`。

---

## 5. MCC Boost（kalMccBoostCheck）

```
kalMccBoostCheck:(INIT DEBUG) TputLv:3 Th:3 State:0->1
```

| 项 | 结论 |
|----|------|
| 触发 | 常见 `TputLv ≥ Th`（本批 Th=3），约 1s 周期检查 |
| 效果 | NAF 从约 **50:50（~100ms/~100ms）** 变为常见 **~25:75（STA~100ms / P2P~300ms）** |
| **建链期** | **不会**在 GO-neg / Join / 4-way / DHCP 打开；只在 **传输入口后** |
| 退出 | 部分日志无 `State→0`；高吞吐段常维持 `1→1` |

→ Boost **不能**用来保证 P2P **建链成功率**；建链需单独提高 P2P duty 或 SCC。

---

## 6. 经验量级（AIOT-260827-2，供对照）

| 类型 | 占空比 | 时隙中位 | 切信道中位 |
|------|--------|----------|------------|
| 同频异信道（无 Boost） | ~50%:50% | ~100ms / ~100ms | ~12–22 ms |
| 异频 + Boost | ~25%:75% | ~100ms / ~300ms | ~16–22 ms |
| 异频无 Boost | ~50%:50% | ~100ms / ~100ms | ~16–22 ms |

异频切换死时间未必明显大于同频异信道，吞吐差异更多来自 **5G 80MHz vs 2.4 HT40** 与 Boost 偏置。

---

## 7. 报告输出模板

分析含 MCC 的 P2P/互传/投屏单时，报告须含：

```markdown
### MCC 时隙（NAF）
- 类型：同频异信道 / 异频
- STA / P2P 信道：...
- 占空比 STA:P2P：xx%:yy%
- 时隙中位 STA/P2P：aa / bb ms
- 切信道中位 STA→P2P / P2P→STA：cc / dd ms
- Boost：有/无（首次 State:0→1 时刻 vs Join/DHCP 时刻）
```

---

## 8. 关联 TAG

| TAG | 何时打 |
|-----|--------|
| MCC异信道并发 | STA/P2P 不同信道 |
| MCC同频异信道 | 同 band 不同 ch |
| MCC异频并发 | 跨 2.4/5G |
| NAF时隙统计 | 已按本文完成占空比/时隙/切信道统计 |
| MCC Boost | 出现 `kalMccBoostCheck State:0->1` |
| SCC同信道 | STA/P2P 同主信道 |
| 软件MCC(DBDC Mode0) | `DBDC Mode 0` / 非硬件 DBDC |
