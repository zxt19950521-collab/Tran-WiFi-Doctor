# CASE-033: 同网 fast.com 双机并发测速低于对比机（CN6 WiFi 链路正常）

## 基本信息
- **案例ID**: CASE-033
- **分类**: performance
- **来源**: CN6OS16-2381
- **创建时间**: 2026-07-07
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝反馈：同网 WiFi 下 CN6 网速明显低于 Poco X6，认为 CN6 WiFi 应优化到 ISP 带宽水平。
- 机型 TECNO CN6（XYZ），Android 16 / HiOS 16.3.0，`CN6-16.3.0.132SP01(OP002PF001AZ)FANS`，MTK 平台。
- 对比机：Poco X6（Jira 评论）。
- 测速网站：**fast.com**（两机同时打开）。
- 截图锚点 **19:37:52**：`Screenshot_20260702-193752.jpg` — CN6 **180 Mbps** vs Poco **230 Mbps**（差距约 **22%**）。
- 关键：CN6 WiFi **持续 validated**、Ping 全成功、PHY 数 Gbps 级，不是断连/弱信号/高时延故障。

## 根因结论

**CN6 WiFi 链路正常，不构成 WiFi 功能缺陷；180 vs 230 Mbps 差距主要来自双机并发测速争用与终端/平台吞吐差异，非 CN6 驱动或 RF 异常。**

机理链条：
1. CN6 连接 **`PORLAS FAMILY 5G`**（5GHz AX，BSSID `58:ae:**:**:**:b0`），测速时 RSSI **-55~-62 dBm**、link speed **2925~3510 / 3250~4333 Mbps**、**TxFail=0**。
2. `19:37:03~19:42` 系统 `WifiNetworkCheck` Ping **18 次全 success**（4~29ms）；`WifiNetworkQuality` 显示 `rssi sufficient`、测速中 tput **20~34 Mbps**。
3. kernel 在大流量测速时段 PER **9~70%**、Congestion diff 增大，属测速负载下的正常现象，**无 PER 100% 持续、无速率坍塌至 65 Mbps**。
4. 截图显示两机 **同时** 运行 fast.com，共享同一 AP 的 WAN 与空口；Poco 多 50 Mbps 是 AP 调度 + 终端能力差异的常见结果。
5. fast.com 为 **端到端 WAN 测速**（ISP + AP NAT + Netflix CDN），同一网址 **不保证两机连同一 CDN 边缘节点**；但同公网 IP 通常落在同一区域 CDN 池，节点差异不是本单主因。
6. `19:30:00` 曾有 2s `hasConnectivity=false`（`transsion.settings.wifi` 包更新触发），`19:30:02` 已 validated，与 19:37 测速无关。

与 CASE-020/032 区别：本单无「已连接但刷不了内容」、无 Ping 1000ms 超时、无 DNS 失败、无 2.4G 弱链路 PER 突刺。
与 CASE-011 区别：本单 RSSI 正常、CN6 实测 180Mbps 不低；CASE-011 为 5G 隔墙 RSSI 明显弱于对比机，需 RF/OTA 专项。

## 排查步骤

### 第一步：确认是否为 WiFi 链路故障
1. kernel `.localtime` 查 `mtk_cfg80211_get_station`：RSSI、link speed、**TxFail 是否为 0**。
2. 搜 `wlanLinkQualityMonitor`：PER 是否仅在测速大流量时升高，还是持续 100%。
3. main_log 搜 `WifiNetworkCheck` **Ping** → 是否全 `success=true`、时延正常。
4. 搜 `Wifi network validated` / `DISCONNECTED` → 测速时段是否持续在线。

### 第二步：对齐测速场景
1. 向用户确认是否 **双机同时** 测速；要求补 **单台顺序测 3 次** 截图。
2. 确认两机是否均连 **5G SSID**（本单 CN6 为 `PORLAS FAMILY 5G`）。
3. 说明 fast.com 测的是 WAN 端到端，非纯 WiFi PHY；同一网址不一定同一 CDN 节点。

