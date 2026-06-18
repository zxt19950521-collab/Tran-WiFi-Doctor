#!/usr/bin/env python3
"""
WiFi Link Quality 绘图脚本
从 MTK kernel log 中提取 Tput/Tx(rate)/Rx(rate)/rssi/PER 数据并绘制四象限曲线图。
支持多文件合并绘制到同一张图。
支持插入连接状态时间轴图（从 main_log 提取），时间对齐，线宽一致。

数据来源：
- Tput: kalPerMonUpdate 中的吞吐量
- Tx(rate): wlanLinkQualityMonitor 中的发送 PHY Rate
- Rx(rate): wlanLinkQualityMonitor 中的接收 PHY Rate
- rssi: mtk_cfg80211_get_station 中的 MovAvg_rssi（周期约 3s）；勿用 vendor_event_rssi_beyond_range 的稀疏阈值事件
- PER: wlanLinkQualityMonitor 或 mtk_cfg80211_get_station 中的 PER
- 连接状态: main_log 中的 wlan/P2P/softap 连接事件

用法：
  # 单文件（仅 link quality）
  python scripts/plot_wifi_link_quality.py <kernel_log_file>

  # 多文件合并到一张图
  python scripts/plot_wifi_link_quality.py file1.localtime file2.localtime -o output/ -f combined.png

  # 带连接状态图（-m 指定 main_log 文件）
  python scripts/plot_wifi_link_quality.py kernel.localtime -m main_log -o output/ -f combined.png

  # 作为模块导入
  from scripts.plot_wifi_link_quality import plot_from_file, plot_from_files
  plot_from_file("path/to/kernel_log.localtime", output_dir="AI-result/issues/XXX/")
  plot_from_files(["file1.localtime", "file2.localtime"], output_dir="output/", save_filename="combined.png",
                  main_log_paths=["main_log_1", "main_log_2"])
"""

import re
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import unquote

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
except ImportError:
    print("正在安装 matplotlib...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches


# ==================== 连接状态提取（来自 plot_connection_timeline.py） ====================

# freq (MHz) → channel number
FREQ_CHANNEL_MAP = {
    # 2.4 GHz
    2412: 1, 2417: 2, 2422: 3, 2427: 4, 2432: 5, 2437: 6,
    2442: 7, 2447: 8, 2452: 9, 2457: 10, 2462: 11, 2467: 12,
    2472: 13, 2484: 14,
    # 5 GHz (常见信道)
    5180: 36, 5200: 40, 5220: 44, 5240: 48, 5260: 52, 5280: 56,
    5300: 60, 5320: 64, 5500: 100, 5520: 104, 5540: 108, 5560: 112,
    5580: 116, 5600: 120, 5620: 124, 5640: 128, 5660: 132, 5680: 136,
    5700: 140, 5720: 144, 5745: 149, 5765: 153, 5785: 157, 5805: 161,
    5825: 165,
    # 6 GHz
    5955: 1, 5975: 5, 5995: 9, 6015: 13, 6035: 17, 6055: 21,
    6075: 25, 6095: 29, 6115: 33,
}


def freq_to_channel(freq_mhz):
    """Convert frequency (MHz) to channel number string."""
    if freq_mhz in FREQ_CHANNEL_MAP:
        ch = FREQ_CHANNEL_MAP[freq_mhz]
        if freq_mhz < 2500:
            return f"2.4G ch{ch}"
        elif freq_mhz < 6000:
            return f"5G ch{ch}"
        else:
            return f"6G ch{ch}"
    return f"{freq_mhz}MHz"


def parse_connection_time(time_str):
    """Parse 'MM-DD HH:MM:SS.mmmmmm' or 'MM-DD HH:MM:SS.mmm' to datetime (year=2026)."""
    for fmt in ('%m-%d %H:%M:%S.%f', '%m-%d %H:%M:%S'):
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            return dt.replace(year=2026)
        except ValueError:
            continue
    return None


def extract_ssid_from_id_str(id_str):
    """Extract SSID from URL-encoded id_str JSON."""
    try:
        decoded = unquote(id_str)
        m = re.search(r'configKey.*?\\"(.+?)\\"', decoded)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


class ConnectionSession:
    """Represents one connection session for an interface."""
    def __init__(self, interface, start_time, ssid="", bssid="", freq=0,
                 role="", extra=""):
        self.interface = interface  # 'wlan', 'p2p', 'softap'
        self.start_time = start_time
        self.end_time = None
        self.ssid = ssid
        self.bssid = bssid
        self.freq = freq
        self.role = role  # 'GO', 'client', or ''
        self.extra = extra  # disconnect reason, etc.
        self.end_reason = ""
        self.channel_override = ""  # 当 freq 缺失时，由 kernel 推断的信道(如 "2.4G ch11")

    @property
    def channel(self):
        if self.freq:
            return freq_to_channel(self.freq)
        if self.channel_override:
            return self.channel_override
        return ""

    @property
    def duration(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def label(self):
        """Generate label for the session bar."""
        parts = []
        if self.ssid:
            parts.append(self.ssid)
        if self.channel:
            parts.append(self.channel)
        if self.bssid:
            parts.append(format_bssid_display(self.bssid))
        if self.role:
            parts.append(self.role)
        return " | ".join(parts)


def is_p2p_iface(iface: str) -> bool:
    """p2p0 / p2p-p2p0-0 等接口上的 STA 事件属于 P2P 链路，不应计入 WLAN。"""
    return iface.lower().startswith('p2p')


def _sessions_overlap(a, b, slack_sec=2.0):
    """两段时间是否重叠(允许少量起止时间差)。"""
    a_end = a.end_time or a.start_time
    b_end = b.end_time or b.start_time
    if a.start_time is None or b.start_time is None:
        return False
    pad = timedelta(seconds=slack_sec)
    return (a.start_time - pad) <= b_end and (b.start_time - pad) <= a_end


def dedupe_p2p_wlan_sessions(sessions):
    """去掉与 P2P 会话重复的 WLAN 记录。

    P2P 建组时 wpa_supplicant 会在 p2p* 接口上同时打印 CTRL-EVENT-CONNECTED
    与 P2P-GROUP-STARTED，若前者被误归入 wlan 会与 p2p 行重复显示。
    """
    p2p_list = sessions.get('p2p', [])
    if not p2p_list:
        return sessions

    kept = []
    for w in sessions.get('wlan', []):
        dup = False
        if w.ssid and w.ssid.upper().startswith('DIRECT-'):
            dup = True
        else:
            for p in p2p_list:
                if not _sessions_overlap(w, p):
                    continue
                if w.ssid and p.ssid and w.ssid == p.ssid:
                    dup = True
                    break
                if w.bssid and p.bssid and w.bssid.lower() == p.bssid.lower():
                    dup = True
                    break
        if not dup:
            kept.append(w)
    sessions['wlan'] = kept
    return sessions


def extract_connection_sessions(file_path):
    """
    Parse main_log for wlan/P2P/softap connection events.
    Returns dict: {'wlan': [ConnectionSession], 'p2p': [ConnectionSession], 'softap': [ConnectionSession]}

    Supports multiple log patterns:
    - Trying to associate with SSID 'xxx' (extract SSID)
    - Associated with xx:xx:xx:xx:xx:xx (extract BSSID)
    - CTRL-EVENT-CONNECTED - Connection to xx:xx:xx:xx:xx:xx completed (extract BSSID)
    - CTRL-EVENT-DISCONNECTED bssid=xx:xx:xx:xx:xx:xx reason=N (extract BSSID and reason)
    """
    sessions = {'wlan': [], 'p2p': [], 'softap': []}
    open_wlan = {}  # bssid -> Session
    open_p2p = {}   # iface -> Session
    open_softap = None

    # Track pending association (SSID from "Trying to associate")
    pending_assoc = {}  # iface -> {'ssid': str, 'timestamp': datetime}

    time_re = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')

    # wlan0: Trying to associate with SSID 'xxx'
    trying_associate_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+Trying to associate with SSID\s+\'([^\']+)\''
    )

    # wlan0: Associated with xx:xx:xx:xx:xx:xx
    associated_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+Associated with\s+([0-9a-fA-F:]+)'
    )

    sta_connect_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+CTRL-EVENT-CONNECTED\s+-\s+Connection to\s+([0-9a-fA-F:]+)\s+completed'
        r'(?:\s+\[id=\d+\s+id_str=([^\]]*)\])?'
        r'(?:\s+freq=(\d+))?'
    )

    sta_disconnect_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+CTRL-EVENT-DISCONNECTED\s+bssid=([0-9a-fA-F:]+)\s+reason=(\d+)'
        r'(?:\s+locally_generated=(\d+))?'
    )

    p2p_started_re = re.compile(
        r'wpa_supplicant.*P2P-GROUP-STARTED\s+(\S+)\s+(GO|client)\s+ssid="([^"]+)"\s+freq=(\d+)'
        r'(?:\s+go_dev_addr=([0-9a-fA-F:]+))?'
    )

    p2p_removed_re = re.compile(
        r'wpa_supplicant.*P2P-GROUP-REMOVED\s+(\S+)\s+(GO|client)\s+reason=(\S+)'
    )

    ap_enabled_re = re.compile(r'wpa_supplicant.*AP-ENABLED')
    ap_disabled_re = re.compile(r'wpa_supplicant.*AP-DISABLED')

    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    if not lines:
        print(f"无法解码文件：{file_path}")
        return sessions

    for line in lines:
        line = line.strip()
        if not line:
            continue

        tm = time_re.match(line)
        if not tm:
            continue
        ts = parse_connection_time(tm.group(1))
        if not ts:
            continue

        # --- Trying to associate with SSID ---
        m = trying_associate_re.search(line)
        if m:
            iface = m.group(1)
            ssid = m.group(2)
            if not is_p2p_iface(iface):
                pending_assoc[iface] = {'ssid': ssid, 'timestamp': ts}
            continue

        # --- Associated with BSSID ---
        m = associated_re.search(line)
        if m:
            iface = m.group(1)
            bssid = m.group(2)
            if not is_p2p_iface(iface) and iface in pending_assoc:
                pending_assoc[iface]['bssid'] = bssid
            continue

        # --- wlan STA CONNECTED ---
        m = sta_connect_re.search(line)
        if m:
            iface = m.group(1)
            # p2p* 接口上的 CONNECTED 由 P2P-GROUP-STARTED 跟踪，避免与 WLAN 重复计数
            if is_p2p_iface(iface):
                continue
            bssid = m.group(2)
            id_str = m.group(3) or ""
            freq = int(m.group(4)) if m.group(4) else 0
            ssid = extract_ssid_from_id_str(id_str) or ""

            # Check if we have pending association info
            if iface in pending_assoc:
                pending = pending_assoc[iface]
                if not ssid:
                    ssid = pending.get('ssid', '')
                if not bssid and 'bssid' in pending:
                    bssid = pending['bssid']
                del pending_assoc[iface]

            sess = ConnectionSession('wlan', ts, ssid=ssid, bssid=bssid, freq=freq)
            open_wlan[bssid] = sess
            sessions['wlan'].append(sess)
            continue

        # --- wlan STA DISCONNECTED ---
        m = sta_disconnect_re.search(line)
        if m:
            iface = m.group(1)
            if is_p2p_iface(iface):
                continue
            bssid = m.group(2)
            reason = m.group(3)
            locally = m.group(4)
            reason_str = f"reason={reason}"
            if locally:
                reason_str += f" local={locally}"
            if bssid in open_wlan:
                open_wlan[bssid].end_time = ts
                open_wlan[bssid].end_reason = reason_str
                del open_wlan[bssid]
            continue

        # --- P2P GROUP STARTED ---
        m = p2p_started_re.search(line)
        if m:
            iface = m.group(1)
            role = m.group(2)
            ssid = m.group(3)
            freq = int(m.group(4))
            go_mac = m.group(5) or ""
            sess = ConnectionSession('p2p', ts, ssid=ssid, bssid=go_mac, freq=freq, role=role)
            open_p2p[iface] = sess
            sessions['p2p'].append(sess)
            continue

        # --- P2P GROUP REMOVED ---
        m = p2p_removed_re.search(line)
        if m:
            iface = m.group(1)
            reason = m.group(3)
            if iface in open_p2p:
                open_p2p[iface].end_time = ts
                open_p2p[iface].end_reason = f"reason={reason}"
                del open_p2p[iface]
            continue

        # --- SoftAP ---
        if ap_enabled_re.search(line):
            sess = ConnectionSession('softap', ts)
            open_softap = sess
            sessions['softap'].append(sess)
            continue

        if ap_disabled_re.search(line):
            if open_softap:
                open_softap.end_time = ts
                open_softap = None
            continue

    # Close any open sessions at the last timestamp
    last_ts = None
    for line in reversed(lines):
        tm = time_re.match(line.strip())
        if tm:
            last_ts = parse_connection_time(tm.group(1))
            break

    if last_ts:
        for sess in open_wlan.values():
            if not sess.end_time:
                sess.end_time = last_ts
                sess.end_reason = "(open)"
        for sess in open_p2p.values():
            if not sess.end_time:
                sess.end_time = last_ts
                sess.end_reason = "(open)"
        if open_softap and not open_softap.end_time:
            open_softap.end_time = last_ts
            open_softap.end_reason = "(open)"

    # Filter out sessions without end_time
    for iface in sessions:
        sessions[iface] = [s for s in sessions[iface] if s.end_time]

    return dedupe_p2p_wlan_sessions(sessions)


