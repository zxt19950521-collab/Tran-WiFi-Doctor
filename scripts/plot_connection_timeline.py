#!/usr/bin/env python3
"""
WiFi Connection State Timeline 绘图脚本
从 Android main_log 中提取 wlan/P2P/softap 连接状态事件，绘制甘特图式时间轴。

数据来源：main_log（非 kernel_log）
解析事件：
  - wlan STA: CTRL-EVENT-CONNECTED / CTRL-EVENT-DISCONNECTED
  - P2P: P2P-GROUP-STARTED / P2P-GROUP-REMOVED
  - softap: AP-ENABLED / AP-DISABLED

用法：
  # 单文件
  python scripts/plot_connection_timeline.py <main_log_file>

  # 多文件合并
  python scripts/plot_connection_timeline.py file1 file2 -o output/ -f ISSUE_timeline.png

  # 作为模块导入
  from scripts.plot_connection_timeline import plot_from_file, plot_from_files
"""

import re
import os
import sys
import tempfile
from datetime import datetime
from urllib.parse import unquote

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
except ImportError:
    print("正在安装 matplotlib...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch


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


def parse_time(time_str):
    """Parse 'MM-DD HH:MM:SS.mmmmmm' or 'MM-DD HH:MM:SS.mmm' to datetime (year=2026)."""
    time_str = f"2026 {time_str.strip()}"
    for fmt in ('%Y %m-%d %H:%M:%S.%f', '%Y %m-%d %H:%M:%S'):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def read_timestamp_sorted_lines(file_paths):
    """Read multiple log files and return timestamped lines sorted as one stream.

    This keeps open connection sessions alive across log rotation. Without this,
    parsing each main_log independently closes an open connection at that file's
    last timestamp, so timelines can incorrectly stop at the rotation point.
    """
    time_re = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    timestamped = []
    order = 0

    for file_path in file_paths:
        lines = []
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        for line in lines:
            tm = time_re.match(line.strip())
            if not tm:
                continue
            ts = parse_time(tm.group(1))
            if ts is None:
                continue
            timestamped.append((ts, order, line if line.endswith('\n') else line + '\n'))
            order += 1

    timestamped.sort(key=lambda item: (item[0], item[1]))
    return [line for _, _, line in timestamped]


def extract_sessions_from_files(file_paths):
    """Parse multiple main_log files as a single chronological stream."""
    lines = read_timestamp_sorted_lines(file_paths)
    if not lines:
        return {'wlan': [], 'p2p': [], 'softap': []}

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False,
                                        suffix='.main_log') as tmp:
            tmp_path = tmp.name
            tmp.writelines(lines)
        return extract_sessions(tmp_path)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def extract_ssid_from_id_str(id_str):
    """Extract SSID from URL-encoded id_str JSON like %7B%22configKey%22%3A%22%5C%22SSID%5C%22WPA_PSK%22..."""
    try:
        decoded = unquote(id_str)
        # Match "configKey":"\"SSID\"SECURITY" pattern
        m = re.search(r'configKey.*?\\"(.+?)\\"', decoded)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


class Session:
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

    @property
    def channel(self):
        if self.freq:
            return freq_to_channel(self.freq)
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
            # Show last 5 chars of MAC for brevity
            mac_short = self.bssid[-5:] if len(self.bssid) >= 5 else self.bssid
            parts.append(mac_short)
        if self.role:
            parts.append(self.role)
        return " | ".join(parts)