### 第三步：鉴别「真 WiFi 慢」vs「对比机争用/期望值」
| 若 CN6 WiFi 真有问题 | 本单实际 |
|---------------------|----------|
| Ping fail 或 >100ms 持续 | Ping 18/18 success，4~29ms |
| TxFail>0 / 频繁断连 | TxFail=0，validated 持续 |
| PHY 坍塌至 65 Mbps、PER 100% | PHY 2925~4333 Mbps，PER 仅测速时波动 |
| 单台测速仍显著低于对比机 | 日志仅双机并发场景，CN6 单台 180Mbps 正常 |

### 第四步：深入取证（可选）
1. 单台顺序 fast.com / speedtest.net，记录服务器名与 3 次均值。
2. 差距 **>30% 且可复现** 时参考 CASE-011 做 RF/OTA 对比。
3. 补 tcpdump 可反查 fast.com 实际 CDN IP（本单未提供）。

## 关键日志

```
// 截图时刻（main_log 24）
07-02 19:37:52 SaveImageInBackgroundTask fileName: Screenshot_20260702-193752.jpg
07-02 19:37:52 WifiNetworkQuality: 2.30/3.07 Mbps   // 测速刚结束

// 测速中：链路质量优秀（kernel .localtime +8h）
07-02 19:37:02 mtk_cfg80211_get_station: link speed=2925/3900, MovAvg_rssi=-61, TxFail=0
07-02 19:37:05 wlanLinkQualityMonitor: Tx(rate:2925,...), Rx(rate:3900,...), PER(26)
07-02 19:37:11 mtk_cfg80211_get_station: link speed=2925/4333, MovAvg_rssi=-58, TxFail=0
07-02 19:37:25 wlanLinkQualityMonitor: PER(25), Congestion diff:1118230

// 框架层：Ping 全成功（main_log 24）
07-02 19:37:03 Ping result: {success=true, time=29ms}
07-02 19:37:13 Ping result: {success=true, time=4ms}
...（19:37~19:42 共 18 次 success，0 次 fail）

// 连接信息
07-02 19:30:04 TranWifiSmartAssistantController: SSID :"PORLAS FAMILY 5G", rssi :-66
07-02 19:37:03 WifiNetworkQuality: 20.06/34.38 Mbps, current rssi is sufficient
```

## TAG
- fast.com
- 双机并发测速
- 对比机测速差异
- WiFi链路正常
- 5GHz AX
- 强信号
- TxFail零
- Ping全成功
- PER测速波动
- 非WiFi问题
- 期望值管理
- WAN端到端测速
- CDN节点
- 粉丝反馈
- 菲律宾
- CN6
- Poco X6
- MTK平台

## 建议措施
1. **回复粉丝**：CN6 同网 5G WiFi 实测 **180 Mbps**，WiFi 连接正常；与 Poco 230 Mbps 差距约 22%，建议 **不要双机同时测速**，单台顺序测 3 次取均值。
2. **测试侧**：同位置、同 SSID，分别记录 RSSI、link speed、Ping、fast.com；确认频段一致。
3. **若单台差距 >30% 可复现**：参考 CASE-011 走 RF/OTA 对比，查 CN6 接收灵敏度是否弱于 Poco X6。
4. **不建议**：按 WiFi 驱动 bug 或 ISP 优化需求直接关闭；当前日志不支持「CN6 WiFi 异常」。

## 数据局限
- 仅有 CN6 日志，无 Poco X6 RSSI/PHY 对比。
- 无 tcpdump，无法确认 fast.com 实际 CDN 节点 IP。
- 双机并发测速，无法分离「纯 CN6 单台上限」与「争用损失」。

## 相关案例
- **CASE-025**（CN6OS16-2171）：系统 WiFi 探测正常、用户感知与客观链路不一致 — 回复口径可参考。
- **CASE-011**（CN6OS16-509）：5G RSSI 弱于对比机 — 若需硬件评估走 RF/OTA；本单 RSSI 正常、不匹配弱 RF。
- **CASE-020 / CASE-032**：弱链路 PER 突刺、刷不了内容 — **排除**。

## 分析报告
- `AI-result/issues/CN6OS16-2381/CN6OS16-2381-analysis.md`
- 链路质量图：`AI-result/issues/CN6OS16-2381/CN6OS16-2381_link_quality.png`