def merge_connection_sessions(sessions_list):
    """Merge sessions from multiple files, sorted by start_time."""
    merged = {'wlan': [], 'p2p': [], 'softap': []}
    for sessions in sessions_list:
        for iface in merged:
            merged[iface].extend(sessions[iface])
    for iface in merged:
        merged[iface].sort(key=lambda s: s.start_time)
    return dedupe_p2p_wlan_sessions(merged)


# Color palette for connection sessions
CONNECTION_COLORS = [
    '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
    '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC',
    '#86BCB6', '#D37295', '#FABFD2', '#B6992D', '#499894',
]


# ==================== 时间对齐（kernel UTC ↔ main_log 本地时间） ====================

def detect_tz_offset_hours(file_path):
    """从 .localtime 头部的 'timezone:XXX' 推断 kernel(UTC) → 设备本地时间 的偏移小时数。

    MTK kernel_log_converter 转换出的 .localtime 内时间戳为 UTC，但文件头会带上
    设备时区(例如 '----- timezone:Asia/Manila')。main_log 用的是设备本地时间。
    因此对齐时需要给 kernel 时间加上该时区的 UTC 偏移。

    返回 float 小时数；无法检测时返回 None。
    """
    if ZoneInfo is None:
        return None
    tz_name = None
    data_date = None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(30):
                line = f.readline()
                if not line:
                    break
                if tz_name is None:
                    m = re.search(r'timezone:\s*([\w/+\-]+)', line)
                    if m:
                        tz_name = m.group(1).strip()
                if data_date is None:
                    dm = re.match(r'(\d{2})-(\d{2})\s', line)
                    if dm:
                        data_date = (int(dm.group(1)), int(dm.group(2)))
                if tz_name and data_date:
                    break
    except OSError:
        return None
    if not tz_name:
        return None
    try:
        mm, dd = data_date if data_date else (1, 1)
        dt = datetime(2026, mm, dd, tzinfo=ZoneInfo(tz_name))
        off = dt.utcoffset()
        if off is None:
            return None
        return off.total_seconds() / 3600.0
    except Exception:
        return None


def shift_data_times(data, all_times, offset_hours):
    """把 kernel 提取数据中的所有时间戳平移 offset_hours 小时（对齐到本地时间）。"""
    if not offset_hours:
        return data, all_times
    delta = timedelta(hours=offset_hours)
    for key in data:
        times, nums = data[key]
        data[key] = ([t + delta for t in times], nums)
    all_times = [t + delta for t in all_times]
    return data, all_times


# TranWifiSmartAssistantController 周期监控：当前连接的网络 id 与 SSID
_SMART_NET_RE = re.compile(
    r'TranWifiSmartAssistantController.*?mCurrentNetwork\s*:\s*(-?\d+)\s+'
    r'SSID\s*:\s*"?([^"\r\n]*?)"?\s*$'
)
_SMART_TS_RE = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')