def extract_sessions(file_path):
    """
    Parse main_log for wlan/P2P/softap connection events.
    Returns dict: {'wlan': [Session], 'p2p': [Session], 'softap': [Session]}

    Supports multiple log patterns:
    - Trying to associate with SSID 'xxx' (extract SSID)
    - Associated with xx:xx:xx:xx:xx:xx (extract BSSID)
    - CTRL-EVENT-CONNECTED - Connection to xx:xx:xx:xx:xx:xx completed (extract BSSID)
    - CTRL-EVENT-DISCONNECTED bssid=xx:xx:xx:xx:xx:xx reason=N (extract BSSID and reason)
    """
    sessions = {'wlan': [], 'p2p': [], 'softap': []}
    # Track open sessions for matching end events
    open_wlan = {}  # bssid -> Session
    open_p2p = {}   # iface -> Session
    open_softap = None

    # Track pending association (SSID from "Trying to associate")
    pending_assoc = {}  # iface -> {'ssid': str, 'timestamp': datetime}

    # Regex patterns
    # Time prefix: "MM-DD HH:MM:SS.mmmmmm  PID  TID LEVEL TAG: "
    time_re = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')

    # wlan0: Trying to associate with SSID 'xxx'
    trying_associate_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+Trying to associate with SSID\s+\'([^\']+)\''
    )

    # wlan0: Associated with xx:xx:xx:xx:xx:xx
    associated_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+Associated with\s+([0-9a-fA-F:]+)'
    )

    # wlan0: CTRL-EVENT-CONNECTED - Connection to <BSSID> completed [id=N id_str=...]
    sta_connect_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+CTRL-EVENT-CONNECTED\s+-\s+Connection to\s+([0-9a-fA-F:]+)\s+completed'
        r'(?:\s+\[id=\d+\s+id_str=([^\]]*)\])?'
        r'(?:\s+freq=(\d+))?'
    )

    # wlan0: CTRL-EVENT-DISCONNECTED bssid=<BSSID> reason=<N> [locally_generated=<0|1>]
    sta_disconnect_re = re.compile(
        r'wpa_supplicant.*(\w+):\s+CTRL-EVENT-DISCONNECTED\s+bssid=([0-9a-fA-F:]+)\s+reason=(\d+)'
        r'(?:\s+locally_generated=(\d+))?'
    )

    # P2P-GROUP-STARTED <iface> <GO|client> ssid="<SSID>" freq=<N> go_dev_addr=<MAC>
    p2p_started_re = re.compile(
        r'wpa_supplicant.*P2P-GROUP-STARTED\s+(\S+)\s+(GO|client)\s+ssid="([^"]+)"\s+freq=(\d+)'
        r'(?:\s+go_dev_addr=([0-9a-fA-F:]+))?'
    )

    # P2P-GROUP-REMOVED <iface> <GO|client> reason=<R>
    p2p_removed_re = re.compile(
        r'wpa_supplicant.*P2P-GROUP-REMOVED\s+(\S+)\s+(GO|client)\s+reason=(\S+)'
    )

    # AP-ENABLED
    ap_enabled_re = re.compile(r'wpa_supplicant.*AP-ENABLED')
    # AP-DISABLED
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

        # Extract timestamp
        tm = time_re.match(line)
        if not tm:
            continue
        ts = parse_time(tm.group(1))
        if not ts:
            continue

        # --- Trying to associate with SSID ---
        m = trying_associate_re.search(line)
        if m:
            iface = m.group(1)
            ssid = m.group(2)
            pending_assoc[iface] = {'ssid': ssid, 'timestamp': ts}
            continue

        # --- Associated with BSSID ---
        m = associated_re.search(line)
        if m:
            iface = m.group(1)
            bssid = m.group(2)
            # Update pending association with BSSID
            if iface in pending_assoc:
                pending_assoc[iface]['bssid'] = bssid
            continue

        # --- wlan STA CONNECTED ---
        m = sta_connect_re.search(line)
        if m:
            iface = m.group(1)
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

            sess = Session('wlan', ts, ssid=ssid, bssid=bssid, freq=freq)
            open_wlan[bssid] = sess
            sessions['wlan'].append(sess)
            continue

        # --- wlan STA DISCONNECTED ---
        m = sta_disconnect_re.search(line)
        if m:
            iface = m.group(1)
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
            sess = Session('p2p', ts, ssid=ssid, bssid=go_mac, freq=freq, role=role)
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
            sess = Session('softap', ts)
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
            last_ts = parse_time(tm.group(1))
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

    return sessions


def merge_sessions(sessions_list):
    """Merge sessions from multiple files, sorted by start_time."""
    merged = {'wlan': [], 'p2p': [], 'softap': []}
    for sessions in sessions_list:
        for iface in merged:
            merged[iface].extend(sessions[iface])
    for iface in merged:
        merged[iface].sort(key=lambda s: s.start_time)
    return merged


