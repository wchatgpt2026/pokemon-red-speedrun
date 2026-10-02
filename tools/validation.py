#!/usr/bin/env python3
"""WP004 build validation. Python 3 standard library; RGBDS 1.0.4 maps."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("pokered", "pokeblue", "pokeblue_debug")
# Hardware address spaces, not project section placements. -d joins WRAM0/1.
BOUNDS = {"ROM0": (0, 0x4000), "ROMX": (0x4000, 0x8000),
          "VRAM": (0x8000, 0xa000), "SRAM": (0xa000, 0xc000),
          "WRAM0": (0xc000, 0xe000), "HRAM": (0xff80, 0xffff)}
CRITICAL = {1, 2, 3, 0x0e, 0x0f, 0x19, 0x1a, 0x1b, 0x1e, 0x1f}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_map(path):
    """Reconcile sections + holes + per-bank totals with the linker summary.

    Reject unknown records rather than treating a changed map format as zero.
    Zero-length sections and aliased symbols are valid and occupy no extra bytes.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0] == "SUMMARY:", f"{path}: missing SUMMARY")
    summary, banks = {}, {}
    current = None
    for number, line in enumerate(lines[1:], 2):
        s = line.strip()
        if not s:
            continue
        where = f"{path}:{number}"
        m = re.fullmatch(r"(\w+): (\d+) bytes used / (\d+) free(?: in (\d+) banks)?", s)
        if m:
            kind, used, free, count = m.groups()
            require(not banks and kind in BOUNDS and kind not in summary,
                    f"{where}: duplicate/unknown/misplaced summary")
            summary[kind] = (int(used), int(free), int(count or 1))
            continue
        m = re.fullmatch(r"(\w+) bank #(\d+):", s)
        if m:
            require(current is None, f"{where}: missing TOTAL EMPTY")
            kind, bank = m[1], int(m[2])
            key = f"{kind}:{bank:02x}"
            require(kind in BOUNDS and key not in banks, f"{where}: unknown/duplicate bank")
            current = {"region": kind, "bank": bank, "free": 0,
                       "largest_hole": 0, "used": 0, "ranges": []}
            banks[key] = current
            continue
        require(current is not None, f"{where}: record outside bank: {s}")
        m = re.fullmatch(r'(SECTION|EMPTY): \$([0-9a-f]+)(?:-\$([0-9a-f]+))? '
                         r'\(\$([0-9a-f]+) bytes?\)(?: \[".*"\])?', s)
        if m:
            record, start, end, size = m.groups()
            start, size = int(start, 16), int(size, 16)
            end = int(end, 16) + 1 if end else start + size
            lo, hi = BOUNDS[current["region"]]
            require(end - start == size and lo <= start <= end <= hi,
                    f"{where}: invalid range/size")
            if size:
                current["ranges"].append((start, end))
            if record == "EMPTY":
                current["free"] += size
                current["largest_hole"] = max(current["largest_hole"], size)
            else:
                current["used"] += size
            continue
        m = re.fullmatch(r"TOTAL EMPTY: \$([0-9a-f]+) bytes?", s)
        if m:
            require(current["free"] == int(m[1], 16), f"{where}: free total mismatch")
            lo, hi = BOUNDS[current["region"]]
            position = lo
            for start, end in sorted(current.pop("ranges")):
                require(start == position, f"{where}: overlapping or omitted address range")
                position = end
            require(position == hi, f"{where}: incomplete bank")
            current = None
            continue
        require(re.fullmatch(r"\$[0-9a-f]+ = \S+", s), f"{where}: unknown record: {s}")
    require(current is None, f"{path}: truncated bank")
    for kind in ("ROM0", "ROMX", "SRAM", "WRAM0", "HRAM"):
        require(kind in summary, f"{path}: missing {kind} summary")
    for kind in BOUNDS:
        entries = [v for v in banks.values() if v["region"] == kind]
        used = sum(v["used"] for v in entries)
        free = sum(v["free"] for v in entries)
        if kind in summary:
            require((used, free, len(entries)) == summary[kind],
                    f"{path}: {kind} summary disagrees with banks")
        elif kind != "VRAM": # RGBDS omits VRAM from SUMMARY.
            require(used == 0, f"{path}: missing used-region summary: {kind}")
    for key in ("ROM0:00", "WRAM0:00", "HRAM:00"):
        require(key in banks, f"{path}: missing {key}")
    return banks


def read_symbols(path):
    symbols = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(";"):
            continue
        if re.fullmatch(r"[0-9a-fA-F]+ \S+", line):
            continue # RGBDS exported numeric constants, not banked addresses.
        m = re.fullmatch(r"([0-9a-fA-F]+):([0-9a-fA-F]+) (\S+)", line)
        require(m is not None, f"{path}: malformed symbol record")
        require(m[3] not in symbols, f"{path}: duplicate symbol {m[3]}")
        symbols[m[3]] = (int(m[1], 16), int(m[2], 16))
    return symbols


