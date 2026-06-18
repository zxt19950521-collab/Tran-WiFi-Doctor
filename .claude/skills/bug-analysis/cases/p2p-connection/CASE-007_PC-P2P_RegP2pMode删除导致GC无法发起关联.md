# CASE-007: 同步 wifi.cfg 误删 RegP2pMode 导致手机 GC 无法发起 P2P 关联

## 基本信息
- **案例ID**: CASE-007
- **分类**: p2p-connection
- **来源**: 本地日志 `APLog_2026_0605_095756`（PC 与手机 P2P 连接失败）+ Gerrit CR 1532957 / TOS163-33727
- **创建时间**: 2026-06-05
- **匹配次数**: 0
- **根因状态**: 已确认（代码侧 + 日志侧）

## 现象描述
- 场景：极速互传 / WiFi Direct，**手机 GC 连 PC GO**（`DIRECT-pc-84927`）
- 手机点连后约 **10s** 报失败，连续多次 **100% 失败**
- 平台：MTK gen4m（cla5_h8910 / cla6_h8910）
- 每次 `Trying to associate` 的**同一毫秒**即 `Association request to the driver failed`
- 内核 `authSendAuthFrame=0`、无 `JoinComplete` → **连一帧 Auth 都没发**
- 满 10s → `P2P-GROUP-FORMATION-FAILURE` / `FORMATION_FAILED`
- `wpa_supplicant` 把 GO BSSID 加 ignore list（10s→60s、count 递增），重试在窗口内"出生即死"

## 根因结论
Gerrit **CR [1532957](https://gerrit.transsion.com/c/TRAN_OD_CODE/vendor/transsion/projects/+/1532957)**（`TOS163-33727 [WIFI][cla5&cla6]同步v版本wifi.cfg`，已 MERGED）在同步 wifi.cfg 时**误删 `RegP2pMode 6`**（`cla5_h8910/wlan/config/wifi.cfg`、`cla6_h8910/wlan/config/wifi.cfg` 各删 1 行）。

`RegP2pMode` 由 MTK gen4m 驱动 `wlan_lib.c` 解析消费，控制 **P2P 工作模式/能力**；删除后回退驱动默认，**手机以 GC 发起 P2P 关联的能力失效** → 驱动对 `connect` **同步拒绝** → `Association request to the driver failed`。

**与 GO 所在信道无关、与 STA 并发无关**（wlan0 断开后仍失败）。

## 排查步骤
1. main_log 定位 4 次 `startP2p` → `Trying to associate` → 同毫秒 `Association request to the driver failed` → 10s `P2P-GROUP-FORMATION-FAILURE`
2. kernel `.localtime` 确认 `mtk_p2p_cfg80211_connect` 后无 `authSendAuthFrame`、无 JOIN、无 p2pRoleFsm 动作
3. 排除"扫不到 GO"：GO beacon 在扫描中多次可见
4. 排除 DBDC 并发：第 3/4 次失败时 wlan0 已断开仍被拒
5. 代码侧：Gerrit CR 1532957 diff 确认 `RegP2pMode 6` 被删除

## 关键日志
```
// 09:56:59 发起 GC 连接，同毫秒驱动拒绝关联
06-05 09:56:59.451 welinkBLE: connectP2pDevice: now connect {DIRECT-pc-84927}
06-05 09:56:59.496 wpa_supplicant: p2p0: Trying to associate with SSID 'DIRECT-pc-84927'
06-05 09:56:59.497 wpa_supplicant: p2p0: Association request to the driver failed
06-05 09:56:59.497 wpa_supplicant: p2p0: BSSID be:09:b9:55:f7:2c ignore list count incremented to 2, ignoring for 10 seconds

// 10s 组形成失败
06-05 09:57:09.497 wpa_supplicant: P2P-GROUP-FORMATION-FAILURE
06-05 09:57:09.498 wpa_supplicant: P2P-GROUP-REMOVED p2p0 client reason=FORMATION_FAILED

// 内核：connect 后无 Auth
01:56:59.497 mtk_p2p_cfg80211_connect: bssid: be:09:**:**:**:2c, band: 1, freq: 5765.
（此后 10s 内 authSendAuthFrame=0，无 JOIN）

// 代码回归：CR 1532957 删除 RegP2pMode 6
- RegP2pMode 6        ← 被删除（根因）
  cla5_h8910/wlan/config/wifi.cfg
  cla6_h8910/wlan/config/wifi.cfg
```

## 判别式（区别于近似案例）
| 维度 | 本案例 |
|---|---|
| wpa 关键日志 | `Association request to the driver failed`（本机驱动同步拒绝）|
| Auth 帧 | `authSendAuthFrame=0`（**未发**）|
| 信道 | **无关** |
| STA 并发 | **无关** |
| vs CASE-004 | CASE-004 **已发 74 帧 Auth、PC GO 不回复**；本案例**根本没发 Auth** |

## TAG
- P2P-GROUP-FORMATION-FAILURE
- Association request to the driver failed
- GC驱动拒绝关联
- 未发Auth
- RegP2pMode删除
- wifi.cfg同步回归
- MTK gen4m
- 极速互传
- PC GO
- CR1532957/TOS163-33727

## 建议措施
1. **恢复 `RegP2pMode 6`**（cla5_h8910 / cla6_h8910 的 wifi.cfg），回推修正 CR
2. 核对本次同步是否还误删其它必要项（coexSetIdcFreqIdx* / DropPackets*）
3. 打恢复版回归：手机 GC 连 PC GO，确认 `connect` 成功、能发 Auth、成组
4. 回归面：确认其它走相同 wifi.cfg 同步的机型未丢 `RegP2pMode`

## 相关案例
- CASE-004: PC 长时间待机后 P2P 连接失败（GC 发 Auth 无回复）——同场景但失败阶段更靠后（已发 Auth）
- CASE-001: Windows PC 接收端 P2P 冲突导致极速互传连接失败率高
