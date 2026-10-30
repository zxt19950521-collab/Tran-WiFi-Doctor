# CASE-077: TP-LINK WPA2/WPA3 SAE 路径 IGTK KeyID 非法导致连接失败

## 基本信息
- **案例ID**: CASE-077
- **分类**: auth-failure
- **来源**: TOS170-42568
- **创建时间**: 2026-10-30
- **匹配次数**: 0

## 现象描述
- 设备：CO7 / MTK（CO7-17.0.0.042），同平台 X6765 同样失败；竞品 X6878 同场大多成功
- 挂测 `MC_WiFi_STACON_0341` 连家用路由 `TP-LINK_XDR3010-Y`
- WPA/WPA2-PSK 全过；WPA2/WPA3-PSK 混合 + SAE + MFPC 多种 PHY 失败（CO7 8/19）
- 扫描可见目标，RSSI 强（约 −46 dBm），BSSID `68:77:24:e4:4f:ad`
- 挂测 UI 异常后执行 `cmd wifi connect-network "<ssid>" "wpa3"`

## 根因结论
**主因：故障 AP 的 IGTK KDE KeyID 高字节非 0（形如 `0xXX04`），STA `wpa_supplicant` 按规范拒绝安装 IGTK 并拆 4-Way；竞品容忍后能连通。**

- SAE 关联成功（`assoc key_mgmt 0x400`），四次握手 M1/M3 都到
- M3 后 `WPA: Invalid IGTK KeyID 58884`（`0xE604`，低字节=合法 KeyID 4）→ `RSN: Failed to configure IGTK` → 本机 `CTRL-EVENT-DISCONNECTED reason=1`
- 全部非法 KeyID 低字节恒为 `0x04`，高字节随时间变（像 IPN 污染 KeyID reserved 字节）
- 偶发无 IGTK 报错即可 CONNECTED（PTK/GTK 本身正常）；脚本再强制 `wpa3` 又踩中
- 同 AP、同一条 `wpa3` 命令：X6878 `check_connect=True`，CO7/X6765 失败 → 差在 STA IGTK 校验，不是密码/扫描/射频

## 排查步骤
1. 确认扫描 cap 含 `[RSN-PSK+SAE][MFPC]`，且失败用例走 SAE（`key_mgmt 0x400`）而非 PSK（`0x2`）
2. main log 搜 `Invalid IGTK KeyID`；核对十进制 KeyID 低字节是否恒为 4 或 5（`58884=0xE604`）
3. 看是否 M1/M3 已到、有无 `4-Way Handshake failed` / `reason=15`：有 M3 且 reason=1 是 IGTK 安装失败，不是缺 EAPOL
4. 对照 WPA2 成功路径（`key_mgmt 0x2`、握手 ver=2、无 IGTK 报错）
5. 对照竞品是否同一 `connect-network wpa3` 却 check_connect 成功
6. RSSI 强仍失败 → 排除射频；无 dhcp 日志 → 失败在 RSNA 之前

## 关键日志
```
wpa_supplicant: assoc key_mgmt 0x400 network key_mgmt 0xc000d42
wpa_supplicant: wlan0: Associated with 68:77:24:e4:4f:ad
wpa_supplicant: wlan0: WPA: RX message 1 of 4-Way Handshake from 68:77:24:e4:4f:ad (ver=0)
wpa_supplicant: wlan0: RSN: RX message 3 of 4-Way Handshake from 68:77:24:e4:4f:ad (ver=0)
wpa_supplicant: wlan0: WPA: Invalid IGTK KeyID 58884
wpa_supplicant: wlan0: RSN: Failed to configure IGTK
wpa_supplicant: wlan0: CTRL-EVENT-DISCONNECTED bssid=68:77:24:e4:4f:ad reason=1 locally_generated=1
# 脚本回退
adbd: cmd wifi connect-network "TP-LINK_XDR3010-Y_2.4G" "wpa3" "12345678"
wpa_supplicant: wlan0: CTRL-EVENT-ASSOC-REJECT bssid=68:77:24:e4:4f:ad status_code=1
```

## 解决方案
1. STA：改 `external/wpa_supplicant_8/src/rsn_supp/wpa.c` → `wpa_supplicant_install_igtk()`。`WPA_GET_LE16(keyid) > 4095` 但 `keyid[0]` 为 4/5 时，用低字节继续装 IGTK，不要 `return -1` 拆 4-Way；`set_key` 仍失败则跳过 IGTK、PTK/GTK 走完
2. 过渡：`wpa_supplicant_process_3_of_4()` 里 `install_igtk() < 0` 不中断 4-Way（连通优先，BIP 弱一档）
3. AP：TP-LINK 固件把 IGTK KDE KeyID 做成 2 字节、取值 4 或 5、第二字节为 0
4. 验证：`adb shell cmd wifi connect-network "<ssid>" wpa3 <pwd>`；允许 warning，不能再 reason=1；纯 WPA2 / 正常 PMF AP 回归
5. 挂测：已 CONNECTED 后不要立刻强制 `wpa3` 拆链

## TAG
- 认证失败
- Invalid IGTK KeyID
- Failed to configure IGTK
- WPA3/SAE
- SAE
- MFPC
- 802.11w
- PMF
- reason=1
- ASSOC-REJECT
- 4次握手
- 路由器兼容性
- TP-LINK
- XDR3010
- CO7
- X6765
- X6878
- 竞品对照
- MTK平台
- wpa_supplicant
- 挂测

## 相关案例
- CASE-064：家用路由四次握手失败（AP 不发 M1 / 不回 M3）。本案 M1/M3 都到，卡在 IGTK 安装
