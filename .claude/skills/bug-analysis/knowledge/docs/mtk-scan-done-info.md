# MTK Scan Done Info（scnFsmDumpScanDoneInfo）日志解析

## 来源

MTK Wi-Fi Scan FSM（SCN）模块在一次 Scan Done 时打印的统计信息，来自：
- `scnFsmDumpScanDoneInfo()`
- `tranScanCalculateCurrentBssChannel()`（传音自定义）

触发事件：`EVENT_SCAN_DONE`

用途：Roam 决策、P2P 选信道、SAP/Hotspot ACS、当前 BSS 信道评估。

---

## 日志结构

Scan Done 日志包含以下几个部分：
1. Scan Summary（扫描概要）
2. Country Code（国家码与信道列表）
3. Channel（扫描信道列表）
4. IdleTime（各信道空闲时间）
5. MdrdyCnt（各信道 MAC Rx Ready 计数）
6. BAndPCnt（各信道 Beacon+Probe 计数）
7. CU Value（各信道 Channel Utilization）
8. Scan Result（扫描结果摘要）
9. Current BSS Channel（当前连接信道评分，传音自定义）

---

## 1. Scan Summary

```
[SCN:500:F2D] Version(4)! size of ScanDone540,
used[167], free[133],
ucCompleteChanCount[18],
ucCurrentState[7],
u4ScanDurBcnCnt[72],
Seq[188]
```

### used[N] — 已用 BSS Descriptor 数
- 驱动变量：`prScanInfo->u4NumOfBssDesc`
- 含义：扫描缓存中已使用的 BSS Entry 数量
- 例：`used[167]` = 发现 167 个 AP

### free[N] — 空闲 BSS Descriptor 数
- 含义：还有多少空闲 BSS descriptor 可用
- 总容量约 300 个 BSS
- 若 free 接近 0，说明扫描缓存将满，可能丢失部分 AP 信息

### ucCompleteChanCount[N] — 完成扫描的信道数
- 驱动变量：`ucCompleteChanCount`
- 含义：此次 scan 实际完成扫描的 channel 数量
- 例：`ucCompleteChanCount[18]` = 扫描了 18 个信道

### u4ScanDurBcnCnt[N] — 扫描期间收到的 Beacon 数
- 含义：整个扫描过程中收到的 Beacon 总数
- 例：`u4ScanDurBcnCnt[72]` = 收到 72 个 Beacon

### Seq[N] — 扫描序列号
- 用于标识本次扫描的序号，便于日志关联

---

## 2. Country Code

```
Country Code = CN
Detected_Channel_Num = 18
```

- 含义：当前国家码，决定可用信道范围
- CN 允许信道：
  - 2.4G：1, 6, 9, 11, 12
  - 5G 低频：36, 40, 44, 48, 52, 56, 60, 64
  - 5G 高频：149, 153, 157, 161, 165

---

## 3. Channel（扫描信道列表）

```
Channel: 1 6 9 11 12 36 40 44 48 52 56 60 64 149 153 157 161 165
```

- 含义：此次 scan 实际扫描过的 channel 列表
- 与 `ucCompleteChanCount` 对应
- 注意：DFS 信道（52-64）可能因 radar 检测被跳过

---

## 4. IdleTime（CCA 空闲时间）

```
IdleTime: 2860 4452 5832 4207 2737 3660 4965 5755 4484 5368 5683 5833 4568 5515 5817 4026 5639 5049
```

- 驱动变量：`rChnLoadInfo.u4IdleTime`
- 单位：us 或内部 slot
- 含义：扫描 dwell time 中，信道空闲的时间
- **值越大 = 信道越干净**
- **值越小 = 信道越繁忙**

### 判断标准（经验值，需结合实际平台校准）

| IdleTime | 判定 |
|----------|------|
| > 5000 | 空闲，信道干净 |
| 3000~5000 | 中等 |
| < 3000 | 繁忙，信道拥挤 |

### 与 Channel 对应关系

按 Channel 列表顺序一一对应：
```
Channel:    1     6     9    11    12    36    40    44    48
IdleTime: 2860  4452  5832  4207  2737  3660  4965  5755  4484

Channel:   52    56    60    64   149   153   157   161   165
IdleTime: 5368  5683  5833  4568  5515  5817  4026  5639  5049
```

