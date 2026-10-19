# CASE-043: TDLS 未建链 peer 断连时 DISABLE_LINK 触发 TdlsexLinkOper 空指针 KE 整机重启

## 基本信息
- **案例ID**: CASE-043
- **分类**: disconnect
- **来源**: X6877AEE-14203
- **创建时间**: 2026-10-16
- **匹配次数**: 0

## 现象描述
- FANS 自动上报 KernelReboot `0xffffff04_KE`（Blocker），无用户描述
- 机型 X6877，版本 X6877-16.3.0.160SP01(OP002PF001AZ)FANS，SoC MT6899，驱动 `wlan_drv_gen4m_6899`（build-id `f37ec198fc94860d0339fc8ec57eb795fd7fdabf`）
- 崩溃时间 2026-10-14 18:08:47（uptime 2212.404s）
- Call trace：`TdlsexLinkOper+0xe0 ← wlanSetInformation ← main_thread ← kthread`
- `Unable to handle kernel NULL pointer dereference at virtual address 0000000000000d38`

## 根因结论

**WLAN 驱动缺陷：`TdlsexLinkOper()` 处理 `TDLS_DISABLE_LINK`(oper=4) 时，按 peer MAC 查找 STA_REC 返回 NULL，未判空即读取 `+0xd38` 字段导致 KE。断连只是触发条件。**

机理链条：
1. **18:06:20** 同 AP 下 peer（随机 MAC `a6:c4:45:39:e2:8b`）发来 TDLS Discovery Request，wpa_supplicant 回 Discovery Response（action 14）；**无 Setup、无 ENABLE_LINK**，驱动侧从未为该 peer 建 TDLS STA_REC
2. **18:08:10—18:08:37** 2.4G AP `Origin_02957A`（ch9）RSSI −74 → −86 dBm
3. **18:08:44** `nicEventBeaconTimeout Reason code: 13`（21.3s 无接收）→ `aisFsmStateAbort` → `cnmStaFreeAllStaByNetwork BssIdx=0` 释放 BSS0 全部 STA_REC，断连上报延迟 5s
4. **18:08:47.256** 未找到漫游候选，`Indicate disconnection: Reason=10013`
5. **18:08:47.270** wpa_supplicant（T3879）断连清理 TDLS peer → `mtk_cfg80211_tdls_oper oper=4`
6. **18:08:47.272** main_thread `TdlsexLinkOper` → STA_REC 查找得 NULL → `ldrb w8, [x0, #0xd38]`，x0=0 → **KE**

## 排查步骤

1. **解包 AEE DB**：`.tne` 实为 tar；内部 `.zs` 为 zstd，`*.gz.zs` 需再 gunzip
2. **定位崩溃**：`pstore0` 搜 `Unable to handle` / `Internal error` / `pc :`，记下 fault addr、PC 符号、x0~x30
3. **反汇编 PC 附近指令码**（`PC: 0x...:` dump）：本案 `+0xdc bl <查找函数>` → `+0xe0 ldrb w8,[x0,#0xd38]`，x0=0 即"函数返回 NULL 未判空"
4. **还原 OID 参数**：X2/X20 指向 pvSetBuffer，按 `TDLS_CMD_LINK_OPER` 解析 peer MAC + oper（本案 16 字节，oper=4）
5. **查 TDLS 历史**：全量搜 `tdls`/`TDLS`，确认是否有 Setup Req/Rsp/Confirm 与 ENABLE_LINK（本案仅 Discovery）
6. **查断连与 STA_REC 释放时序**：`nicEventBeaconTimeout`、`aisFsmStateAbort`、`cnmStaFreeAllStaByNetwork`、`Indicate disconnection`
7. **时间换算**：无 MTK converter 时用 kmsg 中 `android time` 同步行做 uptime 锚点换算

## 关键日志

```
// TDLS 仅 Discovery，未建链
[ 2066.101309] statsParsePktInfo: <RX> TDLS type 2, category 12, Action 10, Token 1
[ 2066.101678] TdlsexLinkMgt: ucBssIdx=0, ucActionCode=14, ucDialogToken=1
[ 2066.101797][T3879] mtk_cfg80211_tdls_mgmt: rStatus: 0

// Beacon 丢失断连，释放 BSS0 STA_REC
[ 2209.686821] nicEventBeaconTimeout: Reason code: 13
[ 2209.686925] aisFsmStateAbort: DiscReason[1], CurState[11], delayIndi[1]
[ 2209.687382] cnmStaFreeAllStaByNetwork: BssIdx=0, StaRecIndexExcluded=27
[ 2212.388391] kalIndicateStatusAndComplete: Indicate disconnection: Reason=10013 Locally[0]

// DISABLE_LINK → KE
[ 2212.402150][T3879] mtk_cfg80211_tdls_oper: ucBssIndex = 0, oper=4
[ 2212.404245][T3808] TdlsexLinkOper: prCmd->oper=4, u4SetBufferLen=16
[ 2212.404290][T3808] Unable to handle kernel NULL pointer dereference at virtual address 0000000000000d38
[ 2212.439687][T3808] pc : TdlsexLinkOper+0xe0/0x1e0 [wlan_drv_gen4m_6899]
[ 2212.440800][T3808] x1 : 0000000000000000 x0 : 0000000000000000
```

## TAG
- Kernel Exception
- KernelReboot
- 驱动空指针
- TdlsexLinkOper
- TDLS
- TDLS Discovery
- TDLS_DISABLE_LINK
- Beacon Timeout
- cnmStaFreeAllStaByNetwork
- 断开连接
- 信号弱
- 2.4G频段
- MT6899
- gen4m
- MTK driver
- X6877

## 建议措施

### WLAN 驱动（必须）
1. `TdlsexLinkOper()` 各 oper 分支对 STA_REC 查找结果判空，未找到 peer 时返回 `WLAN_STATUS_INVALID_DATA`/`WLAN_STATUS_FAILURE`，不得解引用
2. 同步排查 `mtk_cfg80211_tdls_oper` 入参校验及 `TdlsexLinkMgt` 等 TDLS 路径同类问题
3. 向 MTK 提 eService（附 build-id、`TdlsexLinkOper+0xe0`、fault addr `0xd38`），确认被调函数/字段名及是否已有官方 patch

### 复现
4. 手机连 AP，同 AP 下 TDLS 能力设备对其发起 Discovery；随后让手机断连（关 AP / 拉远丢 Beacon / 手动断开），观察 `oper=4` 后是否 KE

### 影响评估
5. FANS/KernelReboot 按 `TdlsexLinkOper` 检索 MT6899 / gen4m 其它项目同类 KE

## 关联案例
- **CASE-023**（弱相关）：同为 Beacon 丢失（BTO）断连背景；本案关注断连后驱动 TDLS 清理路径崩溃

## 分析报告
- `AI-result/issues/X6877AEE-14203/X6877AEE-14203-analysis.md`
- 本地日志：`AI-result/issues/X6877AEE-14203/logs/`
