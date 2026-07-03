# PWR-001: LJ9 复杂待机功耗超标 — GMS 蓝牙扫描/广播阻塞 Conn

## 基本信息
- **功耗案例ID**: PWR-001
- **关联案例**: CASE-031（同单，连接类索引保留；根因以本文为准）
- **Jira**: LJ9OS16-81
- **设备**: LJ9 / ASALE3741B000022
- **创建时间**: 2026-06-29
- **最后修订**: 2026-06-29（根因更正：排除 LMAC_NOT_RDY）

## 现象描述
- LJ9 STR4 PIR **复杂待机**，单卡 SIM#1 静态，灭屏约 9.03h
- 条件：WiFi **关闭**、移动数据开、BT/GPS/NFC 开
- 电流 **63.80 mA**（预期 ≤30 mA，**+33.8 mA**，Blocker）
- 功耗组初判「WiFi block26M」→ 转 WiFi 组；经 Connsys/BT 日志复核后 **根因在蓝牙侧**

## 根因结论（修订版）

**灭屏待机期间，GMS 发起的蓝牙频繁 Inquiry 扫描与 BLE 广播，导致 Conninfra BT 链路长时间活跃，系统 LPM 被 conn 阻塞，无法深度休眠，贡献额外待机电流。WiFi 侧 LMAC NOT_RDY 为关闭/非活跃态的正常统计表现，非本单根因。**

### 因果链

```
复杂待机（WiFi 关、BT 开）
    ↓
GMS 触发 BT 频繁 BR_INQUIRY_SCAN + BLE_ADV
    ↓
Connsys BT 累计活跃远超 WiFi（bt:10676s vs wf:217s）
    ↓
SPM: System LPM is blocked by conn
    ↓
26M_off_pct = 0 / 无法深度休眠
    ↓
待机电流 63.8mA（+33.8mA）
```

### 已排除 / 降级项

| 项目 | 结论 |
|------|------|
| **REASON_LMAC_NOT_RDY** | 芯片厂商确认：表示 LMAC **非 ready/非活跃**，与 WiFi 关闭一致，**不代表 WiFi 业务活跃**，不作为根因 |
| WiFi FW 独责 | Connsys 统计 WiFi 活跃时间远低于 BT，WiFi 非主因 |
| wlan0 teardown 不完整 | 可能存在次要因素，但不足以解释 bt 侧 102584 量级活跃 |

## 关键日志

### Connsys 功耗分布（06-23 13:18:29）
```text
conninfra@(_status_dump:273) Connsys status: BTWIFI
[consys_power_state][round:3447]conninfra:0.000,0;wf:0.000,0;bt:0.189,0;gps:0.190,0;
[total]conninfra:189.332,185;wf:217.848,43;bt:10676.473,102584;gps:22330.630,1;
```

解读：**BT 总活跃 10676s / 计数 102584，WiFi 仅 217s / 43** → BT 占 conn 阻塞绝对主导。

### SPM conn 阻塞
```text
06-23 13:18:30.196 [SPM] suspend warning:(OneShot) System LPM is blocked by conn
```

### BT 扫描/广播（06-24 00:30:01，待机期仍活跃）
```text
[btmtk_info] [bt host info] [0][BR_INQURY_SCAN : 0x00120800]
[btmtk_info] [bt host info] [1][BR_SCAN_MODE : 0x00000002]
[btmtk_info] [bt host info] [2][BLE_SCAN : 0x00000000]
[btmtk_info] [bt host info] [3][BLE_ADV : 0x00020190]
[SPM] suspend warning:(OneShot) System LPM is blocked by conn
```

### 系统层佐证（次要）
```text
26M_off_pct = 0
R12_CONN2AP_SPM_WAKEUP_B
```

## 排查步骤

1. 确认复杂待机场景与电流超标幅度
2. 搜 `consys_power_state`，对比 **bt vs wf** 的 total 时间与计数
3. 搜 `LPM is blocked by conn` 与 `Connsys status`
4. 搜 `btmtk_info` / `BR_INQURY_SCAN` / `BLE_ADV` 在灭屏后是否持续
5. **不要**将 `REASON_LMAC_NOT_RDY` 高占比直接定为 WiFi 根因
6. 追溯 BT 扫描发起方（本单：**GMS**）→ 转业务模块

## 建议措施

| 责任方 | 动作 |
|--------|------|
| **GMS / 业务模块** | 分析灭屏待机为何持续 BR Inquiry + BLE ADV；优化扫描/广播策略或灭屏降频 |
| **BT / Conninfra** | 评估 BT 扫描 duty cycle 上限；与 WiFi 共存的 conn 阻塞优化 |
| **WiFi 组** | 非主责；可保留 wlan0 teardown 等次要优化，不作为本单闭环条件 |
| **测试** | 对比 BT 关闭场景电流；抓 GMS 包名/唤醒链 |

## TAG
- 待机功耗
- 复杂待机
- block26M
- 26M_off_pct=0
- LPM blocked by conn
- Connsys BTWIFI
- BR_INQUIRY_SCAN
- BLE_ADV
- GMS
- 蓝牙扫描
- LJ9
- MTK平台

## 参考
- 日志：`\\10.207.190.10\sw_log\快温省\性能功耗\jiaxue.tang\LJ9\复杂待机\单卡待机-SIM#1静态\ASALE3741B000022`
- 分析报告：`D:\AI\AI-result\issues\LJ9OS16-81\LJ9OS16-81-analysis.md`（待同步修订）