def extract_smart_assistant_samples(file_path):
    """从单个 main_log 提取 SmartAssistant STA 采样 (ts, net_id, ssid)。"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    samples = []
    for line in lines:
        m = _SMART_NET_RE.search(line)
        if not m:
            continue
        tm = _SMART_TS_RE.match(line)
        if not tm:
            continue
        ts = parse_connection_time(tm.group(1))
        if ts is None:
            continue
        net_id = m.group(1)
        ssid = m.group(2).strip()
        if net_id == '-1' or not ssid:
            continue
        samples.append((ts, net_id, ssid))
    return samples


def build_smart_assistant_sessions(samples, disconnect_times=None):
    """将 SmartAssistant 采样序列切成连接段（全局一次分段，避免多 main_log 文件边界误切）。"""
    if not samples:
        return []
    samples = sorted(samples, key=lambda x: x[0])
    disc = sorted(disconnect_times or [])

    def disconnect_between(t1, t2):
        return any(t1 < d <= t2 for d in disc)

    sessions = []
    cur = None
    last_ts = None
    last_ssid = None
    for ts, net_id, ssid in samples:
        new_seg = (
            cur is None
            or ssid != last_ssid
            or (last_ts is not None and disconnect_between(last_ts, ts))
        )
        if not new_seg:
            cur.end_time = ts
        else:
            cur = ConnectionSession('wlan', ts, ssid=ssid, extra='SmartAssistant')
            cur.end_time = ts
            sessions.append(cur)
        last_ts = ts
        last_ssid = ssid
    return sessions


def extract_smart_assistant_sta(file_path, disconnect_times=None):
    """从单个 main_log 提取 SmartAssistant STA 连接段（兼容旧接口）。"""
    return build_smart_assistant_sessions(
        extract_smart_assistant_samples(file_path), disconnect_times)


def extract_smart_assistant_sta_all(main_log_paths):
    """从多个 main_log 合并采样后统一分段，避免每个文件各起一段。"""
    paths = _dedupe_paths(main_log_paths)
    all_samples = []
    all_disc = []
    for mp in paths:
        if not os.path.exists(mp):
            print(f"main_log 不存在，跳过：{mp}")
            continue
        print(f"提取连接状态：{os.path.basename(mp)}")
        all_samples.extend(extract_smart_assistant_samples(mp))
        all_disc.extend(extract_disconnect_times(mp))
    return build_smart_assistant_sessions(all_samples, all_disc)


def _dedupe_paths(paths):
    """去重 main_log/kernel 路径：先按绝对路径，再按文件名保留最短路径(避免嵌套解压重复)。"""
    seen_abs = set()
    by_base = {}
    base_order = []
    for p in paths or []:
        ap = os.path.abspath(p)
        if ap in seen_abs:
            continue
        seen_abs.add(ap)
        base = os.path.basename(p)
        if base not in by_base:
            by_base[base] = p
            base_order.append(base)
        elif len(ap) < len(os.path.abspath(by_base[base])):
            by_base[base] = p
    return [by_base[b] for b in base_order]


_DISCO_TS_RE = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')
_DISCO_RE = re.compile(
    r'wpa_supplicant.*?(\w+):\s+CTRL-EVENT-DISCONNECTED\s+bssid=[0-9a-fA-F:]+\s+reason='
)


def extract_disconnect_times(file_path):
    """提取 wpa_supplicant 在 STA(非 p2p) 接口上的真实断连时间点。

    用作 SmartAssistant 连接段的切分依据：只有发生过这些断连，连接段才分开。
    返回 list[datetime]。
    """
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    times = []
    for line in lines:
        if 'CTRL-EVENT-DISCONNECTED' not in line:
            continue
        m = _DISCO_RE.search(line)
        if not m:
            continue
        if is_p2p_iface(m.group(1)):
            continue
        tm = _DISCO_TS_RE.match(line)
        if not tm:
            continue
        ts = parse_connection_time(tm.group(1))
        if ts is not None:
            times.append(ts)
    return times


# kernel 漫游/选网日志：apsSearchBssDescByScore: Selected <mac> ... Band[..] ... when find <SSID>
_KERNEL_SELECTED_RE = re.compile(
    r'apsSearchBssDescByScore.*?Selected\s+([0-9a-fA-F:\*]{17})\s*,'
    r'.*?Band\[([^\]]+)\].*?when find\s+([^,\r\n]+)'
)
_KERNEL_STA_MAC_RE = re.compile(
    r'mtk_cfg80211_get_station:.*?mac:\[([0-9a-fA-F:\*]+)\]'
)
_MAIN_BSSID_RE = re.compile(r'BSSID=([0-9a-fA-F:\*]+)')


def format_bssid_display(bssid):
    """连接条标签用的 BSSID 展示（保留日志中的打码形式）。"""
    if not bssid:
        return ""
    return bssid.strip()


def extract_bssid_map_from_kernel(kernel_files):
    """从 kernel 选网日志提取 SSID -> (bssid, band) 映射。

    用于给 SmartAssistant 段(只有 SSID)补 BSSID——尤其是抓 log 前已建立、
    wpa_supplicant 没有关联事件的连接(如 David_5)。
    kernel 中 mac 中间字节常被隐私打码(0c:4b:**:**:**:1c)，保留打码形式即可。
    """
    mapping = {}
    for kf in kernel_files or []:
        if not kf or not os.path.exists(kf):
            continue
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                with open(kf, 'r', encoding=enc, errors='ignore') as f:
                    for line in f:
                        if 'apsSearchBssDescByScore' not in line:
                            continue
                        m = _KERNEL_SELECTED_RE.search(line)
                        if not m:
                            continue
                        bssid, band, ssid = m.group(1), m.group(2), m.group(3).strip()
                        if ssid and ssid not in mapping:
                            mapping[ssid] = (bssid, band)
                break
            except UnicodeDecodeError:
                continue
    return mapping


def extract_connected_bssid_from_kernel(kernel_files):
    """从 mtk_cfg80211_get_station 提取当前连接 AP 的 BSSID（取众数）。

    抓 log 前已建立连接、无 apsSearchBssDescByScore 选网日志时，这是主要来源。
    """
    from collections import Counter
    macs = []
    for kf in kernel_files or []:
        if not kf or not os.path.exists(kf):
            continue
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                with open(kf, 'r', encoding=enc, errors='ignore') as f:
                    for line in f:
                        if 'mtk_cfg80211_get_station' not in line:
                            continue
                        m = _KERNEL_STA_MAC_RE.search(line)
                        if m:
                            macs.append(m.group(1))
                break
            except UnicodeDecodeError:
                continue
    if not macs:
        return ""
    return Counter(macs).most_common(1)[0][0]


def extract_bssid_from_main_log(main_log_paths):
    """从 main_log 的 WifiHAL 等 BSSID= 行提取当前连接 BSSID（取众数）。"""
    from collections import Counter
    macs = []
    for mp in main_log_paths or []:
        if not mp or not os.path.exists(mp):
            continue
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                with open(mp, 'r', encoding=enc, errors='ignore') as f:
                    for line in f:
                        m = _MAIN_BSSID_RE.search(line)
                        if m:
                            macs.append(m.group(1))
                break
            except UnicodeDecodeError:
                continue
    if not macs:
        return ""
    return Counter(macs).most_common(1)[0][0]


def fill_bssid_from_kernel(sessions, kernel_files):
    """对缺少 BSSID 的 wlan 会话补全：选网日志 SSID 映射 → 连接态 station MAC。"""
    if not sessions:
        return
    mapping = extract_bssid_map_from_kernel(kernel_files)
    connected = extract_connected_bssid_from_kernel(kernel_files)
    filled_ssid = []
    filled_sta = 0
    for s in sessions.get('wlan', []):
        if s.bssid:
            continue
        if s.ssid and s.ssid in mapping:
            s.bssid = mapping[s.ssid][0]
            filled_ssid.append(s.ssid)
        elif connected:
            s.bssid = connected
            filled_sta += 1
    if filled_ssid:
        print(f"  从 kernel 选网日志补 BSSID：{', '.join(sorted(set(filled_ssid)))}")
    if filled_sta:
        print(f"  从 kernel station 日志补 BSSID：{connected}（{filled_sta} 段）")


def fill_bssid_from_main_log(sessions, main_log_paths):
    """对仍缺 BSSID 的 wlan 会话，用 main_log 中 WifiHAL BSSID= 补全。"""
    if not sessions:
        return
    connected = extract_bssid_from_main_log(main_log_paths)
    if not connected:
        return
    filled = 0
    for s in sessions.get('wlan', []):
        if not s.bssid:
            s.bssid = connected
            filled += 1
    if filled:
        print(f"  从 main_log 补 BSSID：{connected}（{filled} 段）")


def extract_current_channel_from_kernel(kernel_files):
    """从 kernel ScanDone 推断 STA 当前连接信道。

    MTK 在 STA 已连接时会周期性对【当前连接信道】做单信道定向扫描，
    对应 scnFsmDumpScanDoneInfo 的 `Detected_Channel_Num = 1` + `Channel: <ch>`。
    取这些单信道扫描信道的众数作为当前连接信道，返回 "2.4G chN"/"5G chN" 或 ""。
    """
    from collections import Counter
    singles = []
    for kf in kernel_files or []:
        if not kf or not os.path.exists(kf):
            continue
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                with open(kf, 'r', encoding=enc, errors='ignore') as f:
                    pending = False
                    for line in f:
                        if 'scnFsmDumpScanDoneInfo' not in line:
                            continue
                        if 'Detected_Channel_Num = 1' in line:
                            pending = True
                        elif pending and 'Channel  :' in line:
                            nums = re.findall(
                                r'\b\d+\b', line.split('Channel  :', 1)[1])
                            if nums:
                                singles.append(int(nums[0]))
                            pending = False
                break
            except UnicodeDecodeError:
                continue
    if not singles:
        return ""
    ch = Counter(singles).most_common(1)[0][0]
    if ch <= 14:
        return f"2.4G ch{ch}"
    if ch <= 196:
        return f"5G ch{ch}"
    return f"ch{ch}"


def fill_channel_from_kernel(sessions, kernel_files):
    """对缺少 freq/channel 的 wlan 会话，用 kernel 推断的当前连接信道补全。"""
    if not sessions:
        return
    ch = extract_current_channel_from_kernel(kernel_files)
    if not ch:
        return
    filled = False
    for s in sessions.get('wlan', []):
        if not s.freq and not s.channel_override:
            s.channel_override = ch
            filled = True
    if filled:
        print(f"  从 kernel 单信道扫描推断当前连接信道：{ch}")


# 连接失败事件：关联被拒 / 认证被拒 / 4-way 握手失败 / 网络被临时禁用
_FAIL_PATTERNS = [
    ('ASSOC-REJECT', re.compile(r'CTRL-EVENT-ASSOC-REJECT.*?status_code=(\d+)')),
    ('AUTH-REJECT', re.compile(r'CTRL-EVENT-AUTH-REJECT.*?status_code=(\d+)')),
    ('4WAY-FAIL', re.compile(r'4-Way Handshake failed')),
    ('SSID-DISABLED', re.compile(r'CTRL-EVENT-SSID-TEMP-DISABLED')),
]
_FAIL_TS_RE = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')


def extract_fail_events(file_path):
    """从 main_log 提取连接失败事件，返回 list[dict(ts, kind, status)]。"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    events = []
    for line in lines:
        if 'wpa_supplicant' not in line:
            continue
        tm = _FAIL_TS_RE.match(line)
        if not tm:
            continue
        for kind, rx in _FAIL_PATTERNS:
            m = rx.search(line)
            if m:
                ts = parse_connection_time(tm.group(1))
                if ts is None:
                    break
                status = m.group(1) if m.groups() else ''
                events.append({'ts': ts, 'kind': kind, 'status': status})
                break
    return events


def load_fail_events(main_log_paths):
    """提取并合并多个 main_log 的连接失败事件。"""
    events = []
    for mp in main_log_paths or []:
        if os.path.exists(mp):
            events.extend(extract_fail_events(mp))
    events.sort(key=lambda e: e['ts'])
    if events:
        kinds = {}
        for e in events:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
        desc = ', '.join(f"{k}×{v}" for k, v in kinds.items())
        print(f"连接失败事件：{len(events)} 次 ({desc})")
    return events


