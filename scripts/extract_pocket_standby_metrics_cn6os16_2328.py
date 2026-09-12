#!/usr/bin/env python3
"""Extract pocket standby metrics for CN6OS16-2328."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from statistics import mean

ISSUE_DIR = Path(r"d:\04_AI\Claude-Wifi-doctor\AI-result\issues\CN6OS16-2328")
POCKET = ISSUE_DIR / "logs" / "CN6 PIR" / "CN6" / "口袋待机"
APLOG = POCKET / "debuglogger" / "mobilelog" / "APLog_2026_0703_170159__11"
OUT_PATH = ISSUE_DIR / "pocket_standby_metrics.txt"

RE_TPUT = re.compile(r"kalPerMonUpdate.*?Tput:\s*(\d+)\(([\d.]+)mbps\)")
RE_CONSYS = re.compile(
    r"\[consys_power_state\]\[round:(\d+)\].*?wf:([\d.]+),(\d+);bt:.*?\[total\].*?wf:([\d.]+),(\d+)"
)
RE_SETSUSPEND = re.compile(r"SETSUSPENDMODE\s+(\d+)")
RE_TS = re.compile(r"^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")


def iter_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def find_kernel_localtimes(folder: Path) -> list[Path]:
    out = []
    for p in sorted(folder.rglob("kernel_log*")):
        if p.is_file() and not str(p).endswith(".localtime"):
            lt = Path(str(p) + ".localtime")
            if lt.exists():
                out.append(lt)
    return out


def find_main_logs(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("main_log*") if p.is_file())


def parse_kernels(paths: list[Path], lines_out: list[str]) -> None:
    lines_out.append("=== Kernel WiFi metrics: pocket standby ===")
    if not paths:
        lines_out.append("  (no kernel *.localtime found)")
        return
    for p in paths:
        lines_out.append(f"  File: {p.relative_to(POCKET)}")

    kal_total = nz_count = 0
    all_mbps: list[float] = []
    consys_parsed: list[tuple] = []
    wlan_pm = suspend_kw = 0
    ip170_hits: list[str] = []

    for path in paths:
        for line in iter_lines(path):
            if "wlan_pm_notifier" in line:
                wlan_pm += 1
            low = line.lower()
            if "suspend" in low and ("wlan" in low or "wifi" in low or "pm" in low):
                suspend_kw += 1
            if "170.114" in line:
                ip170_hits.append(line.strip()[:200])
                if len(ip170_hits) > 15:
                    ip170_hits.pop(0)
            if "kalPerMonUpdate" in line:
                m = RE_TPUT.search(line)
                if m:
                    kal_total += 1
                    if int(m.group(1)) > 0:
                        nz_count += 1
                        all_mbps.append(float(m.group(2)))
            if "consys_power_state" in line and "[total]" in line:
                m = RE_CONSYS.search(line)
                if m:
                    ts = line[:18] if len(line) >= 18 else ""
                    consys_parsed.append(
                        (
                            ts,
                            int(m.group(1)),
                            float(m.group(2)),
                            int(m.group(3)),
                            float(m.group(4)),
                            int(m.group(5)),
                        )
                    )

    ratio = (nz_count / kal_total * 100) if kal_total else 0.0
    lines_out.append(f"  kalPerMonUpdate parsed: {kal_total}")
    lines_out.append(f"  Tput > 0: {nz_count} ({ratio:.2f}% of kalPerMonUpdate)")
    if all_mbps:
        lines_out.append(
            f"  Tput (mbps) min/avg/max: {min(all_mbps):.3f} / {mean(all_mbps):.3f} / {max(all_mbps):.3f}"
        )
    lines_out.append(f"  consys_power_state [total] wf dumps: {len(consys_parsed)}")
    if consys_parsed:
        for tag, idx in zip(["first", "middle", "last"], [0, len(consys_parsed) // 2, -1]):
            ts, rnd, rwf, rwf_aux, twf_on, twf_off = consys_parsed[idx]
            denom = twf_on + twf_off
            off_pct = (twf_off / denom * 100) if denom else 0
            lines_out.append(
                f"    {tag} [{ts}] round={rnd}: round_wf={rwf},{rwf_aux}; "
                f"[total] wf on={twf_on}s off={twf_off}s (off/(on+off)={off_pct:.1f}%)"
            )
    lines_out.append(f"  wlan_pm_notifier line count (kernel): {wlan_pm}")
    lines_out.append(f"  suspend-related wlan/wifi/pm lines (kernel, heuristic): {suspend_kw}")
    lines_out.append(f"  170.114 mentions in kernel: {len(ip170_hits)}")
    for i, s in enumerate(ip170_hits[:8], 1):
        lines_out.append(f"    sample {i}: {s}")
    lines_out.append("")


def parse_main_logs(paths: list[Path], lines_out: list[str]) -> None:
    lines_out.append("=== main_log: pocket standby ===")
    if not paths:
        lines_out.append("  (no main_log* found)")
        return
    for p in paths:
        lines_out.append(f"  File: {p.relative_to(POCKET)}")

    mode0 = mode1 = 0
    screen_on: list[str] = []
    screen_off: list[str] = []
    softap_hits: list[str] = []
    softap_keywords = ("AP-ENABLED", "startSoftAp", "StartSoftAp", "SOFTAP", "SoftAp")
    zoom_hits = fb_hits = net170_hits = 0
    zoom_samples: list[str] = []
    fb_samples: list[str] = []
    net170_samples: list[str] = []
    wlan_pm_main = suspend_main = 0

    for path in paths:
        for line in iter_lines(path):
            mo = RE_TS.match(line)
            if "SETSUSPENDMODE" in line:
                sm = RE_SETSUSPEND.search(line)
                if sm:
                    if sm.group(1) == "0":
                        mode0 += 1
                    elif sm.group(1) == "1":
                        mode1 += 1
            if mo and ("SCREEN_ON" in line or "android.intent.action.SCREEN_ON" in line):
                screen_on.append(mo.group(1))
            if mo and ("SCREEN_OFF" in line or "android.intent.action.SCREEN_OFF" in line):
                screen_off.append(mo.group(1))
            if mo:
                for kw in softap_keywords:
                    if kw in line:
                        softap_hits.append(f"{mo.group(1)}: {line.strip()[:160]}")
                        break
            if "wlan_pm_notifier" in line:
                wlan_pm_main += 1
            low = line.lower()
            if "suspend" in low and ("wlan" in low or "wifi" in low or "pm" in low):
                suspend_main += 1
            if "us.zoom" in line or "zoom.videomeetings" in line:
                zoom_hits += 1
                if len(zoom_samples) < 5:
                    zoom_samples.append(line.strip()[:180])
            if "facebook" in low or "com.facebook" in line:
                fb_hits += 1
                if len(fb_samples) < 5:
                    fb_samples.append(line.strip()[:180])
            if "170.114" in line:
                net170_hits += 1
                if len(net170_samples) < 8:
                    net170_samples.append(line.strip()[:180])

    lines_out.append(f"  SETSUSPENDMODE mode 0 (resume): {mode0}")
    lines_out.append(f"  SETSUSPENDMODE mode 1 (suspend): {mode1}")
    lines_out.append(f"  SCREEN_ON events: {len(screen_on)}")
    if screen_on:
        lines_out.append(f"    times: {', '.join(screen_on)}")
    lines_out.append(f"  SCREEN_OFF events: {len(screen_off)}")
    if screen_off:
        lines_out.append(f"    times: {', '.join(screen_off)}")
    lines_out.append(f"  SoftAP indicators: {len(softap_hits)}")
    for h in softap_hits[:10]:
        lines_out.append(f"    {h}")
    if not softap_hits:
        lines_out.append("    (none in main_log)")
    lines_out.append(f"  wlan_pm_notifier lines (main): {wlan_pm_main}")
    lines_out.append(f"  suspend-related wlan/wifi/pm lines (main): {suspend_main}")
    lines_out.append(f"  Zoom-related lines: {zoom_hits}")
    for s in zoom_samples:
        lines_out.append(f"    {s}")
    lines_out.append(f"  Facebook-related lines: {fb_hits}")
    for s in fb_samples:
        lines_out.append(f"    {s}")
    lines_out.append(f"  170.114 network hints (main): {net170_hits}")
    for s in net170_samples:
        lines_out.append(f"    {s}")
    lines_out.append("")


def main() -> int:
    missing_lt = []
    for p in sorted(POCKET.rglob("kernel_log*")):
        if p.is_file() and not str(p).endswith(".localtime"):
            if not Path(str(p) + ".localtime").exists():
                missing_lt.append(str(p.relative_to(POCKET)))

    kernels = find_kernel_localtimes(POCKET)
    mains = find_main_logs(POCKET)

    lines: list[str] = []
    lines.append("CN6OS16-2328 pocket standby (口袋待机) metrics summary")
    lines.append("=" * 60)
    lines.append(f"Folder: {POCKET}")
    lines.append(f"kernel_log* without .localtime (after conversion pass): {len(missing_lt)}")
    for m in missing_lt:
        lines.append(f"  STILL MISSING: {m}")
    lines.append("")

    parse_kernels(kernels, lines)
    parse_main_logs(mains, lines)

    text = "\n".join(lines)
    OUT_PATH.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
