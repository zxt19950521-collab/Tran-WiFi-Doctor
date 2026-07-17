# 功耗专题总结（持续更新）

本目录收录 **待机/灭屏功耗** 类问题的分析结论与排查经验，与连接类案例（P2P/DHCP 等）分开维护，便于后续持续补充。

---

## 使用说明

- 每条记录命名：`PWR-{序号}_{Jira单号}_{简短标题}.md`
- 本文件 `SUMMARY.md` 为 **索引 + 共性知识**，新增案例后同步更新下方表格
- 连接类性能问题仍可使用 `cases/performance/`，但 **待机功耗根因分析以本目录为准**

---

## 共性排查路径

```
1. 确认测试场景（WiFi 开/关、数据、BT、灭屏时长、电流基准）
2. 查 SPM：26M_off_pct、suspend wake up by、LPM is blocked by
3. 查 Connsys 功耗分布：conninfra_power_state 中 bt/wf/gps 占比
4. 查 BT：btmtk BR_INQUIRY_SCAN / BLE_ADV / BLE_SCAN
5. 查 WiFi（若相关）：SETSUSPENDMODE、wlan0 teardown、P2P listen、`nic_rxd_v2_check_wakeup_reason`
6. 追溯上层发起方（GMS / 系统服务 / 三方 App / 远端服务器 IP）
```

---

## WiFi 下行唤醒日志要点

```text
nic_rxd_v2_check_wakeup_reason:(RX DEBUG) IP Packet from:170.114.52.5,
```

| 要点 | 说明 |
|------|------|
| 出现时机 | 灭屏/suspend 前后仍反复打印 |
| 处理 | WHOIS 归属 IP → 对应 App/业务；对照停用该 App 测电流 |
| 与 driver | 有下行业务保持 awake **通常为预期**，优先查应用保活 |

配合：`SETSUSPENDMODE 0/1` 进出、`kalPerMonUpdate` Tput>0 占比。

---

## 已知误区（勿作为 WiFi 根因）

| 日志/指标 | 正确理解 | 错误解读 |
|-----------|----------|----------|
| **REASON_LMAC_NOT_RDY**（PWR INFO） | 统计窗口内 WiFi LMAC 多处于 **非 ready/非活跃** 态，与「WiFi 已关闭或仅扫描态」**一致** | ~~LMAC 异常活跃导致无法休眠~~ |
| **HW enter sleep count = 0**（WiFi 关闭场景） | WiFi 关闭时 HW 不进 sleep **可能是预期表现** | 需结合 Connsys 哪条链路在 block |
| **26M_off_pct = 0** | 系统层 26M 未关，需查 **谁 block 了 conn**（BT/WiFi/GPS） | 直接等同 WiFi driver bug |

> 以上 LMAC_NOT_RDY 结论已咨询芯片厂商确认。

---

## Connsys 功耗日志解读要点

典型格式：
```text
[consys_power_state] conninfra:0.000,0; wf:0.000,0; bt:0.189,0; gps:0.190,0;
[total] conninfra:189.332,185; wf:217.848,43; bt:10676.473,102584; gps:22330.630,1;
```

| 字段 | 含义 | 关注点 |
|------|------|--------|
| `bt:10676.473,102584` | BT 累计活跃时间远高于 WiFi | BT 为 conn 阻塞主因 |
| `wf:217.848,43` | WiFi 活跃时间相对很低 | 与「WiFi 已关闭」一致 |
| `Connsys status: BTWIFI` | 组合态运行 | 需看哪一侧在拉高占比 |

配合 SPM：
```text
[SPM] suspend warning: System LPM is blocked by conn
```

---

## BT 扫描/广播日志要点

```text
[bt host info] [0][BR_INQURY_SCAN : 0x00120800]
[bt host info] [1][BR_SCAN_MODE : 0x00000002]
[bt host info] [3][BLE_ADV : 0x00020190]
```

| 字段 | 含义 |
|------|------|
| BR_INQUIRY_SCAN | 经典蓝牙 Inquiry 扫描活跃 |
| BR_SCAN_MODE | BR 扫描模式开启 |
| BLE_ADV | BLE 广播活跃 |

若灭屏待机期间持续出现且间隔短 → **BT 频繁扫描/广播** → block conninfra → 系统无法深度休眠。

**上层追溯**：本专题已记录案例中，发起方可能为 **GMS**，需转对应业务模块（非 WiFi 组独力解决）。

---

## 案例索引

| ID | Jira | 标题 | 根因摘要 | 责任方向 | 状态 |
|----|------|------|----------|----------|------|
| PWR-001 | LJ9OS16-81 | LJ9 复杂待机电流超标 | GMS 发起 BT 频繁扫描/广播 → conn block → LPM 失败 | GMS / BT 业务 + Conninfra | 已分析 |
| PWR-002 | CN6OS16-2328 | CN6 口袋待机温升 | Zoom 下行 170.114.52.x 反复唤醒 WiFi → 无法稳定休眠 | Zoom / 应用保活 | 已分析 |

---

## 待补充（占位）

| Jira | 场景 | 备注 |
|------|------|------|
| CL6OS16-55 | WiFi 开未连 AP，P2P Action 帧 ~20s 唤醒 | 见 `cases/performance/` 分析报告，待迁入本目录 |

---

*最后更新：2026-07-17*