# Color palette for different SSIDs
COLORS = [
    '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
    '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC',
    '#86BCB6', '#D37295', '#FABFD2', '#B6992D', '#499894',
]


def get_color_for_ssid(ssid, ssid_color_map):
    """Assign a consistent color to each SSID."""
    if ssid not in ssid_color_map:
        ssid_color_map[ssid] = COLORS[len(ssid_color_map) % len(COLORS)]
    return ssid_color_map[ssid]


def plot_timeline(sessions, output_dir, save_filename="connection_timeline.png",
                  source_file_path=""):
    """
    Plot connection timeline using thin colored lines for each SSID.
    Each SSID gets a unique color with legend showing SSID and MAC.
    """
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # Count total sessions
    total = sum(len(sessions[iface]) for iface in sessions)
    if total == 0:
        print("无连接事件，跳过绘图")
        return None

    # Collect all times for x-axis range
    all_times = []
    for iface in sessions:
        for s in sessions[iface]:
            all_times.extend([s.start_time, s.end_time])
    if not all_times:
        return None

    time_min = min(all_times)
    time_max = max(all_times)
    time_range = (time_max - time_min).total_seconds()

    # Build SSID color map
    ssid_color_map = {}
    ssid_sessions = {}  # ssid -> list of sessions

    # Group sessions by SSID
    for iface in sessions:
        for sess in sessions[iface]:
            ssid_key = sess.ssid or "(unknown)"
            if ssid_key not in ssid_sessions:
                ssid_sessions[ssid_key] = []
            ssid_sessions[ssid_key].append(sess)

    # Assign colors to SSIDs
    for ssid in ssid_sessions:
        if ssid not in ssid_color_map:
            ssid_color_map[ssid] = COLORS[len(ssid_color_map) % len(COLORS)]

    # Create figure
    fig, ax = plt.subplots(figsize=(max(14, time_range / 60), 6))

    # Plot each SSID's sessions as thin lines
    line_height = 0.6
    y_positions = {}
    current_y = 0

    for ssid in sorted(ssid_sessions.keys()):
        y_positions[ssid] = current_y
        color = ssid_color_map[ssid]

        for sess in ssid_sessions[ssid]:
            start_num = mdates.date2num(sess.start_time)
            end_num = mdates.date2num(sess.end_time)
            duration = (sess.end_time - sess.start_time).total_seconds()

            # Draw thin line
            ax.plot([start_num, end_num], [current_y, current_y],
                   color=color, linewidth=2.5, solid_capstyle='round')

            # Add SSID label on the line (if wide enough)
            if duration > time_range * 0.03:
                mid_x = start_num + (end_num - start_num) / 2
                # Get MAC short form
                mac_short = sess.bssid[-5:] if len(sess.bssid) >= 5 else sess.bssid
                label = f"{sess.ssid}\n{mac_short}"
                ax.text(mid_x, current_y, label,
                       ha='center', va='center', fontsize=7,
                       color=color, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor=color))

            # Add disconnect reason annotation
            if sess.end_reason:
                ax.annotate(
                    sess.end_reason,
                    xy=(end_num, current_y),
                    xytext=(5, 10),
                    textcoords='offset points',
                    fontsize=6,
                    color='#CC0000',
                    rotation=30,
                )

        current_y += 1

    # Y-axis
    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(list(y_positions.keys()), fontsize=10, fontweight='bold')
    ax.set_ylim(-0.5, current_y - 0.5)
    ax.invert_yaxis()

    # X-axis
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, fontsize=9)

    # Grid
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Title
    start_str = time_min.strftime('%m-%d %H:%M:%S')
    end_str = time_max.strftime('%m-%d %H:%M:%S')
    ax.set_title(f'WiFi Connection Timeline ({start_str} ~ {end_str})',
                fontsize=14, fontweight='bold', pad=15)

    # Legend with SSID and MAC
    legend_elements = []
    for ssid in sorted(ssid_sessions.keys()):
        color = ssid_color_map[ssid]
        # Get unique MACs for this SSID
        macs = set()
        for sess in ssid_sessions[ssid]:
            if sess.bssid:
                macs.add(sess.bssid)
        mac_str = ", ".join(sorted(macs)) if macs else "N/A"
        legend_elements.append(
            plt.Line2D([0], [0], color=color, linewidth=2.5,
                      label=f"{ssid} ({mac_str})")
        )

    ax.legend(handles=legend_elements, loc='upper right', fontsize=8,
             title='SSID (MAC)', title_fontsize=9,
             bbox_to_anchor=(1.0, 1.0))

    # Stats annotation
    stats_text = []
    for iface_key, name in [('wlan', 'wlan'), ('p2p', 'P2P'), ('softap', 'SoftAP')]:
        count = len(sessions[iface_key])
        if count > 0:
            stats_text.append(f"{name}: {count} sessions")
    if stats_text:
        ax.text(0.01, 1.02, " | ".join(stats_text),
               transform=ax.transAxes, fontsize=9, color='#666',
               verticalalignment='bottom')

    plt.tight_layout()

    # Save
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, save_filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n连接状态时间轴已保存到：{save_path}")
    plt.close(fig)
    return save_path