---

## 5. MdrdyCnt（MAC Rx Ready 计数）

```
MdrdyCnt: 145 57 3 12 57 89 96 29 167 29 22 14 129 219 187 178 26 150
```

- 驱动变量：`u4MdrdyCnt`
- 含义：MDRDY = MAC Rx Ready Count，来自 PHY MIB
- 统计：在该 channel 上收到的帧数（包括 beacon、probe response、data、control）
- **值越大 = 空中流量越多**
- **值越小 = 信道越空闲**

### 判断标准（经验值）

| MdrdyCnt | 判定 |
|----------|------|
| < 20 | 非常空闲 |
| 20~100 | 中等 |
| > 100 | 繁忙 |

### 与 Channel 对应关系

```
Channel:    1     6     9    11    12    36    40    44    48
MdrdyCnt: 145   57    3    12    57    89    96    29   167

Channel:   52    56    60    64   149   153   157   161   165
MdrdyCnt:  29    22    14   129   219   187   178    26   150
```

---

## 6. BAndPCnt（Beacon + Probe 计数）

```
BAndPCnt: 8 5 0 1 1 6 13 5 0 0 6 1 3 10 5 6 2 0
```

- 驱动变量：`u4BcnAndProbeCnt`
- 含义：该信道上收到的 Beacon + Probe Response 数量
- 反映：周围 AP 数量
- **值越大 = AP 越密集**

### 与 Channel 对应关系

```
Channel:    1     6     9    11    12    36    40    44    48
BAndPCnt:   8     5     0     1     1     6    13     5     0

Channel:   52    56    60    64   149   153   157   161   165
BAndPCnt:   0     6     1     3    10     5     6     2     0
```

---

## 7. CU Value（Channel Utilization）

```
CU Value: 0 0 0 0 0 0 0 0 94 0 96 0 56 0 75 0 97 0
```

- 驱动变量：`u4ChannelUtilization`
- 来源：802.11k BSS Load IE 或 MIB 计算
- 范围：0~255
- 转换公式：`Busy% = CU × 100 / 255`

### 判断标准

| CU Value | Busy% | 判定 |
|----------|-------|------|
| 0 | 0% | 空闲 |
| 1~63 | < 25% | 轻度负载 |
| 64~127 | 25~50% | 中度负载 |
| 128~191 | 50~75% | 高负载 |
| 192~255 | > 75% | 极度拥塞 |

### 与 Channel 对应关系

```
Channel:    1     6     9    11    12    36    40    44    48
CU:         0     0     0     0     0     0     0     0    94

Channel:   52    56    60    64   149   153   157   161   165
CU:         0    96     0    56     0    75     0    97     0
```

- channel 48：CU=94 → Busy ≈ 37%
- channel 56：CU=96 → Busy ≈ 38%
- channel 64：CU=56 → Busy ≈ 22%
- channel 153：CU=75 → Busy ≈ 29%
- channel 161：CU=97 → Busy ≈ 38%

---

## 8. Scan Result（扫描结果摘要）

```
Total:34/151
```

- 含义：上报给 Kernel 的 AP 数 / 总共缓存的 AP 数
- 部分 BSS 因过滤条件被移除
- 调用 `cfg80211_scan_done()` 完成扫描

---

## 9. 当前连接信道评估（传音自定义）

```
tranScanCalculateCurrentBssChannel
transsion idle time:4452
transsion score:10
```

- 来源：传音（Transsion）自定义逻辑
- **idle time**：当前 BSS 所在 channel 的空闲时间
- **score**：当前信道评分（0~10），10 = 最优
- 计算因子：`score = f(idle_time, channel_load, AP_num, mdrdy_count)`

---

## 10. 驱动变量映射表