def load_connection_sessions(main_log_paths):
    """提取并合并多个 main_log 的连接会话，返回 dict 或 None。

    WLAN(STA) 优先采用 TranWifiSmartAssistantController 的准确连接段(带真实 SSID)；
    wpa_supplicant 的 wlan 会话仅保留与之不重叠的部分(如失败的关联尝试)。
    """
    sess_list = []
    main_log_paths = _dedupe_paths(main_log_paths)
    for mp in main_log_paths:
        if not os.path.exists(mp):
            print(f"main_log 不存在，跳过：{mp}")
            continue
        sess_list.append(extract_connection_sessions(mp))
    if not sess_list:
        return None
    merged = merge_connection_sessions(sess_list)

    sa_sessions = extract_smart_assistant_sta_all(main_log_paths)
    if sa_sessions:
        sa_sessions.sort(key=lambda s: s.start_time)
        # SmartAssistant 只有 SSID，用与之重叠的 wpa 会话补 BSSID/信道(freq)
        for sa in sa_sessions:
            for w in merged['wlan']:
                if _sessions_overlap(w, sa) and (not w.ssid or w.ssid == sa.ssid):
                    if not sa.bssid and w.bssid:
                        sa.bssid = w.bssid
                    if not sa.freq and w.freq:
                        sa.freq = w.freq
                    if sa.bssid and sa.freq:
                        break
        # 保留与 SmartAssistant 段不重叠的 wpa wlan 会话
        kept_wpa = [w for w in merged['wlan']
                    if not any(_sessions_overlap(w, s) for s in sa_sessions)]
        merged['wlan'] = sorted(sa_sessions + kept_wpa, key=lambda s: s.start_time)
        print(f"  STA(SmartAssistant) 连接段：{len(sa_sessions)} 段 "
              f"(SSID: {', '.join(sorted({s.ssid for s in sa_sessions}))})")

    total = sum(len(merged[k]) for k in merged)
    print(f"连接会话：wlan={len(merged['wlan'])} "
          f"p2p={len(merged['p2p'])} softap={len(merged['softap'])}")
    return merged if total else None


def _session_label_lines(s):
    """把一次会话拆成多行文本：SSID / 信道·mac·角色 / reason，避免挤在一行重叠。"""
    line1 = s.ssid or '(unknown)'
    parts = []
    if s.channel:
        parts.append(s.channel)
    if s.bssid:
        parts.append(format_bssid_display(s.bssid))
    if s.role:
        parts.append(s.role)
    lines = [line1]
    if parts:
        lines.append(' · '.join(parts))
    if s.end_reason and s.end_reason != '(open)':
        lines.append(s.end_reason)
    return lines


def _stagger_levels(mids, total_span, min_gap_frac=0.055, max_levels=8):
    """按时间邻近度为标签分配竖向层级：x 太近的会话放到不同层级以免重叠。

    mids: 各标签锚点(datetime)；total_span: 轴总时长(秒)。返回与 mids 等长的层级列表。
    """
    n = len(mids)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: mids[i])
    gap = (total_span * min_gap_frac) if total_span else 0
    levels = [0] * n
    last_at = {}  # level -> 该层最后一个标签的 mid
    for i in order:
        chosen = None
        for lvl in range(max_levels):
            lt = last_at.get(lvl)
            if lt is None or (mids[i] - lt).total_seconds() >= gap:
                chosen = lvl
                break
        if chosen is None:
            chosen = min(last_at, key=lambda l: last_at[l])
        levels[i] = chosen
        last_at[chosen] = mids[i]
    return levels


