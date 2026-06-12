#!/usr/bin/env python3
"""Parse kernel log for kalPerMonUpdate/halDumpMsduReportStats and plot graphs."""

import re
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def parse_kernel_log(filepath):
    """Parse converted kernel log for kalPerMonUpdate and halDumpMsduReportStats."""
    # Format: 06-01 04:17:46.541 ... kalPerMonUpdate:... <1839ms> Tput: 976(0.000mbps) [132:2:93:1]... LQ[506120:517543:15157]...
    tput_pattern = re.compile(
        r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+).*kalPerMonUpdate.*?'
        r'Tput:\s*(\d+)\(([0-9.]+)mbps\)\s*'
        r'\[([0-9]+):([0-9]+):([0-9]+):([0-9]+)\].*?'
        r'LQ\[(\d+):(\d+):(\d+)\]'
    )
    # Format: 06-01 ... halDumpMsduReportStats ... C:[10:20:50:80]=[2:0:0:0:0#0] ... Txfail:0
    tx_delay_pattern = re.compile(
        r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+).*halDumpMsduReportStats.*'
        r'C:\[([0-9:]+)\]=\[([0-9#:]+)\].*'
        r'Txfail:(\d+)'
    )

    tput_data = []  # (time, throughput_mbps, lq_tx, lq_rx, lq_val, tx1, tx2, rx1, rx2)
    delay_data = []  # (time, delay_buckets, txfail)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = tput_pattern.search(line)
            if m:
                ts_str = m.group(1)
                tput_bytes = int(m.group(2))
                tput_mbps = float(m.group(3))
                tx1, tx2, rx1, rx2 = int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7))
                lq_tx = int(m.group(8))
                lq_rx = int(m.group(9))
                lq_val = int(m.group(10))
                try:
                    ts = datetime.strptime(f"2026-{ts_str}", "%Y-%m-%d %H:%M:%S.%f")
                except:
                    ts = datetime.strptime(f"2026-{ts_str}", "%Y-%m-%d %H:%M:%S")
                tput_data.append((ts, tput_mbps, lq_tx, lq_rx, lq_val, tx1, tx2, rx1, rx2))

            m2 = tx_delay_pattern.search(line)
            if m2:
                ts_str = m2.group(1)
                delay_str = m2.group(3)
                txfail = int(m2.group(4))
                try:
                    ts = datetime.strptime(f"2026-{ts_str}", "%Y-%m-%d %H:%M:%S.%f")
                except:
                    ts = datetime.strptime(f"2026-{ts_str}", "%Y-%m-%d %H:%M:%S")
                delay_data.append((ts, delay_str, txfail))

    return tput_data, delay_data


def calc_per(delay_data):
    """Calculate PER from halDumpMsduReportStats C: delay data."""
    per_data = []
    for ts, delay_str, txfail in delay_data:
        # Parse "count1:count2:count3:count4:count5#total"
        m = re.match(r'(\d+):(\d+):(\d+):(\d+):(\d+)#(\d+)', delay_str)
        if m:
            counts = [int(m.group(i)) for i in range(1, 6)]
            total = int(m.group(6))
            # PER = packets in >80ms bucket / total (or use txfail)
            if total > 0:
                per = (counts[-1] / total) * 100  # >80ms bucket as PER proxy
            else:
                per = 0
            per_data.append((ts, per, total, txfail))
    return per_data


