# CASE-005: AirTransfer与NearbySharing P2P资源冲突导致NFC碰传失败

## 基本信息
- **案例ID**: CASE-005
- **分类**: p2p-connection
- **来源**: OS162-40628
- **设备**: Infinix X6877 (Android 16, TOS xos16.2.0)
- **应用**: 快传 (com.transsion.airtransfer) v1.2.1.238
- **创建时间**: 2026-06-04
- **匹配次数**: 0

## 现象描述
- 使用快传 NFC 碰传功能传输视频文件时连接失败，必现
- 错误码 105，connectDevice timeout
- 重试 4 次以上均失败

## 根因结论
AirTransfer 创建 P2P Group 时移除了 NearbySharing (quickshare) 正在使用的 GC 连接，NearbySharing 自动重连与 AirTransfer 的 Group 创建产生竞态，底层返回 BUSY，导致 GO 创建失败。

## 关键日志
```
// NearbySharing 正在通过 WIFI_DIRECT 传输文件
18:24:15.286 NearbyConnections: KEEP_ALIVE frame from endpoint 4Z13 on channel WIFI_DIRECT
18:24:15.959 NearbySharing: TransferComplete(payloadId=-4940165479340496742)

// AirTransfer 移除 NearbySharing 的 GC 连接
18:24:16.218 AirTransfer-TransferBusinessManager: createWifiP2PGroup
18:24:16.233 welinkBLE: Wi-Fi P2P Group is formed, remove group owner
18:24:16.252 wpa_supplicant: P2P-GROUP-REMOVED p2p0 client reason=REQUESTED

// NearbySharing 自动重连导致 BUSY
18:24:16.265 NearbyMediums: MEDIUM_ERROR [WIFI_DIRECT][CONNECTION_ABORT]
18:24:16.268 NearbyConnections: [ReconnectManager] start auto-reconnect for WIFI_DIRECT
18:24:16.298 NearbyMediums: Failed to remove group, reason : [2]BUSY.
18:24:17.465 NearP2pManager: onCreateGroupFail
18:24:17.779 wpa_supplicant: P2P-GROUP-FORMATION-FAILURE
```

## 建议
1. 创建 Group 前调用 `requestGroupInfo()` 检查 P2P 是否正在使用
2. 如有 GC 连接，优先复用而非创建新 GO
3. Framework 层增加多应用 P2P 资源仲裁机制

## TAG
- P2P_RESOURCE_CONFLICT
- P2P_BUSY
- P2P_GROUP_FORMATION_FAILURE
- NFC_CONNECT_TIMEOUT
- NearbySharing

## 复现条件
1. NearbySharing (quickshare) 正在通过 WIFI_DIRECT 传输文件
2. 同时使用 AirTransfer NFC 碰传发送视频文件
3. AirTransfer 移除 NearbySharing 的 GC 连接后创建 Group 失败

## 相关案例
- CASE-001: Windows PC接收端P2P冲突导致极速互传连接失败率高
