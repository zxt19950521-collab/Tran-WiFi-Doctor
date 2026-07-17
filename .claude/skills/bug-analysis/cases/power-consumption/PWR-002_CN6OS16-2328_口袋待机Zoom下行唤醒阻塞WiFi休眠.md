# PWR-002: CN6 口袋待机温升 — Zoom 下行包唤醒阻塞 WiFi 休眠

## 基本信息
- **功耗案例ID**: PWR-002
- **关联案例**: CASE-036（同单，连接/性能索引保留；根因以本文为准）
- **Jira**: CN6OS16-2328
- **设备**: CN6（MTK），环温 25℃，BOM：V
- **创建时间**: 2026-07-17
- **最后修订**: 2026-07-17

## 现象描述
- PIR **口袋待机**温升超竞品：最高温 **34.1℃**，温升 **8.6℃**
- vs Redmi note 14 5G：温升 5.3℃（超 **3.3℃**）；vs LK7K：温升 6℃（超 **2.6℃**）
- 功耗 **433.1 mA**；上一阶段 113 版本 **385.06 mA**（+48 mA，温升差约 2.3℃）
- 功耗组：26M 休眠率一直为 0；AP 休眠期间 Connsys `*wf:0,0*`（WiFi 未休眠）→ 转 WiFi
- WiFi 组：持续收发，接收侧主导来自 **`170.114.52.5`**

## 根因结论

**口袋待机灭屏期间，Zoom 服务器（`170.114.52.5` / `170.114.52.83`，归属 Zoom Video Communications）下行 IP 包反复触发 `nic_rxd_v2_check_wakeup_reason` 唤醒 WiFi；同时约 40% 采样窗口仍有非零吞吐（非零均值 ~1.9 Mbps）。WiFi 有下行业务时保持 awake 为预期行为，导致 Connsys wf 无法稳定休眠、系统 26M/深度休眠失败，抬高待机电流与板温。责任在 Zoom/应用后台保活，非 WiFi driver bug。本份日志 SoftAP 未开启。**

### 因果链

```
口袋待机（STA 连 AP，灭屏）
    ↓
Zoom 后台长连接：下行 170.114.52.5 / .83
    ↓
nic_rxd_v2_check_wakeup_reason 反复唤醒 + 间歇 Tput>0 (~40%)
    ↓
WiFi 无法稳定 LPS / 深度休眠（SETSUSPENDMODE 有进有出，被打断）
    ↓
功耗组：wf:0,0 / 26M_off=0
    ↓
电流 433 mA、温升 8.6℃（超竞品）
```

### 已排除 / 降级项

| 项目 | 结论 |
|------|------|
| **SoftAP 常开** | 本份口袋待机 main_log SoftAP 指示器 = **0**；非本单根因 |
| **Facebook 链路流量** | main 大量 facebook 命中为 AIM 应用推荐/MRU，非 wakeup IP |
| **WiFi FW/Driver 独责** | 有下行业务保持 awake 符合设计；无「无流量仍不睡」证据 |
| **仅 Zoom 通话场景误判** | 通话场景 Tput>0≈95% 为对照；**口袋待机 kernel 已直接命中 Zoom IP 唤醒** |

## 关键日志

### Zoom IP 唤醒（口袋待机 kernel，UTC 时间；+8h 对齐 main）
```text
07-03 09:31:45.996 nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.5,
07-03 09:31:48.494 nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.83,
07-03 09:31:52.913 nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.5,
```
WHOIS：`170.114.0.0/16` → Zoom Video Communications, Inc。

### 吞吐与 suspend（口袋待机）
```text
kalPerMonUpdate: 1151 samples; Tput>0: 457 (39.7%); avg 1.876 Mbps (non-zero)
SETSUSPENDMODE 0 (resume): 8
SETSUSPENDMODE 1 (suspend): 7
SoftAP: 0
```

### 功耗组转单依据（评论）
```text
26M 休眠率一直为 0
AP 休眠期间 *wf:0,0*  → WiFi 未休眠
```

## 排查步骤

1. 确认场景为口袋待机/灭屏，记录电流与温升相对竞品差值
2. 搜 `26M_off_pct` / `wf:0,0` / `LPM is blocked by conn`，确认阻塞在 WiFi
3. kernel 搜 `nic_rxd_v2_check_wakeup_reason` / `IP Packet from:`，统计 Top 唤醒 IP
4. WHOIS / 业务归属唤醒 IP（本单为 Zoom）
5. main_log 确认 SoftAP（`AP-ENABLED`）是否开启；本单为否
6. 对照测：强制停用 Zoom / 限制后台联网后电流是否回落
7. 有 tcpdump 时再做 UID↔IP 映射（本单 CN6 无 tcpdump）

## 建议措施

| 责任方 | 动作 |
|--------|------|
| **应用 / Zoom 策略** | 灭屏限制 `us.zoom.videomeetings` 后台长连接；评估 Doze/待机冻结 |
| **测试** | 对照「无 Zoom 后台」口袋待机电流；可选补 CN6 tcpdump |
| **软件** | 对比 113 vs 133 Zoom/联网保活、白名单差分（+48 mA） |
| **WiFi 组** | 非主责；可协助 wakeup IP TopN，不作为合入条件 |

## 量化对照

| 场景 | Tput>0 | 非零 avg | SETSUSPENDMODE 0/1 | SoftAP | 170.114 唤醒 |
|------|--------|----------|--------------------|--------|--------------|
| **口袋待机** | 39.7% | 1.876 Mbps | 8 / 7 | 0 | 15（.52.5/.83） |
| Zoom 通话 | 95.3% | 2.257 Mbps | 1 / 0 | 0 | （评论侧） |

## TAG
- 待机功耗
- 口袋待机
- block26M
- 26M_off_pct=0
- WiFi 阻塞休眠
- SETSUSPENDMODE
- nic_rxd_v2_check_wakeup_reason
- Zoom
- us.zoom.videomeetings
- 170.114.52.5
- 应用后台保活
- 版本回归
- CN6
- MTK平台
- 续航温升

## 参考
- 日志：`\\10.150.98.90\03_测试Log\温升测试log\zenghao\CN6 PIR\CN6\口袋待机`
- 分析报告：`AI-result/issues/CN6OS16-2328/CN6OS16-2328-analysis.md`
- 曲线图：`CN6OS16-2328_pocket_link_quality.png`
- 相关：PWR-001（BT 阻塞 conn，机制同类、侧别不同）
