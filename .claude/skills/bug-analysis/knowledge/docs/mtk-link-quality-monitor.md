# MTK wlanLinkQualityMonitor 日志解析

## 日志格式

```
[wlan]wlanLinkQualityMonitor:(SW4 INFO) Link Quality:
  Tx(rate:X, total:Y, retry:Z, fail:W, RTS fail:A, ACK fail:B),
  Rx(rate:X, total:Y, dup:Z, error:W),
  PER(X),
  Congestion(idle slot:X, diff:Y, AwakeDur:Z)
```

此日志由 MTK WLAN Driver 的 `wlanLinkQualityMonitor()` 函数输出，通常每隔几秒打印一次，统计当前链路质量。

---

## 1. Tx（发送链路）

### rate — 当前发送 PHY 速率
- 驱动变量：`u2CurTxRate`
- 单位：Mbps
- 来源：RA（Rate Adaptation）模块的当前 MCS 对应速率
- 示例：`rate:390` = 390 Mbps

**PHY Rate 与 MCS/BW/NSS 对应关系（参考）：**

| MCS | BW | NSS | PHY Rate |
|-----|-----|-----|----------|
| MCS7 | 80MHz | 1SS | 390 Mbps |
| MCS9 | 40MHz | 2SS | 400 Mbps |
| MCS7 | 80MHz | 2SS | 722 Mbps |
| MCS9 | 80MHz | 2SS | 866 Mbps |
| MCS7 | 20MHz | 1SS | 65 Mbps |
| MCS0 | 20MHz | 1SS | 6.5 Mbps |

### total — 累计发送包数
- 驱动变量：`u4TxTotalCnt`
- 单位：MPDU packets
- 示例：`total:873478`

### retry — 重传次数
- 驱动变量：`u4TxRetryCnt`
- 含义：首次发送失败后重新发送成功的次数
- 重传率 = retry / total
- 判断标准：
  - < 5%：优秀
  - 5~10%：正常
  - 10~20%：开始恶化
  - \> 20%：较差
  - \> 40%：严重

### fail — 发送最终失败次数
- 驱动变量：`u4TxFailCnt`
- 含义：经过多次 retry 后仍然没有成功、最终被丢弃的 MPDU 数
- 包含：ACK timeout + Excessive retry + 其他
- 失败率 = fail / total
- 判断标准：
  - < 5%：正常
  - 5~10%：偏高
  - \> 10%：异常

### RTS fail — RTS 帧未收到 CTS
- 驱动变量：`u4TxRtsFailCnt`
- 过程：发送 RTS → 未收到 CTS → RTS fail++
- 原因：
  - **Hidden node**：两个 STA 相互听不到，RTS/CTS 机制失效
  - **信道干扰**：RTS 帧损坏，对端未正确接收
  - **对端忙碌**：GO/GC 正忙（省电/处理中）
- 关联：RTS fail 高 → 重传率高

### ACK fail — 发送后未收到 ACK
- 驱动变量：`u4TxAckFailCnt`
- 过程：发送 DATA → 对端接收 → 应回 ACK → ACK timeout → ACK fail++
- 原因：
  - **RSSI 差**（< -70 dBm）：上行链路预算不足
  - **干扰**：CRC error，ACK 帧损坏
  - **MCC 切信道**：对端短时间不在当前 channel
  - **GO 省电（NoA）**：Notice of Absence，GO 周期性休眠
  - **BT 共存**：蓝牙共存导致时隙被占用
- **关键指标**：ACK fail 高 = 链路质量差的强信号

---

## 2. Rx（接收链路）

### rate — 当前接收 PHY 速率
- 驱动变量：`u2CurRxRate`
- 单位：Mbps
- 含义：对端发送给本机的速率
- 示例：`rate:722` = 80MHz 2SS MCS7 ≈ 722 Mbps

### total — 累计接收包数
- 驱动变量：`u4RxTotalCnt`
- 单位：成功收到的 MPDU 数量

### dup — 重复包数
- 驱动变量：`u4RxDupCnt`
- 正常值：极少（< 0.1%）
- 来源：Block Ack 重传机制
  ```
  发送端发: 1 2 3 4
  接收端收: 1 3 4（丢 2）
  BA 请求: 需要 packet 2
  发送端重发: 2 3 4
  结果: 3、4 成为 duplicate
  ```
- 数量少属正常，数量多说明重传频繁

### error — CRC/FCS 错误包数
- 驱动变量：`u4RxErrCnt`
- 含义：PHY 收到信号（RSSI OK），但 Frame Check Sequence 校验失败
- 错误率 = error / total
- **关键指标**
- 判断标准：
  - < 5%：正常
  - 5~15%：偏高，信道质量下降
  - 15~30%：严重，高 PER
  - \> 30%：极端恶劣
- 包括：
  - OFDM decode error
  - CRC error
  - interference（干扰）
  - SNR 过低
  - MCS 过高无法稳定解调
