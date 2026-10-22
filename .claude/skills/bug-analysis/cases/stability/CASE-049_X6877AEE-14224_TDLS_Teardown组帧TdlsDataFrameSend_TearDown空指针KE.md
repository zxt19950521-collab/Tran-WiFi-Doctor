# CASE-049: TDLS Teardown 组帧 TdlsDataFrameSend_TearDown 对空指针解引用导致 Kernel KE

## 基本信息
- **案例ID**: CASE-049
- **分类**: stability
- **来源**: X6877AEE-14224
- **创建时间**: 2026-10-22
- **匹配次数**: 0

## 现象描述
- FANS 自动上报 KernelReboot `0xffffff04_KE`（Blocker）
- 机型 X6891 / X6877，版本 `16.3.0.160SP01(OP002PF001AZ)FANS`，SoC MT6899，驱动 `wlan_drv_gen4m_6899`（build-id `f37ec198fc94860d0339fc8ec57eb795fd7fdabf`）
- CurProcess：`TdlsDataFrameSend_TearDown`
- `Unable to handle kernel NULL pointer dereference at virtual address 0000000000000038`
- 本聚类 4 张单 / 5 次 dump / 3 台粉丝设备

## 根因结论

**WLAN 驱动缺陷：`TdlsexLinkMgt()` 处理 TDLS teardown（`ucActionCode=3`）时，`cnmGetTdlsPeerByAddress()` 返回 NULL，未判空即进入 `TdlsDataFrameSend_TearDown()`，读 NULL+0x38 导致 KE。**

机理链条：
1. 对端或本端发起 TDLS teardown（ActionCode=3）；X6877AEE-14224 发生在 AIS `ONLINE_SCAN` 期间
2. `wlanSetInformation` → `TdlsexLinkMgt` 按 peer MAC 查找 STA_REC
3. 查找失败（peer 已释放 / 未建链）仍调用 `TdlsDataFrameSend_TearDown`
4. `+0x34` 处读 `NULL+0x38` → KE

## 调用栈

```
TdlsDataFrameSend_TearDown+0x34/0x2e0 [wlan_drv_gen4m_6899]
TdlsexLinkMgt+0x270/0x350 [wlan_drv_gen4m_6899]
wlanSetInformation+0x90/0x128 [wlan_drv_gen4m_6899]
main_thread+0x244/0x1e60 [wlan_drv_gen4m_6899]
```

## 排查步骤

1. KE 现场：`pc : TdlsDataFrameSend_TearDown+0x34`，fault addr `0x38`
2. 前一行搜 `TdlsexLinkMgt` 的 `ucActionCode=3` / `ucBssIdx`
3. 确认是否同时有 `ONLINE_SCAN`、对端 Action 10/14、CMD buffer `MEM WARN`
4. 同设备是否还撞过 `qmDetermineStaRecIndex` / `TdlsexLinkOper`（CASE-048 / CASE-050）

## 关键日志

```
TdlsexLinkMgt:(TDLS INFO) u4SetBufferLen=620
TdlsexLinkMgt:(TDLS INFO) ucBssIdx=0, ucActionCode=3, ucDialogToken=0
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000038
pc : TdlsDataFrameSend_TearDown+0x34/0x2e0 [wlan_drv_gen4m_6899]
Call trace:
  TdlsDataFrameSend_TearDown+0x34
  TdlsexLinkMgt+0x270
  wlanSetInformation+0x90
  main_thread+0x244
```

## TAG
- Kernel Exception
- KernelReboot
- 驱动空指针
- TdlsDataFrameSend_TearDown
- TdlsexLinkMgt
- TDLS
- TDLS Teardown
- STA_REC
- NULL+0x38
- ONLINE_SCAN
- FANS
- MT6899
- gen4m
- MTK driver
- X6891
- X6877

## 建议措施

### WLAN 驱动（必须）
1. `TdlsexLinkMgt()` teardown 分支对 `cnmGetTdlsPeerByAddress` 判空，失败则 `return TDLS_STATUS_FAIL`，不得组帧
2. Gerrit [1623153](https://gerrit.transsion.com/c/MTK_CODE/neptune/wlan_driver/gen4m/+/1623153) 已加此判空，挂单即 X6877AEE-14224，预计能挡住本类 KE

### 验证
3. 回归：对端 teardown、本端拆直连、扫描期间 teardown，确认不再 KE；允许 teardown 失败返回

## 同类工单
- X6891：10878, 10972, 10991
- X6877：14224

## 关联案例
- **CASE-048**：同一生命周期的 TX 入队 `qmDetermineStaRecIndex` 空指针
- **CASE-050**：同一生命周期的 DISABLE_LINK `TdlsexLinkOper` 空指针
- **CASE-043**：oper=4 空指针（Beacon Timeout 断连清理）