def print_summary(sessions):
    """Print session summary."""
    print("\n=== 连接会话统计 ===")
    for iface_key, name in [('wlan', 'wlan'), ('p2p', 'P2P'), ('softap', 'SoftAP')]:
        sess_list = sessions[iface_key]
        print(f"\n  {name}: {len(sess_list)} 个会话")
        for i, s in enumerate(sess_list):
            dur = s.duration
            dur_str = f"{dur:.1f}s" if dur < 120 else f"{dur/60:.1f}min"
            print(f"    [{i+1}] {s.start_time.strftime('%H:%M:%S')} ~ "
                  f"{s.end_time.strftime('%H:%M:%S')} ({dur_str}) "
                  f"SSID={s.ssid or '-'} {s.channel} BSSID={s.bssid or '-'} "
                  f"{s.role or ''} {s.end_reason}")


def plot_from_file(file_path, output_dir=None, save_filename="connection_timeline.png"):
    """Single file: extract + plot + save."""
    if not os.path.exists(file_path):
        print(f"文件不存在：{file_path}")
        return None

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(file_path))

    sessions = extract_sessions(file_path)
    total = sum(len(sessions[iface]) for iface in sessions)
    print(f"提取到 {total} 个连接会话 "
          f"(wlan={len(sessions['wlan'])}, p2p={len(sessions['p2p'])}, "
          f"softap={len(sessions['softap'])})")

    if total == 0:
        print("无连接事件，跳过绘图")
        return None

    print_summary(sessions)
    return plot_timeline(sessions, output_dir, save_filename, file_path)


def plot_from_files(file_paths, output_dir=None, save_filename="connection_timeline.png"):
    """Multi-file merge: parse files as one chronological stream → plot single chart."""
    valid_files = []

    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"文件不存在，跳过：{fp}")
            continue
        print(f"\n{'='*60}")
        print(f"纳入数据：{os.path.basename(fp)}")
        print(f"{'='*60}")
        valid_files.append(fp)

    if not valid_files:
        print("无有效数据")
        return None

    merged = extract_sessions_from_files(valid_files)
    total = sum(len(merged[iface]) for iface in merged)
    print(f"\n{'='*60}")
    print(f"合并 {len(valid_files)} 个文件为连续时间流: {total} 个连接会话")
    print(f"{'='*60}")

    print_summary(merged)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(valid_files[0]))

    return plot_timeline(merged, output_dir, save_filename)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(f"用法: python {sys.argv[0]} <file1> [file2 ...] [-o output_dir] [-f save_filename]")
        print(f"示例: python {sys.argv[0]} main_log_1 main_log_2 -o output/ -f ISSUE_timeline.png")
        sys.exit(1)

    # Parse arguments
    file_paths = []
    output_dir = None
    save_filename = "connection_timeline.png"
    i = 0
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == "-f" and i + 1 < len(args):
            save_filename = args[i + 1]
            i += 2
        else:
            file_paths.append(args[i])
            i += 1

    if not file_paths:
        print("错误：未指定文件")
        sys.exit(1)

    if len(file_paths) == 1:
        plot_from_file(file_paths[0], output_dir, save_filename)
    else:
        plot_from_files(file_paths, output_dir, save_filename)