def plot_graphs(tput_data, delay_data, output_dir, save_filename="kernel_metrics.png"):
    """Generate three graphs: negotiation rate, throughput, PER."""
    per_data = calc_per(delay_data)

    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    fig.suptitle('WiFi Kernel Metrics', fontsize=14, fontweight='bold')

    # Graph 1: Negotiation Rate (LQ values)
    if tput_data:
        times = [d[0] for d in tput_data]
        lq_vals = [d[4] for d in tput_data]  # LQ value (third field in LQ[x:y:z])

        axes[0].plot(times, lq_vals, 'b-o', markersize=3, linewidth=1)
        axes[0].set_ylabel('LQ Value')
        axes[0].set_title('Negotiation Rate (LQ Link Quality)')
        axes[0].grid(True, alpha=0.3)
        # If LQ is constant, annotate
        if len(set(lq_vals)) == 1:
            axes[0].axhline(y=lq_vals[0], color='g', linestyle='--', alpha=0.5)
            axes[0].annotate(f'Stable: {lq_vals[0]}', xy=(times[0], lq_vals[0]),
                           fontsize=10, color='green', fontweight='bold')

    # Graph 2: Throughput Rate
    if tput_data:
        tput_mbps = [d[1] for d in tput_data]
        axes[1].plot(times, tput_mbps, 'r-o', markersize=3, linewidth=1)
        axes[1].set_ylabel('Throughput (Mbps)')
        axes[1].set_title('Throughput Rate')
        axes[1].grid(True, alpha=0.3)
        # Mark burst and near-zero
        for i, (t, v) in enumerate(zip(times, tput_mbps)):
            if v > 100:
                axes[1].annotate(f'{v:.0f}', xy=(t, v), fontsize=7, ha='center', va='bottom')
            elif v < 1:
                axes[1].annotate(f'{v:.2f}', xy=(t, v), fontsize=7, ha='center', va='top', color='red')

    # Graph 3: PER (Packet Error Rate)
    if per_data:
        per_times = [d[0] for d in per_data]
        per_vals = [d[1] for d in per_data]
        axes[2].plot(per_times, per_vals, 'm-o', markersize=3, linewidth=1)
        axes[2].set_ylabel('PER (%)')
        axes[2].set_title('Packet Error Rate (>80ms TX delay ratio)')
        axes[2].grid(True, alpha=0.3)
        axes[2].axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10% threshold')
        axes[2].axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% threshold')
        axes[2].legend(loc='upper right')
        # Annotate high PER
        for t, v in zip(per_times, per_vals):
            if v > 50:
                axes[2].annotate(f'{v:.1f}%', xy=(t, v), fontsize=8, color='red', fontweight='bold')

    axes[2].set_xlabel('Time')
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = os.path.join(output_dir, save_filename)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Graph saved to: {output_path}")
    plt.close()


def print_summary(tput_data, delay_data):
    """Print summary statistics."""
    if tput_data:
        tputs = [d[1] for d in tput_data]
        print(f"\n=== Throughput Summary ===")
        print(f"  Samples: {len(tputs)}")
        print(f"  Max: {max(tputs):.2f} Mbps")
        print(f"  Min: {min(tputs):.2f} Mbps")
        print(f"  Avg: {sum(tputs)/len(tputs):.2f} Mbps")

        lq_vals = [d[4] for d in tput_data]
        print(f"\n=== LQ (Link Quality) ===")
        print(f"  Unique values: {set(lq_vals)}")
        print(f"  Constant: {len(set(lq_vals)) == 1}")

        tx_pkts = [d[5]+d[6] for d in tput_data]
        rx_pkts = [d[7]+d[8] for d in tput_data]
        print(f"\n=== Packet Counts ===")
        print(f"  TX total: {sum(tx_pkts)}")
        print(f"  RX total: {sum(rx_pkts)}")

    if delay_data:
        per_data = calc_per(delay_data)
        per_vals = [d[1] for d in per_data]
        print(f"\n=== PER Summary (from halDumpMsduReportStats) ===")
        print(f"  Samples: {len(per_vals)}")
        print(f"  Max PER: {max(per_vals):.1f}%")
        print(f"  Avg PER: {sum(per_vals)/len(per_vals):.1f}%")
        high_per = [v for v in per_vals if v > 50]
        print(f"  Samples >50% PER: {len(high_per)}")


def plot_from_file(file_path, output_dir=None, save_filename="kernel_metrics.png"):
    """One-shot interface: parse + plot + save."""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(output_dir, exist_ok=True)

    tput_data, delay_data = parse_kernel_log(file_path)
    print(f"Found {len(tput_data)} kalPerMonUpdate entries, {len(delay_data)} halDumpMsduReportStats entries")

    if tput_data or delay_data:
        print_summary(tput_data, delay_data)
        plot_graphs(tput_data, delay_data, output_dir, save_filename)
        return os.path.join(output_dir, save_filename)
    else:
        print("No matching data found in kernel log.")
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <kernel_log_file> [output_dir] [save_filename]")
        print(f"Example: python {sys.argv[0]} kernel_log.localtime output/ ISSUE-123_kernel_metrics.png")
        sys.exit(1)

    log_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    save_filename = sys.argv[3] if len(sys.argv) > 3 else "kernel_metrics.png"
    plot_from_file(log_file, output_dir, save_filename)
