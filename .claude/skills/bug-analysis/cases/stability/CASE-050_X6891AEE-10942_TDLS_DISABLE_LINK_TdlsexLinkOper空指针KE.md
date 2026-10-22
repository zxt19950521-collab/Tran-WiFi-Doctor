# CASE-050: TDLS DISABLE_LINK 时 TdlsexLinkOper 对空 STA_REC 解引用导致 Kernel KE

## 基本信息
- **案例ID**: CASE-050
- **分类**: stability
- **来源**: X6891AEE-10942
- **创建时间**: 2026-10-22
- **匹配次数**: 0

## 现象描述
- FANS 自动上报 KernelReboot `0xffffff04_KE`（Blocker）
- 机型 X6891 / X6877，版本 `16.3.0.160SP01(OP002PF001AZ)FANS`，SoC MT6899，驱动 `wlan_drv_gen4m_6899`（build-id `f37ec198fc94860d0339fc8ec57eb795fd7fdabf`）
- CurProcess：`TdlsexLinkOper`
- `Unable to handle kernel NULL pointer dereference at virtual address 0000000000000d38`
- 本聚类 4 张单 / 4 次 dump / 4 台粉丝设备
- X6877AEE-14177 前台为飞书 `com.ss.android.lark.transsion`

## 根因结论

**WLAN 驱动缺陷：`TdlsexLinkOper()` 处理 `TDLS_DISABLE_LINK`(oper=4) 时，按 peer MAC 查找 STA_REC 返回 NULL，未判空即读取 `+0xd38`（`ldrb w8,[x0,#0xd38]`）导致 KE。**

与 CASE-043 同一崩溃点。本案聚类来自 16.3.0.160SP01 粉丝稳定性，触发更常见于 TDLS 直连建立后又 disable（cfg80211 oper=4），不限于 CASE-043 的「仅 Discovery + Beacon Timeout」。

机理链条：
1. `mtk_cfg80211_tdls_oper` `oper=4`，`wlanSetInformation` 进入 `TdlsexLinkOper`
2. `cnmGetTdlsPeerByAddress` 找不到 peer（未建链、已 `cnmStaFreeAllStaByNetwork`、或 ENABLE_LINK 未写好 STA_REC）
3. 直接访问 `prStaRec->ucTdlsIndex` / `IS_DLS_STA(prStaRec)` → fault `0xd38` → KE

## 调用栈

```
TdlsexLinkOper+0xe0/0x1e0 [wlan_drv_gen4m_6899]
wlanSetInformation+0x90/0x128 [wlan_drv_gen4m_6899]
main_thread+0x244/0x1e60 [wlan_drv_gen4m_6899]
```

部分 dump 为 `wlanSetInformation+0x8c`、`main_thread+0x240`。

## 排查步骤

1. KE 现场：`pc : TdlsexLinkOper+0xe0`，fault addr `0xd38`，x0=0
2. 前一行确认 `TdlsexLinkOper:(TDLS INFO) prCmd->oper=4`
3. 往前搜是否有 ENABLE_LINK(oper=3)、Discovery-only、或 `cnmStaFreeAllStaByNetwork`
4. 同 build-id 是否还有 CASE-048 / CASE-049 签名

## 关键日志

```
mtk_cfg80211_tdls_oper:(REQ INFO) ucBssIndex = 0, oper=4
TdlsexLinkOper:(TDLS INFO) prCmd->oper=4, u4SetBufferLen=16
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000d38
pc : TdlsexLinkOper+0xe0/0x1e0 [wlan_drv_gen4m_6899]
Call trace:
  TdlsexLinkOper+0xe0
  wlanSetInformation+0x90
  main_thread+0x244
```

## TAG
- Kernel Exception
- KernelReboot
- 驱动空指针
- TdlsexLinkOper
- TDLS
- TDLS_DISABLE_LINK
- STA_REC
- NULL+0xd38
- FANS
- MT6899
- gen4m
- MTK driver
- X6891
- X6877

## 建议措施

### WLAN 驱动（必须）
1. `TdlsexLinkOper()` 各 oper 分支对 STA_REC 查找结果判空，未找到则失败返回，不得解引用
2. Gerrit [1623153](https://gerrit.transsion.com/c/MTK_CODE/neptune/wlan_driver/gen4m/+/1623153) 已将 DISABLE_LINK 整段包进 `if (prStaRec)`，预计能挡住本类 KE
3. ENABLE_LINK(oper=3) 同步加了 `if (prStaRec)`，避免建链路径写空指针

### 验证
4. 回归：应用/框架 disable TDLS、断连后清理 oper=4、未建链 peer 的 DISABLE_LINK

## 同类工单
- X6891：10942, 11000
- X6877：14177, 14264

## 关联案例
- **CASE-043**：同一崩溃点，触发为仅 Discovery + Beacon Timeout 断连
- **CASE-048**：同一生命周期的 TX 入队空指针
- **CASE-049**：同一生命周期的 Teardown 组帧空指针
