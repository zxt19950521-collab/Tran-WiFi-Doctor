# CASE-004: PC 长时间待机后 P2P 连接失败（GC 发 Auth 无回复）

## 基本信息
- **案例ID**: CASE-004
- **分类**: p2p-connection
- **来源**: K16SFA-375
- **创建时间**: 2026-06-03
- **匹配次数**: 0
- **根因状态**: 待确认（缺空口日志，未最终定位）

## 现象描述
- 场景：【AIOT】【STR4】【PIR】【超正】联想办公电脑（PC）连接手机失败
- 预置条件：**电脑长时间待机**后发起连接
- PC 作 **P2P GO**，手机作 **GC**；手机弹窗用户点“允许”后连接失败
- PC（基座端）已发出 P2PInfo，但 **1 分钟内等不到 GC 上线**，未收到 GC 上线的 `ReqType=512` JSON
- 手机 GC 扫描到 PC GO 后，driver **反复发送 Auth 帧但收不到任何 Auth Response**，约 10 秒后 `P2P-GROUP-FORMATION-FAILURE`
- 平台：MTK；频段：5G（ch149 / 5745MHz）；环境：周围 58 个 AP（AP 密集）

## 根因结论（待确认）
失败发生在 **P2P Group Formation 的 Auth 阶段**：手机 GC 反复发 Auth 给 PC GO（`f2:0a:**:**:**:7f`）却始终收不到 Auth Response，10 秒后组形成失败。

两类可能方向（手机端日志无法区分“PC 没收到”还是“收到没回”，需空口包确认）：
1. **PC GO 侧异常（嫌疑最大）**：PC 长时间待机后 WiFi Direct GO 进入异常/休眠态，未在 ch149 正常响应 Auth（机理近 CASE-001）
2. **空口 / RX 路径问题**：58-AP 密集环境，PC 未收到 Auth 或收到未回（机理近 CASE-002 形态 B）

## 排查步骤
1. 通过 PC 端“等不到 GC 上线、无 `ReqType=512`”定位失败发生在 P2P 连接建立阶段
2. 手机端定位 `P2P-GROUP-FORMATION-FAILURE`（10:48:30），回溯到 10:48:20 `start p2p gc`
3. 检查 MTK kernel log，发现 `authSendAuthFrame` 连续发送 Auth（Seq 147→160）均无 Auth Response
4. 检查 ScanDone，发现周围 58 个 AP（Country=CN），环境密集
5. 结合 summary “电脑长时间待机”，怀疑 PC GO 长待机后异常
6. 待补充：ch149 空口 sniffer，确认 PC 是否收到/回复 Auth

## 关键日志
```
// 10:48:20 手机启动 GC 发起连接
05-19 10:48:20.764 NearP2pManager: TransConnect:startP2p: start p2p gc
05-19 10:48:20.764 welinkBLE: connectP2pDevice: now connect {DIRECT-5Z-TCIRCLE}

// driver 反复发 Auth 给 PC GO（f2:0a:**:**:**:7f, 5745MHz/ch149），无回复
05-19 02:48:23.326 mtk_p2p_cfg80211_connect: bssid: f2:0a:**:**:**:7f, band:1, freq:5745
05-19 02:48:23.352 authSendAuthFrame: Send Auth, TranSeq:1, Seq:147 ... DA: f2:0a:**:**:**:7f
05-19 02:48:23.575 authSendAuthFrame: Send Auth, TranSeq:1, Seq:150 ...
05-19 02:48:24.504 authSendAuthFrame: Send Auth, TranSeq:1, Seq:160 ...   // 仍无 Auth Response

// 10:48:30 组形成失败
05-19 10:48:30.870 wpa_supplicant: P2P-GROUP-FORMATION-FAILURE

// 环境：扫描到 58 个 AP
05-19 02:48:25.493 SCANLOG: [SCN:500:F2D] ... 58: ... Country Code = CN, Detected_Channel_Num = 22

// 10:45:35 较早一次：手机以 client 关联成功，但 supplicant AIDL 加载持久组报错（疑为告警）
05-19 10:45:35.649 wpa_supplicant: CTRL-EVENT-CONNECTED ... P2P-GROUP-STARTED p2p0 client
05-19 10:45:35.683 SupplicantP2pIfaceHalAidlImpl: getNetwork failed ... Failed to retrieve network object for 25
```

## TAG
- P2P-GROUP-FORMATION-FAILURE
- GC加入GO超时
- Auth无回复
- AP密集
- PC长时间待机
- 5G ch149
- MTK driver
- SupplicantP2pIfaceHal AIDL异常

## 建议措施
1. 抓 ch149/5745MHz 空口 sniffer，确认 PC 是否收到/回复 Auth（区分根因）
2. 干净环境复测，排除 AP 密集干扰
3. 对照“PC 刚唤醒 vs 长待机”复测，验证长待机导致 GO 异常假设
4. 开启完整日志：开发者详情日志 + `persist.log.tag DEBUG` + MTK WiFi Driver Log = More

## 相关案例
- CASE-001: Windows PC 接收端 P2P 冲突导致极速互传连接失败率高（PC 作 GO / GC 无法加入）
- CASE-002: 双端 2.4G 网络下 Android 碰传偶现发送失败（发 Auth 后 RX 异常 / AP 密集）
