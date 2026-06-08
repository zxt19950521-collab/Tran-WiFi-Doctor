# CASE-007: 5G AC 隔墙 30m OTA RSSI 弱于对比机，CTIA 开关影响显著

## 基本信息
- **案例ID**: CASE-007
- **分类**: performance
- **来源**: CN6OS16-509
- **创建时间**: 2026-06-08
- **匹配次数**: 0

## 现象描述
- CN6（DUT）vs NOTE 14 PRO 5G（对比机），5G AC ch36 隔墙 30m OTA 测试
- 测试环境：C7 车库，TP-LINK 7DR-3610，11AC mixed，16 组姿态
- A 标要求：测试机 RSSI ≥ 竞品机 -3 dBm
- PR2-4 复测 FAIL：CN6 kernel RSSI 均值 -58.3 dBm，对比机 -55.2 dBm，差距 ~3.1 dB
- 原始测试差距约 9 dB，射频整改后缩小到 5 dB → 4 dB，仍未达标
- OTA 测试开启 CTIA，软测日志 `mediatek.wlan.ctia=0`，测试条件不一致

## 根因结论
**主因**：CN6 在 5G AC ch36 弱信号 OTA 场景下，WiFi 接收灵敏度/天线效率弱于对比机 NOTE 14 PRO 5G，RSSI 平均低约 3—4 dB。

**干扰因素**：OTA 测试开启 CTIA、软测关闭 CTIA，MTK 确认 CTIA 对 OTA 数据影响极大（Case 143289661），导致 OTA 与软测 log 口径不一致。

**共性**：评论称部分 MTK 共性，LK6 与 CN6 差异仍在跟踪。

## 排查步骤
1. 确认测试条件：频段 ch36（5180MHz）、路由器型号、隔墙距离、姿态组数
2. 对比两台设备 kernel_log 中 RSSI 样本统计（均值/中位数/P10/P90）
3. 检查 main_log 中 `WifiClientModeImpl` / `Wlan` 的 RSSI、TxLinkSpeed、freq
4. 确认 CTIA 开关状态：`getprop mediatek.wlan.ctia`（OTA vs 软测是否一致）
5. 对比历史版本改善趋势（原始 → 整改 → 复测）
6. 必要时抓取 WiFi FW log、空口 log，分析天线分集/chain 选择
7. 参考 MTK Case 143289661 确认 CTIA 对 OTA 数据的影响幅度

## 关键日志
```
// CN6 连接 — RSSI -59, ch36
05-20 14:27:43.127745  SecurityPay Wlan: BSSID=f8:ce:21:9b:b0:9a, level=-59, freq=5180, cap=[ESS]

// NOTE 14 连接 — RSSI -54, 433Mbps, ch36
05-20 15:09:13.014729  WifiClientModeImpl: updateLinkLayerStatsRssiSpeedFrequencyCapabilities rssi=-54 TxLinkspeed=433 freq=5180 RxLinkSpeed=433

// CTIA 属性（软测均为关闭）
[mediatek.wlan.ctia]: [0]
[ro.tr_wifi_sar.feature.support]: [1]
```

## 统计参考
| 设备 | kernel RSSI 样本数 | 均值 | 中位数 |
|------|-------------------|------|--------|
| CN6 | 4615 | -58.34 dBm | -58 dBm |
| NOTE 14 PRO 5G | 4584 | -55.23 dBm | -55 dBm |
| 差距 | — | 3.11 dB | 3 dB |

## TAG
- RSSI
- OTA
- 5G AC
- CTIA
- 隔墙
- ch36
- 射频性能
- CN6
- MTK共性
- 弱信号
- 对比机测试

## 相关案例
- CASE-006（performance 类，蜂窝热点温升，不同子场景）