def check_rom(path, banks, symbols, debug):
    rom = path.read_bytes()
    require(len(rom) >= 0x150, f"{path}: truncated ROM")
    require(rom[0x148] <= 8 and len(rom) == 0x8000 << rom[0x148],
            f"{path}: ROM size/header mismatch")
    require(rom[0x147] == 0x13 and rom[0x149] == 3,
            f"{path}: expected MBC3+RAM+BATTERY / 32 KiB SRAM")
    require(rom[0x14d] == (-sum(rom[0x134:0x14d]) - 25) & 255,
            f"{path}: header checksum mismatch")
    require(int.from_bytes(rom[0x14e:0x150], "big") ==
            (sum(rom[:0x14e]) + sum(rom[0x150:])) & 65535,
            f"{path}: global checksum mismatch")
    title = b"POKEMON RED" if path.stem == "pokered" else b"POKEMON BLUE"
    require(rom[0x134:0x134 + len(title)] == title, f"{path}: wrong variant title")
    for entry in banks.values():
        if entry["region"] == "ROMX":
            require(0 < entry["bank"] < len(rom) // 0x4000, f"{path}: bank outside ROM")
    require({v["bank"] for v in banks.values() if v["region"] == "SRAM"} == set(range(4)),
            f"{path}: expected all four SRAM banks to be described")
    for symbol in ("Init", "InitBattle", "wPartyCount", "wObtainedBadges", "wEventFlags"):
        require(symbol in symbols, f"{path}: missing required symbol {symbol}")
    fixtures = {s for s in symbols if s.startswith("WP004")}
    required = {"WP004BattleFixture", "WP004BattleReady", "WP004MapFixture", "WP004MapReady"}
    require(required <= fixtures if debug else not fixtures,
            f"{path}: debug fixture isolation failure")
    return hashlib.sha256(rom).hexdigest()


def collect(root):
    result = {}
    reference_ram = None
    for variant in VARIANTS:
        banks = parse_map(root / f"{variant}.map")
        symbols = read_symbols(root / f"{variant}.sym")
        ram_symbols = {name: location for name, location in symbols.items()
                       if 0xa000 <= location[1] <= 0xffff}
        if reference_ram is None:
            reference_ram = ram_symbols
        require(ram_symbols == reference_ram, f"{variant}: RAM symbol layout differs from Red")
        digest = check_rom(root / f"{variant}.gbc", banks, symbols, variant.endswith("_debug"))
        result[variant] = {"sha256": digest, "banks": banks}
    # Fixtures must not allocate RAM: saved data and scratch layouts stay common.
    for variant in VARIANTS[1:]:
        for key, entry in result[VARIANTS[0]]["banks"].items():
            if entry["region"] in ("WRAM0", "HRAM", "SRAM"):
                require(result[variant]["banks"].get(key) == entry,
                        f"{variant}: RAM allocation differs from Red in {key}")
    return result


def warnings(report, baseline):
    messages = []
    require(set(baseline) == set(VARIANTS), "baseline variant set mismatch")
    for variant, data in report.items():
        old = baseline[variant]["banks"]
        require(set(data["banks"]) == set(old),
                f"{variant}: bank topology changed; review layout and update baseline explicitly")
        for key, entry in data["banks"].items():
            previous = old[key]["free"]
            require(isinstance(previous, int) and previous >= 0, f"baseline: invalid {key}")
            critical = (entry["region"] in ("ROM0", "WRAM0", "HRAM") or
                        entry["region"] == "ROMX" and
                        (entry["bank"] in CRITICAL or previous <= 128))
            if critical and entry["free"] < previous:
                messages.append(f"{variant} {key}: headroom shrank by {previous - entry['free']} "
                                f"bytes ({previous} -> {entry['free']})")
    return messages


def render(report, baseline):
    print("Free bytes by linker bank (hex); largest contiguous hole in parentheses.")
    print("Area          Red             Blue            Blue debug")
    first = report[VARIANTS[0]]["banks"]
    for key in first:
        if first[key]["region"] == "VRAM":
            continue
        values = []
        for variant in VARIANTS:
            e = report[variant]["banks"][key]
            delta = e["free"] - baseline[variant]["banks"][key]["free"]
            values.append(f"{e['free']:5} ({e['largest_hole']:5}) {delta:+d}")
        print(f"{key:10}  " + "  ".join(values))
    print("Values end with signed free-byte delta from the reviewed WP004 baseline.")
    for variant, data in report.items():
        entries = data["banks"].values()
        total = sum(e["free"] for e in entries if e["region"] in ("ROM0", "ROMX"))
        sram = sum(e["free"] for e in entries if e["region"] == "SRAM")
        print(f"{variant}: allocated ROM free={total}; declared SRAM unallocated={sram}")
    print("Totals are NOT same-bank capacity. Holes may be fragmented; alignment and near pointers")
    print("can further constrain placement. ROM padding is excluded; SRAM gaps are not save-format permission.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="build artifact directory")
    parser.add_argument("--baseline", type=Path, default=ROOT / "tools/capacity-baseline.json")
    parser.add_argument("--json", action="store_true", help="emit machine-readable report")
    parser.add_argument("--check", action="store_true", help="structural validation with concise output")
    args = parser.parse_args()
    try:
        report = collect(args.root)
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        notices = warnings(report, baseline)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.check:
            print("PASS: Red, Blue, Blue debug headers, checksums, maps, symbols and fixture isolation")
        else:
            render(report, baseline)
        for message in notices:
            print(f"WARNING: {message}", file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
