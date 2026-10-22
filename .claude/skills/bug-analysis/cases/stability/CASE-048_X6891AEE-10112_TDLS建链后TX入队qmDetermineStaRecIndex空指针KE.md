# CASE-048: TDLS 建链后 TX 入队 qmDetermineStaRecIndex 对空 STA_REC 解引用导致 Kernel KE

## 基本信息
- **案例ID**: CASE-048
- **分类**: stability
- **来源**: X6891AEE-10112
- **创建时间**: 2026-10-22
- **匹配次数**: 0

## 现象描述
- FANS 自动上报 KernelReboot `0xffffff04_KE`（Blocker）
- 机型 X6891 / X6877，版本 `16.3.0.160SP01(OP002PF001AZ)FANS`，SoC MT6899，驱动 `wlan_drv_gen4m_6899`（build-id `f37ec198fc94860d0339fc8ec57eb795fd7fdabf`）
- CurProcess：`qmDetermineStaRecIndex`
- `Unable to handle kernel NULL pointer dereference at virtual address 0000000000000034`
- 本聚类 10 张单 / 16 次 dump / 3 台粉丝设备（X6891 两台 14 次，X6877 一台 2 次）

## 根因结论

**WLAN 驱动缺陷：`qmDetermineStaRecIndex()` 在 TX 入队时调用 `cnmGetTdlsPeerByAddress()` 得到 NULL，未判空即执行 `IS_DLS_STA(prTempStaRec)`（读 STA_REC +0x34）导致 KE。**

机理链条：
1. TDLS `ENABLE_LINK`（oper=3）或 `mtk_cfg80211_add_key` / `qmActivateStaRec`（见过 STA[3]/[10]/[22]）
2. host TX 立即入队：`kalProcessTxReq` → `wlanEnqueueTxPacket` → `nicTxEnqueueMsdu` → `qmEnqueueTxPackets` → `qmDetermineStaRecIndex`
3. `cnmGetTdlsPeerByAddress` 返回 NULL（STA_REC 未就绪、已释放，或组播 `DA=BMCAST` 无 peer）
4. `IS_DLS_STA(NULL)` → `LDRB [x0,#0x34]` → KE
5. 补充窗口：s2idle 挂起（X6891AEE-10971）

## 调用栈

```
qmDetermineStaRecIndex+0xe8/0x250 [wlan_drv_gen4m_6899]
qmEnqueueTxPackets+0xd8/0x4d4 [wlan_drv_gen4m_6899]
nicTxEnqueueMsdu+0x260/0x544 [wlan_drv_gen4m_6899]
wlanEnqueueTxPacket+0x198/0x22c [wlan_drv_gen4m_6899]
kalProcessTxReq+0x144/0x3f0 [wlan_drv_gen4m_6899]
main_thread+0x3d4/0x1e60 [wlan_drv_gen4m_6899]
```

部分 dump 偏移差 4 字节（如 `nicTxEnqueueMsdu+0x25c`），符号与调用关系相同。

## 排查步骤

1. KE 现场：`pc : qmDetermineStaRecIndex+0xe8`，fault addr `0x34`，x0=0
2. 崩溃前搜 `qmActivateStaRec` / `mtk_cfg80211_add_key` / `mtk_cfg80211_tdls_oper` oper=3
3. 确认 TX 目的地址：单播 TDLS peer 或 `TX with DA = BMCAST`
4. 同 build-id 检索 FANS KernelReboot 是否还有 TearDown / TdlsexLinkOper 同类 KE（CASE-049 / CASE-050）

## 关键日志

```
[wlan] qmActivateStaRec:(QM INFO) QM: +STA[10]
[wlan] qmSetStaRecTxAllowed:(QM INFO) Set Sta[10] TxAllowed from [0] to [1]
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000034
pc : qmDetermineStaRecIndex+0xe8/0x250 [wlan_drv_gen4m_6899]
Call trace:
  qmDetermineStaRecIndex+0xe8
  qmEnqueueTxPackets+0xd8
  nicTxEnqueueMsdu+0x260
  wlanEnqueueTxPacket+0x198
  kalProcessTxReq+0x144
  main_thread+0x3d4
```

## TAG
- Kernel Exception
- KernelReboot
- 驱动空指针
- qmDetermineStaRecIndex
- qmEnqueueTxPackets
- TDLS
- TDLS_ENABLE_LINK
- STA_REC
- IS_DLS_STA
- NULL+0x34
- FANS
- MT6899
- gen4m
- MTK driver
- X6891
- X6877

## 建议措施

### WLAN 驱动（必须）
1. `qmDetermineStaRecIndex()` 对 `cnmGetTdlsPeerByAddress` 返回值判空后再 `IS_DLS_STA`
2. 同步给 `TdlsexLinkMgt` / `TdlsexLinkOper` 同类路径加判空（见 CASE-049 / CASE-050）
3. Gerrit [1623153](https://gerrit.transsion.com/c/MTK_CODE/neptune/wlan_driver/gen4m/+/1623153)（`tOS16.3.0_mtk_A15_vnd_release`）已在 `nic/que_mgt.c` 改为 `if (prTempStaRec && IS_DLS_STA(prTempStaRec) && ...)`，预计直接挡住本类 KE

### 验证
4. 合入后用原粉丝机回归 TDLS 建链后立刻 TX（含组播），确认 `qmDetermineStaRecIndex` 签名清零；流量允许走 AP 绕路，但不得 panic

## 同类工单
- X6891：10112, 10882, 10941, 10964, 10965, 10971, 10992, 10993
- X6877：14243, 14267

## 关联案例
- **CASE-049**：同一生命周期的 Teardown 组帧空指针
- **CASE-050**：同一生命周期的 DISABLE_LINK `TdlsexLinkOper` 空指针
- **CASE-043**：oper=4 另一触发（仅 Discovery + Beacon Timeout 断连）