- 原因分类：
  - **同频干扰**：2.4G（蓝牙/USB3.0/微波炉/邻AP）；5G（同频AP/DFS雷达）
  - **RSSI 低**（< -70 dBm）
  - **MCS 过高**：高阶调制在弱信号下无法稳定解调
  - **天线问题**：接触不良/PIFA匹配差/屏蔽罩影响

---

## 3. PER — Packet Error Rate

- 驱动变量：`u4TxPer`
- 格式：`PER(X)`
- 通常计算：`PER = TxFail × 100 / TxTotal`
- **平台差异**：MTK 不同平台（MT6631、MT6989、MT6879、MT7668）实现略有不同，有些统计最近窗口 PER 而非累计 PER
- **PER(0) 不代表链路正常**：
  - PER 是短时 Tx PER 统计，反映当前采样窗口的瞬时状态
  - fail/ACK fail/Rx error 是累积值，两者时间尺度不同
  - 例：`PER(0)` 但 `fail=84450, ACK fail=51523, Rx error=38.5%` → 链路实际已严重恶化

---

## 4. Congestion — 信道拥塞统计（CCA）

CCA（Clear Channel Assessment）统计，反映信道繁忙程度。

### idle slot — 空闲时隙数
- 驱动变量：`u4IdleSlotCount`
- 含义：检测到 channel idle 的 slot 数
- **值大 = 信道不繁忙**（如 201375448 → 信道空闲）
- **值小 = 信道繁忙**（如 604/985 → 介质被占用）
- 判断方法：对比同时间段的 diff 值，idle/diff 比值越高说明信道越空闲

### diff — 统计周期
- 驱动变量：`u4DiffTime`
- 单位：us（微秒）
- 示例：`diff:10295` ≈ 10 ms
- 含义：两次统计之间的时间窗口

### AwakeDur — WiFi 唤醒时间
- 驱动变量：`u4AwakeDuration`
- 单位：us（微秒）
- 示例：`AwakeDur:4070346` ≈ 4.07 秒
- 含义：WiFi MAC 保持 awake 状态的时间
- 用途：Power Save 分析、Channel Utilization 计算

---

## 5. 驱动变量映射表

| 日志字段 | 驱动变量 | 说明 |
|----------|----------|------|
| Tx(rate) | `u2CurTxRate` | 当前发送 PHY Rate |
| Tx(total) | `u4TxTotalCnt` | 累计发送 MPDU 数 |
| Tx(retry) | `u4TxRetryCnt` | MAC 层重传次数 |
| Tx(fail) | `u4TxFailCnt` | 发送最终失败数 |
| RTS fail | `u4TxRtsFailCnt` | RTS→CTS 失败数 |
| ACK fail | `u4TxAckFailCnt` | ACK 超时数 |
| Rx(rate) | `u2CurRxRate` | 当前接收 PHY Rate |
| Rx(total) | `u4RxTotalCnt` | 累计接收 MPDU 数 |
| dup | `u4RxDupCnt` | 重复包数 |
| error | `u4RxErrCnt` | CRC/FCS 错误包数 |
| PER | `u4TxPer` | 发送包错误率 |
| idle slot | `u4IdleSlotCnt` | 空闲时隙数 |
| diff | `u4DiffTime` | 统计周期(us) |
| AwakeDur | `u4AwakeDuration` | WiFi 唤醒时长(us) |

---

## 6. 综合判断模板

### 场景 A：信道拥塞型
```
特征：retry 高 + fail 高 + idle slot 小
结论：信道繁忙，退避竞争激烈
建议：换信道 / 减少同频干扰
```

### 场景 B：信号质量型
```
特征：PHY rate 高 + ACK fail 高 + Rx error 高 + idle slot 大
结论：信道不忙但无线质量差（弱信号/干扰/天线问题）
建议：靠近AP / 检查天线 / 降低MCS / 缩窄带宽
```

### 场景 C：Hidden Node 型
```
特征：RTS fail 高 + ACK fail 高 + idle slot 大
结论：存在 hidden node，RTS/CTS 机制失效
建议：启用 RTS/CTS / 减少覆盖范围
```

### 场景 D：上行链路失效型
```
特征：ACK fail ≈ fail（几乎全部失败都是无ACK）
结论：STA→AP 上行帧无法到达，典型上行RF问题
建议：检查TX功率/天线/PA，对比参考机
```

### 场景 E：强信号高PHY但无线质量差型（P2P/投屏典型）
```
特征：PHY rate 高（Tx 390, Rx 722）+ Rx error 极高（38.5%）+ ACK fail 高 + idle slot 大（信道不忙）
结论：不是信道拥塞，而是无线质量差
根因排查（按优先级）：
  1. RSSI 弱（<-65dBm）
  2. 80MHz 带宽过宽 → 降为 40MHz
  3. SCC/MCC 共存切信道
  4. 同频 AP 干扰
  5. 天线隔离问题（横屏投屏手握遮挡）
  6. GO 端 NoA 节能
  7. 蓝牙共存（BT Coexist）
建议：降带宽 80→40MHz / 检查天线 / 降低MCS / 排查同频干扰
```

