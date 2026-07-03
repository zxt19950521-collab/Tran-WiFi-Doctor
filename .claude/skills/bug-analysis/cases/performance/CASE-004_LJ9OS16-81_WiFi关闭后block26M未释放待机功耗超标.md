# CASE-004: LJ9 复杂待机功耗超标 — Conn 被蓝牙阻塞（非 WiFi 根因）

> **根因以功耗专题为准**：`cases/power-consumption/PWR-001_LJ9OS16-81_复杂待机GMS蓝牙扫描阻塞conn.md`

## 基本信息
- **案例ID**: CASE-004
- **功耗专题**: PWR-001
- **分类**: performance / power-consumption
- **来源**: LJ9OS16-81
- **创建时间**: 2026-06-29
- **修订时间**: 2026-06-29
- **匹配次数**: 0

## 现象描述
- LJ9 STR4 PIR 复杂待机，单卡 SIM#1 静态，灭屏静置约 9.03h
- 测试条件：WiFi **关闭**、移动数据开启、BT/GPS/NFC 开启
- 实测平均电流 **63.80 mA**，预期 **≤30 mA**，超出 **33.8 mA**（Blocker）
- 功耗组初判：WiFi block26M → 经 Connsys/BT 日志复核，**根因在蓝牙**

## 根因结论（修订）

**GMS 发起的蓝牙频繁 Inquiry 扫描与 BLE 广播，导致 Conninfra BT 链路长时间活跃，系统 LPM 被 conn 阻塞，无法深度休眠。**

`REASON_LMAC_NOT_RDY` **不作为根因**（芯片厂商确认：表示 WiFi LMAC 非 ready/非活跃，与 WiFi 关闭一致，不等同 WiFi 业务活跃）。

```
GMS → BT BR_INQUIRY_SCAN + BLE_ADV
  → bt:10676s (vs wf:217s) @ consys_power_state
  → SPM: LPM is blocked by conn
  → 26M_off_pct = 0
  → 待机 +33.8mA
```

## 关键日志

```text
[consys_power_state] bt:10676.473,102584; wf:217.848,43
[SPM] suspend warning: System LPM is blocked by conn
[btmtk_info] BR_INQURY_SCAN : 0x00120800; BLE_ADV : 0x00020190
```

## TAG
- 待机功耗
- 复杂待机
- LPM blocked by conn
- BR_INQUIRY_SCAN
- BLE_ADV
- GMS
- block26M
- LJ9

## 修复建议
- **转 GMS/业务模块**：优化灭屏待机 BT 扫描/广播策略
- BT/Conninfra：评估 conn 阻塞优化
- WiFi 组非主责

## 相关
- PWR-001：`cases/power-consumption/PWR-001_LJ9OS16-81_复杂待机GMS蓝牙扫描阻塞conn.md`
- 功耗专题索引：`cases/power-consumption/SUMMARY.md`