def draw_connection_panel(ax, sessions, x_start, x_end):
    """在给定 ax 上绘制连接状态时间线（wlan/p2p/softap 分行）。

    sessions 中各会话的时间为 main_log 本地时间；调用前应确保 kernel 数据已
    平移到同一(本地)时间基准，使本面板与 RSSI 等子图共享同一 X 轴。

    标签布局：SSID 与 mac/信道/角色/reason 分多行显示；时间上过于接近的会话
    标签自动错开到不同竖向层级，并用细引导线连回对应连接条，避免文字重叠。
    """
    iface_order = [i for i in ('wlan', 'p2p', 'softap') if sessions and sessions.get(i)]
    if not iface_order:
        ax.text(0.5, 0.5, 'No connection events', ha='center', va='center',
                transform=ax.transAxes, fontsize=11, color='#666')
        ax.set_ylabel('Connection', fontsize=12)
        ax.set_title('Connection Status (from main_log)', fontsize=13, fontweight='bold')
        return

    iface_label = {'wlan': 'WLAN', 'p2p': 'P2P', 'softap': 'SoftAP'}
    # 行间留出足够竖向空间给堆叠标签
    row_gap = 3.0
    y_of = {iface: 1.0 + (len(iface_order) - 1 - idx) * row_gap
            for idx, iface in enumerate(iface_order)}

    # 每一次连接(会话)分配独立颜色：按起始时间在所有链路间统一排序后依次取色
    all_sessions = [s for iface in iface_order for s in sessions[iface]
                    if s.start_time is not None]
    all_sessions.sort(key=lambda s: s.start_time)
    color_map = {id(s): CONNECTION_COLORS[i % len(CONNECTION_COLORS)]
                 for i, s in enumerate(all_sessions)}

    def color_for(s):
        return color_map.get(id(s), CONNECTION_COLORS[0])

    total_span = None
    if x_start is not None and x_end is not None and x_end > x_start:
        total_span = (x_end - x_start).total_seconds()

    level_step_pts = 30  # 每个竖向层级的额外像素偏移
    base_off_pts = 10

    for iface in iface_order:
        y = y_of[iface]
        # 收集可视范围内的会话
        visible = []
        for s in sessions[iface]:
            st = s.start_time
            en = s.end_time or s.start_time
            if st is None:
                continue
            if x_start is not None and en < x_start:
                continue
            if x_end is not None and st > x_end:
                continue
            st_c = max(st, x_start) if x_start is not None else st
            en_c = min(en, x_end) if x_end is not None else en
            if en_c < st_c:
                en_c = st_c
            mid = st_c + (en_c - st_c) / 2
            visible.append((s, st_c, en_c, mid))

        if not visible:
            continue

        levels = _stagger_levels([v[3] for v in visible], total_span)

        for (s, st_c, en_c, mid), lvl in zip(visible, levels):
            color = color_for(s)
            # 连接条
            ax.plot([st_c, en_c], [y, y], color=color, lw=6,
                    solid_capstyle='butt', zorder=4)
            lines = _session_label_lines(s)
            off = base_off_pts + lvl * level_step_pts
            # 细引导线：从连接条指向其标签层级
            ax.annotate('', xy=(mid, y), xytext=(0, off),
                        textcoords='offset points',
                        arrowprops=dict(arrowstyle='-', color=color,
                                        lw=0.6, alpha=0.5), zorder=2)
            ax.annotate('\n'.join(lines), (mid, y), xytext=(0, off),
                        textcoords='offset points', ha='center', va='bottom',
                        fontsize=7.5, color=color, linespacing=1.2, zorder=5)

    max_level = 0
    for iface in iface_order:
        mids = []
        for s in sessions[iface]:
            st = s.start_time
            en = s.end_time or s.start_time
            if st is None:
                continue
            if x_start is not None and en < x_start:
                continue
            if x_end is not None and st > x_end:
                continue
            st_c = max(st, x_start) if x_start is not None else st
            en_c = min(en, x_end) if x_end is not None else en
            mids.append(st_c + (max(en_c, st_c) - st_c) / 2)
        if mids:
            max_level = max(max_level, max(_stagger_levels(mids, total_span)))

    top = max(y_of.values()) + 1.0 + max_level * 1.1
    ax.set_ylim(0.2, top)
    ax.set_yticks([y_of[i] for i in iface_order])
    ax.set_yticklabels([iface_label[i] for i in iface_order],
                       fontsize=10, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_title('Connection Status (from main_log)', fontsize=13, fontweight='bold')


# ==================== 扫描事件提取（scnFsmDumpScanDoneInfo / Scan UEvent） ====================

# 每次扫描上报的结果数：Total:报告数/缓存数
_SCAN_TOTAL_RE = re.compile(r'Total:(\d+)/(\d+)')
# 部分平台的 Scan Done 概要：used[N] = 发现的 BSS 数
_SCAN_USED_RE = re.compile(r'used\[(\d+)\]')
# Scan UEvent：含本次扫描的信道列表
_SCAN_UEVENT_RE = re.compile(r'Send UEvent:\s*Scan=Status:(\w+),.*?Channel:([0-9 ]+?)\s*,Reason')
# 完成信道数
_SCAN_CHANCNT_RE = re.compile(r'ucCompleteChanCount\[(\d+)\]')


def _scan_parse_ts(line):
    ts = line[:19].strip()
    if len(ts) < 15:
        return None
    try:
        return datetime.strptime(ts, '%m-%d %H:%M:%S.%f').replace(year=2026)
    except ValueError:
        return None


def extract_scan_events(file_path):
    """从 kernel log 提取每次扫描的「结果个数」与「信道」。

    返回 list[dict]，每项含：
      ts        扫描完成时间(kernel 原始 UTC，未平移)
      n_result  上报的 AP 数(Total 的分子；无 Total 时取 used[N])
      n_cache   缓存 AP 数(Total 的分母；可为 None)
      n_chan    本次扫描信道数
      channels  信道列表(可为空)
    结果按时间排序。结果锚点(result)与信道信息(channel)分别采集后按时间就近配对。
    """
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    if not lines:
        return []

    results = []    # (ts, n_result, n_cache)
    chan_info = []  # (ts, n_chan, channels)
    for line in lines:
        tm = _SCAN_TOTAL_RE.search(line)
        if tm and ('SCN' in line or 'scan' in line.lower() or 'BSS' in line):
            ts = _scan_parse_ts(line)
            if ts:
                results.append((ts, int(tm.group(1)), int(tm.group(2))))
                continue
        um = _SCAN_UEVENT_RE.search(line)
        if um:
            ts = _scan_parse_ts(line)
            if ts:
                chans = [c for c in um.group(2).split() if c]
                chan_info.append((ts, len(chans), chans))
                continue
        cm = _SCAN_CHANCNT_RE.search(line)
        if cm:
            ts = _scan_parse_ts(line)
            if ts:
                chan_info.append((ts, int(cm.group(1)), []))
                continue

    # 无 Total 行的平台：退回用 used[N] 作为结果数
    if not results:
        for line in lines:
            um = _SCAN_USED_RE.search(line)
            if um and 'ScanDone' in line:
                ts = _scan_parse_ts(line)
                if ts:
                    results.append((ts, int(um.group(1)), None))

    events = []
    for ts, n_res, n_cache in results:
        n_chan, channels, best = 0, [], None
        for cts, cnt, chans in chan_info:
            d = abs((cts - ts).total_seconds())
            if d <= 5.0 and (best is None or d < best):
                best, n_chan, channels = d, cnt, chans
        events.append({'ts': ts, 'n_result': n_res, 'n_cache': n_cache,
                       'n_chan': n_chan, 'channels': channels})
    events.sort(key=lambda e: e['ts'])
    return events


def shift_scan_events(events, offset_hours):
    """把扫描事件时间平移 offset_hours 小时（对齐到设备本地时间）。"""
    if not offset_hours or not events:
        return events
    delta = timedelta(hours=offset_hours)
    for e in events:
        e['ts'] = e['ts'] + delta
    return events


def _segments_from_times(times, gap_sec=60.0):
    """把一串时间戳按相邻间隔聚成连续区间(间隔 > gap_sec 视为断开)。返回 [(start, end)]。"""
    if not times:
        return []
    ts = sorted(times)
    segs = []
    seg_start = prev = ts[0]
    for t in ts[1:]:
        if (t - prev).total_seconds() > gap_sec:
            segs.append((seg_start, prev))
            seg_start = t
        prev = t
    segs.append((seg_start, prev))
    return segs


def draw_scan_and_connection_on_rssi(ax, sessions, scan_events, x_start, x_end,
                                     has_rssi, rssi_times=None, fail_events=None):
    """在 RSSI 子图上叠加：连接状态条(上方) + 扫描事件标记(竖线 + 信道/结果数)。

    连接条用 blended transform 放在子图顶部区域(不占用 RSSI 数值刻度)；
    扫描事件用竖直虚线标在时间点，并在底部标注「信道数 / 结果个数」。

    STA(WLAN) 连接条来自 main_log 真实会话(wpa / SmartAssistant)。
    仅当无任何会话且无连接失败事件时，才用 RSSI 整段作兜底标注；
    有会话或失败事件时，会话间隙视为断开，不再用 RSSI 推断补段。
    """
    trans = ax.get_xaxis_transform()  # x=data, y=axes fraction

    # 给 RSSI 数据上方腾出空间放连接条
    if has_rssi:
        y0, y1 = ax.get_ylim()
        ax.set_ylim(y0, y1 + (y1 - y0) * 0.7)

    # ---- 扫描事件：竖直虚线 + 底部「ch/结果」标注 ----
    if scan_events:
        vis = [e for e in scan_events
               if (x_start is None or e['ts'] >= x_start)
               and (x_end is None or e['ts'] <= x_end)]
        vis.sort(key=lambda e: e['ts'])
        for idx, e in enumerate(vis):
            xnum = mdates.date2num(e['ts'])
            ax.axvline(xnum, color='#7f7f7f', lw=0.8, ls=':', alpha=0.55,
                       zorder=1)
            res = e['n_result']
            ch = e['n_chan']
            txt = f"{ch}ch\n{res}AP" if ch else f"{res}AP"
            # 密集扫描标签三级交替错行，避免底部文字重叠
            level = idx % 3
            ax.annotate(txt, (xnum, 0.0), xycoords=trans,
                        xytext=(0, 3 + level * 16), textcoords='offset points',
                        ha='center', va='bottom', fontsize=6.8, color='#444',
                        zorder=6)

    # ---- 连接失败事件：红色 ✕ 竖线(关联/认证被拒、握手失败等) ----
    if fail_events:
        vis_f = [e for e in fail_events
                 if (x_start is None or e['ts'] >= x_start)
                 and (x_end is None or e['ts'] <= x_end)]
        vis_f.sort(key=lambda e: e['ts'])
        if x_start is not None and x_end is not None and x_end > x_start:
            f_xspan = mdates.date2num(x_end) - mdates.date2num(x_start)
        else:
            f_xspan = 0
        f_gap = f_xspan * 0.05 if f_xspan else 0
        f_last_x = {}  # level -> 最后一个标签 x，距离过近则上移一层
        labeled = False
        for e in vis_f:
            xnum = mdates.date2num(e['ts'])
            ax.axvline(xnum, color='#d62728', lw=1.0, ls='-', alpha=0.5, zorder=4)
            ax.plot([xnum], [0.5], transform=trans, marker='x', color='#d62728',
                    markersize=8, markeredgewidth=2, zorder=9,
                    label=('连接失败' if not labeled else None), clip_on=True)
            labeled = True
            tag = e['kind'].replace('CTRL-EVENT-', '')
            if e.get('status'):
                tag += f"({e['status']})"
            level = 0
            while True:
                lx = f_last_x.get(level)
                if lx is None or (xnum - lx) >= f_gap:
                    break
                level += 1
                if level > 8:
                    break
            f_last_x[level] = xnum
            ax.annotate(tag, (xnum, 0.5), xycoords=trans,
                        xytext=(0, 6 + level * 11), textcoords='offset points',
                        ha='center', va='bottom', fontsize=6.2,
                        color='#d62728', fontweight='bold', zorder=9)

    # ---- 连接状态条：顶部区域，按链路分行 ----
    sessions = sessions or {'wlan': [], 'p2p': [], 'softap': []}
    rssi_segments = _segments_from_times(rssi_times or [])

    # 决定要显示哪些链路行：有会话的链路；WLAN 行只要有 RSSI 区间也显示
    iface_order = []
    if sessions.get('wlan') or rssi_segments:
        iface_order.append('wlan')
    for it in ('p2p', 'softap'):
        if sessions.get(it):
            iface_order.append(it)
    if not iface_order:
        return

    iface_label = {'wlan': 'WLAN', 'p2p': 'P2P', 'softap': 'SoftAP'}
    top_base, step = 0.95, 0.085
    yfrac = {it: top_base - idx * step for idx, it in enumerate(iface_order)}

    all_sessions = [s for it in ('wlan', 'p2p', 'softap')
                    for s in sessions.get(it, []) if s.start_time is not None]
    all_sessions.sort(key=lambda s: s.start_time)
    cmap = {id(s): CONNECTION_COLORS[i % len(CONNECTION_COLORS)]
            for i, s in enumerate(all_sessions)}

    # 用于标签错行的总时间跨度(数值)
    if x_start is not None and x_end is not None and x_end > x_start:
        total_xspan = mdates.date2num(x_end) - mdates.date2num(x_start)
    else:
        total_xspan = 0

    def clip(st, en):
        st_c = max(st, x_start) if x_start is not None else st
        en_c = min(en, x_end) if x_end is not None else en
        return st_c, max(en_c, st_c)

    def in_window(st, en):
        if x_start is not None and en < x_start:
            return False
        if x_end is not None and st > x_end:
            return False
        return True

    def draw_bars_with_labels(yf, bars):
        """bars: list of (st, en, color, label)。画连接条，并把 x 相近的标签竖向错行。"""
        specs = []  # (midn, label, color)
        for st, en, color, label in bars:
            st_c, en_c = clip(st, en)
            x0n, x1n = mdates.date2num(st_c), mdates.date2num(en_c)
            # 与其它子图一致的线形：细线 + 圆点 marker(标出连接起止)
            ax.plot([x0n, x1n], [yf, yf], transform=trans, color=color,
                    lw=1.6, marker='o', markersize=5, markevery=[0, 1],
                    solid_capstyle='round', zorder=7, clip_on=True)
            if label:
                specs.append((x0n + (x1n - x0n) / 2, label, color))
        # 按 x 排序后分配层级：与上一同层标签间距过近则换层
        specs.sort(key=lambda s: s[0])
        gap = total_xspan * 0.07 if total_xspan else 0
        last_x_at = {}  # level -> 最后一个标签的 x
        for midn, label, color in specs:
            level = 0
            while True:
                lx = last_x_at.get(level)
                if lx is None or (midn - lx) >= gap:
                    break
                level += 1
                if level > 6:
                    break
            last_x_at[level] = midn
            ax.annotate(label, (midn, yf), xycoords=trans,
                        xytext=(0, 4 + level * 11), textcoords='offset points',
                        ha='center', va='bottom', fontsize=6.8,
                        color=color, zorder=8)

    # 行标签
    for it in iface_order:
        ax.annotate(iface_label[it], (0.0, yfrac[it]), xycoords='axes fraction',
                    xytext=(2, 0), textcoords='offset points',
                    ha='left', va='center', fontsize=7.5,
                    color='#333', fontweight='bold', alpha=0.7)

    # ---- WLAN 行：仅绘制真实会话；断开间隙不再用 RSSI 推断补段 ----
    yf_wlan = yfrac.get('wlan')
    if yf_wlan is not None:
        wlan_sessions = [s for s in sessions.get('wlan', [])
                         if s.start_time is not None]

        wlan_bars = []
        for s in wlan_sessions:
            st, en = s.start_time, s.end_time or s.start_time
            if not in_window(st, en):
                continue
            wlan_bars.append((st, en, cmap.get(id(s), CONNECTION_COLORS[0]), s.label()))

        if not wlan_sessions:
            # 无任何会话 + 有 RSSI：整段兜底(抓 log 前已连上，wpa/SmartAssistant 均无记录)
            if rssi_segments:
                for seg_st, seg_en in rssi_segments:
                    if not in_window(seg_st, seg_en):
                        continue
                    if (seg_en - seg_st).total_seconds() < 1:
                        continue
                    wlan_bars.append((seg_st, seg_en, '#999999', 'STA connected (RSSI)'))
        elif rssi_segments:
            # 有会话时：断连间隙不补；但「第一个会话之前」的 RSSI 前导段例外——
            # 它代表抓 log 前已建立、无起始关联过程的连接，补一条并沿用首个会话 SSID。
            first_start = min(s.start_time for s in wlan_sessions)
            first_ssid = min(wlan_sessions, key=lambda s: s.start_time).ssid
            lead_label = (first_ssid or 'STA') + ' (RSSI)'
            for seg_st, seg_en in rssi_segments:
                lead_en = min(seg_en, first_start)
                if (lead_en - seg_st).total_seconds() < 1:
                    continue
                if not in_window(seg_st, lead_en):
                    continue
                wlan_bars.append((seg_st, lead_en, '#999999', lead_label))

        draw_bars_with_labels(yf_wlan, wlan_bars)

    # ---- P2P / SoftAP 行：直接来自 main_log 会话 ----
    for it in ('p2p', 'softap'):
        yf = yfrac.get(it)
        if yf is None:
            continue
        bars = []
        for s in sessions.get(it, []):
            st, en = s.start_time, s.end_time or s.start_time
            if st is None or not in_window(st, en):
                continue
            bars.append((st, en, cmap.get(id(s), CONNECTION_COLORS[0]), s.label()))
        draw_bars_with_labels(yf, bars)


def build_session_color_map(sessions):
    """按起始时间排序生成会话→颜色映射，与 RSSI 子图连接条配色一致。"""
    all_sessions = [s for it in ('wlan', 'p2p', 'softap')
                    for s in (sessions or {}).get(it, []) if s.start_time is not None]
    all_sessions.sort(key=lambda s: s.start_time)
    cmap = {id(s): CONNECTION_COLORS[i % len(CONNECTION_COLORS)]
            for i, s in enumerate(all_sessions)}
    return all_sessions, cmap


def draw_connection_spans_across(axes, sessions, x_start, x_end):
    """用各连接段自身颜色的竖虚线，从最上子图到最下子图连续贯穿(跨越子图间空隙)，
    标出连接段起止，便于跨子图对应同一段连接的各项指标。"""
    all_sessions, cmap = build_session_color_map(sessions)
    if not all_sessions or not axes:
        return
    from matplotlib.patches import ConnectionPatch
    fig = axes[0].figure
    ax_top, ax_bot = axes[0], axes[-1]
    for s in all_sessions:
        st = s.start_time
        en = s.end_time or s.start_time
        if x_start is not None and en < x_start:
            continue
        if x_end is not None and st > x_end:
            continue
        st_c = max(st, x_start) if x_start is not None else st
        en_c = min(en, x_end) if x_end is not None else en
        color = cmap[id(s)]
        x0n, x1n = mdates.date2num(st_c), mdates.date2num(en_c)
        marks = [(x0n, '--', 0.5)]
        if x1n > x0n:
            marks.append((x1n, ':', 0.38))
        for xn, style, alpha in marks:
            con = ConnectionPatch(
                xyA=(xn, 1.0), coordsA=ax_top.get_xaxis_transform(),
                xyB=(xn, 0.0), coordsB=ax_bot.get_xaxis_transform(),
                color=color, ls=style, lw=0.8, alpha=alpha, zorder=0.5)
            con.set_clip_on(False)
            fig.add_artist(con)


# ==================== 原有 Link Quality 提取 ====================

def extract_data(file_path):
    """
    从 kernel log 提取 Tput/Tx/Rx/rssi/PER 数据。
    时间提取：每行前19字符（格式：MM-DD HH:MM:SS.mmm）
    rssi 优先级（仅 mtk_cfg80211_get_station 行）：
      MovAvg_rssi= → Raw_rssi BSSDesc 首值
    不使用 mtk_cfg80211_vendor_event_rssi_beyond_range 的 , rssi=（稀疏阈值事件，与连续 RSSI 对不上）
    """
    data = {
        "Tput:": ([], []),
        "Tx(rate:": ([], []),
        "Rx(rate:": ([], []),
        ", rssi=": ([], []),
        "PER": ([], [])
    }
    all_valid_times = []

    rssi_keywords = [
        ("MovAvg_rssi=", re.compile(r'MovAvg_rssi=(-?\d+\.?\d*)[,)]')),
        ("Raw_rssi BSSDesc", re.compile(r'Raw_rssi=\[BSSDesc\((-?\d+\.?\d*)')),
    ]
    other_pattern_map = {
        "Tput:": re.compile(r'Tput:\s*(\d+\.?\d*)'),
        "Tx(rate:": re.compile(r'Tx\(rate:\s*(\d+\.?\d*)'),
        "Rx(rate:": re.compile(r'Rx\(rate:\s*(\d+\.?\d*)'),
        "PER": re.compile(r'PER\((\d+\.?\d*)\)')
    }

    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    if not lines:
        print(f"无法解码文件：{file_path}")
        return None, None

    # 提取 Tput/Tx/Rx/PER
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        time_str = line[:19].strip()
        if len(time_str) < 15:
            continue
        try:
            time_obj = datetime.strptime(time_str, '%m-%d %H:%M:%S.%f')
            time_obj = time_obj.replace(year=2026)
        except ValueError:
            continue

        for keyword, pattern in other_pattern_map.items():
            match = pattern.search(line)
            if match:
                try:
                    num = float(match.group(1))
                    data[keyword][0].append(time_obj)
                    data[keyword][1].append(num)
                    if time_obj not in all_valid_times:
                        all_valid_times.append(time_obj)
                except ValueError:
                    continue

    # RSSI：仅从 mtk_cfg80211_get_station 周期采样提取（与 Tx/Rx/PER 同源链路）
    used_keyword = None
    for keyword, pattern in rssi_keywords:
        current_times, current_nums = [], []
        for line in lines:
            line_strip = line.strip()
            if not line_strip or 'mtk_cfg80211_get_station' not in line:
                continue
            time_str = line[:19].strip()
            if len(time_str) < 15:
                continue
            try:
                time_obj = datetime.strptime(time_str, '%m-%d %H:%M:%S.%f')
                time_obj = time_obj.replace(year=2026)
            except ValueError:
                continue
            match = pattern.search(line)
            if match:
                try:
                    num = float(match.group(1))
                    current_times.append(time_obj)
                    current_nums.append(num)
                    if time_obj not in all_valid_times:
                        all_valid_times.append(time_obj)
                except ValueError:
                    continue
        if current_nums:
            data[", rssi="] = (current_times, current_nums)
            used_keyword = keyword
            break

    # 排序
    for keyword in data:
        times, nums = data[keyword]
        if times and nums:
            sorted_pairs = sorted(zip(times, nums), key=lambda x: x[0])
            data[keyword] = ([p[0] for p in sorted_pairs], [p[1] for p in sorted_pairs])

    # 统计
    print("\n数据提取统计：")
    for keyword, (times, nums) in data.items():
        key = "rssi" if keyword == ", rssi=" else keyword
        if nums:
            note = f"（关键字：{used_keyword}）" if keyword == ", rssi=" and used_keyword else ""
            print(f"  {key}：{len(nums)}条 | 范围：{min(nums):.0f}~{max(nums):.0f}{note}")
        else:
            print(f"  {key}：0条有效数据")

    if all_valid_times:
        start = min(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        end = max(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        print(f"时间区间：{start} ~ {end}")

    return data, all_valid_times


def format_x_time(x, pos):
    """将 matplotlib float64 时间戳转回 datetime 并格式化"""
    try:
        time_obj = mdates.num2date(x)
        return time_obj.strftime('%m-%d %H:%M:%S.%f')[:-3]
    except Exception:
        return ""


def _session_overlaps_range(session, range_start, range_end, pad=timedelta(seconds=30)):
    """会话是否与给定时间窗有重叠(忽略与 kernel 数据窗无关的旧会话)。"""
    if session.start_time is None:
        return False
    st = session.start_time
    en = session.end_time or session.start_time
    return (st - pad) <= range_end and (range_start - pad) <= en


def compute_plot_x_bounds(all_valid_times, connection_sessions, data):
    """计算绘图 X 轴起止。

    起点取「真实链路活动」的最早时刻，**不含 Tput**——Tput 在无 STA 连接时
    仍会周期性统计，不能作为有效连接信号。
    候选：与 kernel 数据窗重叠的连接会话起点、RSSI/Tx/Rx/PER 首点。
    """
    data_left, data_right = min(all_valid_times), max(all_valid_times)
    activity_cands = []

    if connection_sessions:
        for it in ('wlan', 'p2p', 'softap'):
            for s in connection_sessions.get(it, []) or []:
                if _session_overlaps_range(s, data_left, data_right):
                    activity_cands.append(s.start_time)

    for key in (", rssi=", "Tx(rate:", "Rx(rate:", "PER"):
        times = data.get(key, ([], []))[0]
        if times:
            activity_cands.append(min(times))

    plot_x_right = data_right
    if not activity_cands:
        return data_left, plot_x_right, None, False

    activity_start = min(activity_cands)
    if activity_start > data_left:
        span = (data_right - activity_start).total_seconds()
        margin = timedelta(seconds=max(span * 0.01, 1))
        plot_x_left = max(data_left, activity_start - margin)
        trimmed = plot_x_left > data_left
    else:
        plot_x_left = data_left
        trimmed = False
    return plot_x_left, plot_x_right, activity_start, trimmed


def plot_quadruple(data, all_valid_times, source_file_path, output_dir=None,
                   save_filename="kernel_log_curves.png", connection_sessions=None,
                   scan_events=None, fail_events=None):
    """
    绘制子图：Tput → Tx/Rx → RSSI(+连接状态+扫描事件+失败标记) → PER
    - connection_sessions：在 RSSI 子图顶部叠加连接状态条(每次连接不同颜色)。
    - scan_events：在 RSSI 子图标记每次扫描(竖虚线 + 信道数/结果个数)。
    - fail_events：在 RSSI 子图标记连接失败(关联/认证被拒、握手失败)，红色 ✕。
    保存到 source_file_path 同目录或 output_dir 指定目录
    """
    tput_times, tput_nums = data["Tput:"]
    tx_times, tx_nums = data["Tx(rate:"]
    rx_times, rx_nums = data["Rx(rate:"]
    rssi_times, rssi_nums = data[", rssi="]
    per_times, per_nums = data["PER"]

    has_tput = len(tput_times) > 0
    has_tx_rx = len(tx_times) > 0 or len(rx_times) > 0
    has_rssi = len(rssi_times) > 0
    has_per = len(per_times) > 0
    has_time = len(all_valid_times) > 0

    if not has_tput and not has_tx_rx and not has_rssi and not has_per:
        print("无有效数据，跳过绘图")
        return None

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['axes.titlepad'] = 12

    # 子图布局：Tput → Tx/Rx → RSSI(叠加连接状态+扫描事件) → PER
    has_conn = bool(connection_sessions) and any(
        connection_sessions.get(k) for k in ('wlan', 'p2p', 'softap'))
    has_scan = bool(scan_events)
    has_fail = bool(fail_events)
    has_conn_overlay = has_conn or has_rssi
    has_overlay = has_conn_overlay or has_scan or has_fail
    panel_order = ['tput', 'txrx', 'rssi', 'per']
    n_plots = len(panel_order)
    # RSSI 子图叠加了连接/扫描信息，给更高行高
    height_ratios = [1.6 if p == 'rssi' and has_overlay else 1.0
                     for p in panel_order]
    fig_height = 3.2 * sum(height_ratios)
    fig, axes = plt.subplots(n_plots, 1, figsize=(18, fig_height), sharex=True,
                             gridspec_kw={'height_ratios': height_ratios})
    if n_plots == 1:
        axes = [axes]
    ax_map = {name: axes[idx] for idx, name in enumerate(panel_order)}
    ax1, ax2, ax3, ax4 = ax_map['tput'], ax_map['txrx'], ax_map['rssi'], ax_map['per']
    plt.subplots_adjust(hspace=0.28, top=0.93, bottom=0.12)

    # 绘图起点：取真实链路活动(RSSI/Tx/Rx/PER/有效连接)的最早时刻；
    # 不含 Tput——无连接时 Tput 仍会统计，会造成前段大片空白。
    plot_x_left = plot_x_right = None
    activity_start = None
    trimmed = False
    if has_time:
        plot_x_left, plot_x_right, activity_start, trimmed = compute_plot_x_bounds(
            all_valid_times, connection_sessions, data)

    if has_time:
        start = plot_x_left.strftime('%m-%d %H:%M:%S.%f')[:-3]
        end = plot_x_right.strftime('%m-%d %H:%M:%S.%f')[:-3]
        trimmed_note = '（已从首个有效链路活动起绘制）' if trimmed else ''
        fig.suptitle(f'WiFi Link Quality（{start} ~ {end}）{trimmed_note}',
                     fontsize=16, fontweight='bold', y=0.98)
    else:
        fig.suptitle('WiFi Link Quality', fontsize=16, fontweight='bold', y=0.98)

    # Tput
    if has_tput:
        ax1.plot(tput_times, tput_nums, color='#1f77b4', marker='o', markersize=4, linewidth=1.2, label='Tput')
        ax1.set_ylim(0, max(tput_nums) * 1.1)
        ax1.set_ylabel('Tput (Mbps)', fontsize=12, color='#1f77b4')
        ax1.tick_params(axis='y', labelcolor='#1f77b4')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(loc='upper right', fontsize=10)
        ax1.set_title('Throughput', fontsize=13, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'No Tput data', ha='center', va='center', transform=ax1.transAxes, fontsize=12, color='#666')
        ax1.set_ylabel('Tput (Mbps)', fontsize=12, color='#1f77b4')

    # Tx/Rx
    if has_tx_rx:
        if tx_nums:
            ax2.plot(tx_times, tx_nums, color='#ff7f0e', marker='s', markersize=4, linewidth=1.2, label='Tx(rate)')
        if rx_nums:
            ax2.plot(rx_times, rx_nums, color='#2ca02c', marker='^', markersize=4, linewidth=1.2, label='Rx(rate)')
        max_val = max(max(tx_nums) if tx_nums else 0, max(rx_nums) if rx_nums else 0)
        ax2.set_ylim(0, max_val * 1.1)
        ax2.set_ylabel('PHY Rate (Mbps)', fontsize=12, color='#ff7f0e')
        ax2.tick_params(axis='y', labelcolor='#ff7f0e')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.legend(loc='upper right', fontsize=10)
        ax2.set_title('Tx/Rx PHY Rate', fontsize=13, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'No Tx/Rx data', ha='center', va='center', transform=ax2.transAxes, fontsize=12, color='#666')
        ax2.set_ylabel('PHY Rate (Mbps)', fontsize=12, color='#ff7f0e')

    # rssi
    if has_rssi:
        ax3.plot(rssi_times, rssi_nums, color='#d62728', marker='*', markersize=4, linewidth=1.2, label='RSSI')
        rssi_min, rssi_max = min(rssi_nums), max(rssi_nums)
        y_margin = max(abs(rssi_min) * 0.1, abs(rssi_max) * 0.1, 5)
        ax3.set_ylim(rssi_min - y_margin, rssi_max + y_margin)
        ax3.set_ylabel('RSSI (dBm)', fontsize=12, color='#d62728')
        ax3.tick_params(axis='y', labelcolor='#d62728')
        ax3.grid(True, alpha=0.3, linestyle='--')
        # 叠加连接/扫描时图注移到右下角，给顶部连接条让出空间
        ax3.legend(loc='lower right' if has_overlay else 'upper right', fontsize=10)
        rssi_title = 'RSSI'
        if has_overlay:
            extra = ' + '.join(([] if not has_conn_overlay else ['连接状态(STA)'])
                               + ([] if not has_scan else ['扫描事件']))
            rssi_title = f'RSSI（叠加 {extra}）'
        ax3.set_title(rssi_title, fontsize=13, fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'No RSSI data', ha='center', va='center', transform=ax3.transAxes, fontsize=12, color='#666')
        ax3.set_ylabel('RSSI (dBm)', fontsize=12, color='#d62728')
        rssi_title = 'RSSI'
        if has_conn or has_scan:
            extra = ' + '.join(([] if not has_conn else ['连接状态'])
                               + ([] if not has_scan else ['扫描事件']))
            rssi_title = f'RSSI（无 RSSI 数据，仅显示 {extra}）'
        ax3.set_title(rssi_title, fontsize=13, fontweight='bold')

    # PER
    if has_per:
        ax4.plot(per_times, per_nums, color='#9467bd', marker='d', markersize=4, linewidth=1.2, label='PER')
        per_min, per_max = min(per_nums), max(per_nums)
        y_margin = max(abs(per_min) * 0.1, abs(per_max) * 0.1, 2)
        ax4.set_ylim(per_min - y_margin, per_max + y_margin)
        ax4.set_ylabel('PER', fontsize=12, color='#9467bd')
        ax4.tick_params(axis='y', labelcolor='#9467bd')
        ax4.grid(True, alpha=0.3, linestyle='--')
        ax4.legend(loc='upper right', fontsize=10)
        ax4.set_title('Packet Error Rate', fontsize=13, fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'No PER data', ha='center', va='center', transform=ax4.transAxes, fontsize=12, color='#666')
        ax4.set_ylabel('PER', fontsize=12, color='#9467bd')

    # 在 RSSI 子图上叠加连接状态条 + 扫描事件标记（共享同一本地时间轴）
    # 注意：传入 rssi_times，使「有 RSSI 处必有 STA 连接标记」
    if has_conn or has_scan or has_rssi or has_fail:
        x0 = plot_x_left if has_time else None
        x1 = plot_x_right if has_time else None
        draw_scan_and_connection_on_rssi(
            ax3, connection_sessions if has_conn else None,
            scan_events if has_scan else None, x0, x1, has_rssi,
            rssi_times=rssi_times if has_rssi else None,
            fail_events=fail_events if has_fail else None)

    # 各连接段竖虚线贯穿所有子图(同段同色)，便于跨子图对应连接状态
    if has_conn and has_time:
        draw_connection_spans_across([ax1, ax2, ax3, ax4], connection_sessions,
                                     plot_x_left, plot_x_right)

    # X 轴
    if has_time:
        ax4.set_xlim(plot_x_left, plot_x_right)
        win_times = [t for t in all_valid_times if plot_x_left <= t <= plot_x_right]
        if not win_times:
            win_times = all_valid_times
        tick_count = min(12, max(8, len(win_times) // 80))
        tick_interval = max(1, len(win_times) // tick_count)
        show_times = [win_times[i] for i in range(0, len(win_times), tick_interval)]
        ax4.set_xticks(show_times)
        ax4.xaxis.set_major_formatter(plt.FuncFormatter(format_x_time))
        ax4.tick_params(axis='x', labelrotation=60, width=1.2, length=6)
        plt.draw()
        for label in ax4.get_xticklabels():
            label.set_ha('right')
            label.set_fontweight('bold')
        ax4.set_xlabel('Time (MM-DD HH:MM:SS.mmm)', fontsize=13, fontweight='bold')

    # 保存
    if output_dir:
        save_dir = output_dir
    else:
        save_dir = os.path.dirname(os.path.abspath(source_file_path))
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, save_filename)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n图表已保存到：{save_path}")
    plt.close(fig)
    return save_path


def _extract_merged_scan_events(kernel_files, offset_hours):
    """从一个或多个 kernel 文件提取扫描事件并平移到本地时间，合并排序。"""
    events = []
    for kf in kernel_files or []:
        if kf and os.path.exists(kf):
            events.extend(extract_scan_events(kf))
    events = shift_scan_events(events, offset_hours)
    events.sort(key=lambda e: e['ts'])
    if events:
        n_zero = sum(1 for e in events if e['n_result'] == 0)
        print(f"扫描事件：{len(events)} 次 | 结果=0 的 {n_zero} 次 | "
              f"结果范围 {min(e['n_result'] for e in events)}~"
              f"{max(e['n_result'] for e in events)}")
    return events


def _resolve_offset_and_shift(data, all_times, ref_file, main_log_paths,
                              tz_offset_hours, kernel_files=None, show_scan=True):
    """决定时区偏移并平移 kernel 时间到本地，返回 (data, all_times, conn, scan_events, fail_events)。

    - 提供 main_log 时：检测/使用时区偏移并加载连接会话与失败事件。
    - 未提供 main_log 时：偏移为 0（kernel 原始时间），不加载连接。
    - show_scan 为真时，从 kernel_files 提取扫描事件(按同一偏移平移)。
    """
    conn = None
    fail_events = None
    if main_log_paths:
        if tz_offset_hours is None:
            tz_offset_hours = detect_tz_offset_hours(ref_file)
            if tz_offset_hours is None:
                tz_offset_hours = 0.0
                print("警告：无法自动检测时区偏移，kernel 与 main_log 可能未对齐，"
                      "可用 --tz-offset 手动指定(kernel 时间需要 +N 小时)")
            else:
                print(f"自动检测时区偏移：kernel(UTC) + {tz_offset_hours:.1f}h = 设备本地时间")
        else:
            print(f"使用指定时区偏移：kernel 时间 + {tz_offset_hours:.1f}h")
        data, all_times = shift_data_times(data, all_times, tz_offset_hours)
        conn = load_connection_sessions(main_log_paths)
        fill_bssid_from_kernel(conn, kernel_files)
        fill_bssid_from_main_log(conn, main_log_paths)
        fill_channel_from_kernel(conn, kernel_files)
        fail_events = load_fail_events(main_log_paths)
        offset = tz_offset_hours
    else:
        # 无 main_log：扫描标记沿用 kernel 原始时间(与已绘制的 kernel 数据一致)
        offset = tz_offset_hours or 0.0
        if offset:
            data, all_times = shift_data_times(data, all_times, offset)

    scan_events = _extract_merged_scan_events(kernel_files, offset) if show_scan else None
    return data, all_times, conn, scan_events, fail_events


def plot_from_file(file_path, output_dir=None, save_filename="kernel_log_curves.png",
                   main_log_paths=None, tz_offset_hours=None, show_scan=True):
    """
    单文件接口：提取数据 + 对齐 main_log 连接状态 + 扫描事件 + 绘图 + 保存
    绘图要求同时提供 kernel log 与 main_log，缺 main_log 返回 None。
    返回保存路径，失败返回 None
    """
    if not os.path.exists(file_path):
        print(f"文件不存在：{file_path}")
        return None

    if not main_log_paths:
        print("错误：绘图需要 main_log（请通过 main_log_paths 传入），"
              "缺少时连接状态只能灰色兜底，已拒绝绘图。")
        return None

    data, all_times = extract_data(file_path)
    if not (data and all_times):
        return None

    data, all_times, conn, scan_events, fail_events = _resolve_offset_and_shift(
        data, all_times, file_path, main_log_paths, tz_offset_hours,
        kernel_files=[file_path], show_scan=show_scan)

    return plot_quadruple(data, all_times, file_path, output_dir, save_filename,
                          connection_sessions=conn, scan_events=scan_events,
                          fail_events=fail_events)


def merge_data(data_list, times_list):
    """
    合并多个文件的提取数据。
    按时间排序，去重（同一时间戳保留最后出现的值）。
    """
    merged = {
        "Tput:": ([], []),
        "Tx(rate:": ([], []),
        "Rx(rate:": ([], []),
        ", rssi=": ([], []),
        "PER": ([], [])
    }
    all_times = []

    for data, times in zip(data_list, times_list):
        if not data or not times:
            continue
        for key in merged:
            t_list, v_list = data.get(key, ([], []))
            merged[key][0].extend(t_list)
            merged[key][1].extend(v_list)
        all_times.extend(times)

    # 按时间排序
    for key in merged:
        t_list, v_list = merged[key]
        if t_list and v_list:
            sorted_pairs = sorted(zip(t_list, v_list), key=lambda x: x[0])
            merged[key] = ([p[0] for p in sorted_pairs], [p[1] for p in sorted_pairs])

    all_times = sorted(set(all_times))
    return merged, all_times


def plot_from_files(file_paths, output_dir=None, save_filename="kernel_log_curves.png",
                    main_log_paths=None, tz_offset_hours=None, show_scan=True):
    """
    多文件合并接口：提取多个文件数据 → 合并 → 对齐 main_log + 扫描事件 → 绘制到同一张图
    绘图要求同时提供 kernel log 与 main_log，缺 main_log 返回 None。
    返回保存路径，失败返回 None
    """
    if not main_log_paths:
        print("错误：绘图需要 main_log（请通过 main_log_paths 传入），"
              "缺少时连接状态只能灰色兜底，已拒绝绘图。")
        return None

    data_list = []
    times_list = []
    valid_files = []

    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"文件不存在，跳过：{fp}")
            continue
        print(f"\n{'='*60}")
        print(f"提取数据：{os.path.basename(fp)}")
        print(f"{'='*60}")
        data, times = extract_data(fp)
        if data and times:
            data_list.append(data)
            times_list.append(times)
            valid_files.append(fp)

    if not data_list:
        print("无有效数据，跳过绘图")
        return None

    print(f"\n{'='*60}")
    print(f"合并 {len(valid_files)} 个文件的数据")
    print(f"{'='*60}")

    merged, all_times = merge_data(data_list, times_list)

    # 合并后统计
    print("\n合并后数据统计：")
    for keyword, (times, nums) in merged.items():
        key = "rssi" if keyword == ", rssi=" else keyword
        if nums:
            print(f"  {key}：{len(nums)}条 | 范围：{min(nums):.0f}~{max(nums):.0f}")
        else:
            print(f"  {key}：0条有效数据")

    if all_times:
        start = min(all_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        end = max(all_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        print(f"总时间区间：{start} ~ {end}")

    merged, all_times, conn, scan_events, fail_events = _resolve_offset_and_shift(
        merged, all_times, valid_files[0], main_log_paths, tz_offset_hours,
        kernel_files=valid_files, show_scan=show_scan)

    return plot_quadruple(merged, all_times, valid_files[0], output_dir, save_filename,
                          connection_sessions=conn, scan_events=scan_events,
                          fail_events=fail_events)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(f"用法: python {sys.argv[0]} <kernel.localtime ...> -m <main_log ...> "
              f"[--tz-offset HOURS] [-o output_dir] [-f save_filename]")
        print(f"示例: python {sys.argv[0]} kernel.localtime -m main_log "
              f"-o output/ -f ISSUE-123_link_quality.png")
        print("说明: 绘图需要同时提供 kernel log(位置参数) 与 main_log(-m)。")
        print("      -m 指定 main_log 后会解析真实连接会话(带 SSID/换网)并画成彩色连接条，"
              "并把 kernel(UTC) 时间按 .localtime 时区头自动平移到设备本地时间(与 main_log 对齐)；"
              "可用 --tz-offset 手动指定 kernel 需要 +N 小时。")
        print("      若仅有 kernel log，连接状态只能用灰色 RSSI 兜底推断，故本脚本要求必须带 main_log。")
        sys.exit(1)

    # 解析参数
    file_paths = []
    main_log_paths = []
    output_dir = None
    save_filename = "kernel_log_curves.png"
    tz_offset_hours = None
    show_scan = True
    i = 0

    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == "-f" and i + 1 < len(args):
            save_filename = args[i + 1]
            i += 2
        elif args[i] in ("-m", "--main-log") and i + 1 < len(args):
            main_log_paths.append(args[i + 1])
            i += 2
        elif args[i] == "--tz-offset" and i + 1 < len(args):
            try:
                tz_offset_hours = float(args[i + 1])
            except ValueError:
                print(f"无效的 --tz-offset 值：{args[i + 1]}")
                sys.exit(1)
            i += 2
        elif args[i] == "--no-scan":
            show_scan = False
            i += 1
        else:
            file_paths.append(args[i])
            i += 1

    if not file_paths:
        print("错误：未指定 kernel log 文件（绘图需要 kernel log + main_log）")
        sys.exit(1)

    if not main_log_paths:
        print("错误：未指定 main_log（绘图需要 kernel log + main_log）")
        print("      请用 -m/--main-log 指定至少一个 main_log，例如：")
        print(f"      python {sys.argv[0]} kernel.localtime -m main_log "
              "-o output/ -f ISSUE-123_link_quality.png")
        print("      原因：缺少 main_log 时无法解析真实连接会话，连接状态条会退化为"
              "灰色 RSSI 兜底推断（无 SSID/换网信息）。")
        sys.exit(1)

    main_log_paths = _dedupe_paths(main_log_paths)

    missing = [p for p in main_log_paths if not os.path.exists(p)]
    if missing:
        print("错误：以下 main_log 不存在：")
        for p in missing:
            print(f"      {p}")
        sys.exit(1)

    if len(file_paths) == 1:
        plot_from_file(file_paths[0], output_dir, save_filename,
                       main_log_paths=main_log_paths, tz_offset_hours=tz_offset_hours,
                       show_scan=show_scan)
    else:
        plot_from_files(file_paths, output_dir, save_filename,
                        main_log_paths=main_log_paths, tz_offset_hours=tz_offset_hours,
                        show_scan=show_scan)