### 场景 F：PER(0) 误导型
```
特征：PER(0) 但 fail/ACK fail/Rx error 累积值很高
结论：PER 只反映短时窗口，累积指标才是真实链路质量
关键：永远不要仅凭 PER(0) 判断链路正常，必须交叉看 fail/ACK fail/Rx error
```

---

## 7. 关键公式

```
重传率 = retry / total × 100%
失败率 = fail / total × 100%
ACK失败占比 = ACK fail / fail × 100%
Rx错误率 = error / total × 100%
RTS失败率 = RTS fail / (total - fail + RTS fail) × 100%
```

### 恒等式验证

```
Tx fail = RTS fail + ACK fail（+ 其他少量失败）
```

此恒等式可用于验证数据一致性。若 `fail >> RTS fail + ACK fail`，说明存在非 RTS/ACK 的其他失败类型。

---

## 8. 数值计算示例

以这条实际日志为例：
```
Tx(rate:390, total:873478, retry:70581, fail:84450, RTS fail:32927, ACK fail:51523)
Rx(rate:722, total:1025381, dup:989, error:394533)
PER(0)
Congestion(idle slot:201375448, diff:10295, AwakeDur:4070346)
```

| 指标 | 计算 | 结果 | 判定 |
|------|------|------|------|
| 重传率 | 70581/873478 | **8.1%** | 正常偏高 |
| 失败率 | 84450/873478 | **9.7%** | 偏高 |
| ACK fail 占比 | 51523/84450 | **61%** | ACK fail 是主要失败原因 |
| Rx 错误率 | 394533/1025381 | **38.5%** | 极高，信道质量极差 |
| RTS fail 占比 | 32927/84450 | **39%** | RTS 也大量失败 |

**综合判断**：
- PHY rate 看起来好（Tx 390, Rx 722），但 Rx error 38.5% 说明空口充满可听到却解不出的帧
- 信道不拥塞（idle slot 大 = 201375448）
- PER(0) 是短时窗口值，不代表链路正常
- 问题本质是**无线质量差**，属于场景 E

---

## 9. 与其他日志的交叉验证

| 现象 | 需交叉验证的日志 | 验证目的 |
|------|-----------------|----------|
| ACK fail 高 | kernel `get_station` RSSI / MovAvg_rssi | 确认信号强度 |
| Rx error 高 | kernel `roamingFsm` 漫游触发 | 确认是否触发漫游 |
| fail 高 | main_log `WifiNetworkQuality` 吞吐量 | 确认应用层影响 |
| RTS fail 高 | 连续多条 `wlanLinkQualityMonitor` 对比趋势 | 确认是持续还是突发 |
| PHY rate 低 | kernel `mtk_cfg80211_get_station` link speed | 确认实际协商速率 |
| SCC/MCC | P2P interface + STA interface 的 channel/freq | 确认共存模式 |

---

## 10. P2P / Miracast 投屏场景专项分析

当 `wlanLinkQualityMonitor` 出现在 P2P（WiFi Direct / Miracast）链路时，需额外关注：

### 典型问题模式

| 模式 | 特征 | 可能原因 |
|------|------|----------|
| 高 PHY + 高 PER | rate 正常但 error/fail 高 | MCS 过高，降带宽 80→40MHz |
| ACK fail 高 + idle slot 大 | 信道不忙但 ACK 收不到 | GO/GC 距离远 / 天线隔离差 |
| Rx error 高 + 同频 | RSSI 正常但 CRC 错误多 | SCC 共信道干扰（P2P+STA 同信道） |
| 间歇性卡顿 | PER 0→突刺→0 | MCC 双信道切换 / 周期性干扰 |

### SCC / MCC 判断

- **SCC（Single Channel Concurrency）**：P2P 和 STA 使用同一信道 → 共享空口时间，互相抢占
- **MCC（Multi Channel Concurrency）**：P2P 和 STA 使用不同信道 → 需要分时切换，引入延迟
- 判断方法：对比 P2P interface 和 STA interface 的 channel/freq

### 排查建议

1. **确认 GO/GC 信道**：是否与 STA 共信道（SCC）
2. **确认 RSSI**：GO↔GC 之间信号强度
3. **确认带宽**：80MHz 在弱信号下 PER 会显著高于 40MHz
4. **检查天线**：横屏投屏时手握遮挡天线是常见原因
5. **tcpdump + iwpriv 交叉验证**：MAC 层抓包 + 驱动统计联合分析

---

## 11. 典型案例参考

### CASE-006：弱信号+单AP漫游失败
- 特征：Tx rate 65/10, ACK fail 暴涨, PER 93~100%
- 根因：弱信号下上行失效 + 单AP无漫游目标

### CASE-008：强信号下空口拥塞
- 特征：RSSI -30dBm 优秀, 但 Rx error 38.5%, ACK fail 51523
- 根因：信道干扰 / MCS过高 / 天线问题
