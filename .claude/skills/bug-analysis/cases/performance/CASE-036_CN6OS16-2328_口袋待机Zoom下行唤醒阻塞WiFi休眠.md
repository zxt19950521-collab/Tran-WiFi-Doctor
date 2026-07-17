# CASE-036: CN6 口袋待机温升 — Zoom 下行唤醒阻塞 WiFi 休眠

> **根因以功耗专题为准**：`cases/power-consumption/PWR-002_CN6OS16-2328_口袋待机Zoom下行唤醒阻塞WiFi休眠.md`

## 基本信息
- **案例ID**: CASE-036
- **功耗专题**: PWR-002
- **分类**: performance / power-consumption
- **来源**: CN6OS16-2328
- **创建时间**: 2026-07-17
- **匹配次数**: 0

## 现象描述
- CN6 口袋待机最高温 34.1℃ / 温升 8.6℃，超竞品；功耗 433.1 mA（相对 113 版本 +48 mA）
- 功耗组：26M 休眠率=0，`wf:0,0` → 转 WiFi
- WiFi：持续数据，对端 `170.114.52.5`（Zoom）

## 根因结论

**口袋待机期间 Zoom 服务器（170.114.52.5 / .83）下行包反复唤醒 WiFi，间歇吞吐约 40% 非零，无法稳定休眠；应用后台保活问题，非 WiFi driver bug。SoftAP 本 log 未开启。**

```
Zoom 下行 170.114.52.x
  → nic_rxd_v2_check_wakeup_reason 唤醒
  → wf 无法稳定休眠 / 26M_off=0
  → 温升与电流超标
```

## 关键日志

```text
nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.5,
nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.83,
Tput>0: 457/1151 (39.7%); SETSUSPENDMODE 0/1 = 8/7; SoftAP=0
```

## TAG
- 待机功耗
- 口袋待机
- block26M
- Zoom
- 170.114.52.5
- WiFi 阻塞休眠
- CN6
- MTK平台

## 参考
- PWR-002（完整因果链与排查步骤）
- 报告：`AI-result/issues/CN6OS16-2328/CN6OS16-2328-analysis.md`