| 日志字段 | 驱动变量 | 说明 |
|----------|----------|------|
| used/free | `prScanInfo->u4NumOfBssDesc` | BSS Descriptor 池使用情况 |
| ucCompleteChanCount | `ucCompleteChanCount` | 完成扫描的信道数 |
| u4ScanDurBcnCnt | `u4ScanDurBcnCnt` | 扫描期间 Beacon 总数 |
| IdleTime | `rChnLoadInfo.u4IdleTime` | CCA 空闲时间 |
| MdrdyCnt | `u4MdrdyCnt` | MAC Rx Ready 帧计数 |
| BAndPCnt | `u4BcnAndProbeCnt` | Beacon + Probe Response 计数 |
| CU Value | `u4ChannelUtilization` | Channel Utilization (0~255) |
| Scan Result Total | `cfg80211_scan_done()` | 上报/缓存的 AP 数 |

---

## 11. 信道质量综合评估方法

### 单信道评估

综合 IdleTime、MdrdyCnt、BAndPCnt、CU 四个维度：

| 优先级 | 指标 | 权重 | 说明 |
|--------|------|------|------|
| 1 | IdleTime | 高 | 越大越好，直接反映空口空闲程度 |
| 2 | CU Value | 高 | 越小越好，反映信道繁忙度 |
| 3 | MdrdyCnt | 中 | 越小越好，反映空中帧流量 |
| 4 | BAndPCnt | 中 | 越小越好，反映同频 AP 密度 |

### 信道排名示例

以本次扫描数据为例：

| 排名 | Channel | IdleTime | MdrdyCnt | BAndPCnt | CU | 综合评价 |
|------|---------|----------|----------|----------|-----|----------|
| 1 | 60 | 5833 | 14 | 1 | 0 | 极佳 |
| 2 | 56 | 5683 | 22 | 6 | 96 | 空闲但 CU 偏高 |
| 3 | 9 | 5832 | 3 | 0 | 0 | 极佳（2.4G） |
| 4 | 64 | 4568 | 129 | 3 | 56 | 中等 |
| 5 | 1 | 2860 | 145 | 8 | 0 | 繁忙 |

---

## 12. 与其他日志的交叉验证

| 现象 | 需交叉验证的日志 | 验证目的 |
|------|-----------------|----------|
| 某信道 CU 极高 | `wlanLinkQualityMonitor` 的 Congestion idle slot | 确认当前连接信道是否也拥塞 |
| 5G DFS 信道缺失 | kernel `DFS` / `radar detected` 日志 | 确认是否因雷达检测跳过 |
| 扫描 AP 数过少 | `used` vs `free` 比例 | 确认是否缓存溢出 |
| 信道评分低 | `tranScanCalculateCurrentBssChannel` score | 确认是否触发信道切换建议 |
| Roam 触发 | `roamingFsm` / `apsSearchBssDescByScore` | 确认扫描结果是否触发漫游 |

---

## 13. 典型应用场景

### 场景 A：ACS 选信道（SAP/Hotspot）
```
需求：找最空闲的信道开启 SoftAP
方法：按 IdleTime 降序 + CU 升序 + BAndPCnt 升序排列
注意：DFS 信道（52-64）需确认 radar 状态
```

### 场景 B：P2P 选信道
```
需求：找干扰最小的信道建立 P2P 连接
方法：优先选与 STA 不同的信道（MCC）或同信道（SCC）
关注：MdrdyCnt 低 + BAndPCnt 低的信道
```

### 场景 C：Roam 决策
```
需求：当前信道质量下降，寻找更好的 AP
方法：对比当前 BSS 的 score 与扫描结果中其他 AP 的信号
触发：score 连续低于阈值 → 启动漫游
```

### 场景 D：信道拥塞排查
```
需求：确认 WiFi 卡顿是否因信道拥塞
方法：对比 IdleTime/MdrdyCnt/CU 与 wlanLinkQualityMonitor 的 Congestion 数据
交叉：idle slot 小 + CU 高 + MdrdyCnt 高 → 确认拥塞
```

---

## 14. 数据流架构

```
PHY MIB (硬件寄存器)
  ↓
MDRDY Count / Idle Time / Channel Utilization
  ↓
EVENT_SCAN_DONE
  ↓
scnFsmDumpScanDoneInfo()    ← 打印本文档解析的日志
  ↓
tranScanCalculateCurrentBssChannel()  ← 传音自定义：当前信道评分
  ↓
cfg80211_scan_done()        ← 上报给 Kernel
  ↓
ACS / P2P Channel Selection / Roam Decision
```
