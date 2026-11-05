#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "tqdm",
# ]
# ///
import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


def human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}PiB"


def run_jdupes(root: Path, hashdb: Path | None, quick: bool) -> dict:
    cmd = ["jdupes", "-r", "-q", "-j"]
    if hashdb:
        cmd += ["-y", str(hashdb)]
    if quick:
        cmd.append("-Q")
    cmd.append(str(root))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # jdupes exits 1 when no dupes are found, which is not an error here.
    if proc.returncode not in (0, 1):
        sys.exit(f"jdupes failed ({proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def bucket_of(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return str(path)


def count_files(root: Path) -> int:
    return sum(len(files) for _, _, files in os.walk(root))


def report(root: Path, data: dict, top: int) -> None:
    sets = data.get("matchSets", [])
    total_files = count_files(root)

    dup_files = 0
    wasted = 0
    cross_sets = cross_wasted = 0
    per_bucket_wasted: dict[str, int] = defaultdict(int)
    per_bucket_files: dict[str, int] = defaultdict(int)
    biggest = []

    for s in tqdm(sets, desc="Analyzing match sets", unit="set", leave=False):
        size = int(s["fileSize"])
        paths = [Path(f["filePath"]) for f in s["fileList"]]
        extra = len(paths) - 1
        set_wasted = size * extra

        dup_files += len(paths)
        wasted += set_wasted

        buckets = {bucket_of(p, root) for p in paths}
        if len(buckets) > 1:
            cross_sets += 1
            cross_wasted += set_wasted

        # Waste is attributed to the redundant copies, not the one kept.
        for p in paths[1:]:
            per_bucket_wasted[bucket_of(p, root)] += size
            per_bucket_files[bucket_of(p, root)] += 1

        biggest.append((set_wasted, size, len(paths), sorted(buckets), paths[0]))

    on_disk = shutil.disk_usage(root)
    print(f"\nRoot:            {root}")
    print(f"Files scanned:   {total_files:,}")
    print(f"Duplicate sets:  {len(sets):,}")
    print(f"Files in sets:   {dup_files:,} ({dup_files / total_files:.1%} of all files)")
    print(f"Redundant files: {dup_files - len(sets):,}")
    print(f"Reclaimable:     {human(wasted)}")
    print(f"  cross-app:     {human(cross_wasted)} in {cross_sets:,} sets")
    print(f"  within-app:    {human(wasted - cross_wasted)} in {len(sets) - cross_sets:,} sets")
    print(f"Volume free:     {human(on_disk.free)}")

    print("\nRedundant copies by top-level entry (keeper is the alphabetically first path):")
    for bucket, waste in sorted(per_bucket_wasted.items(), key=lambda kv: -kv[1]):
        print(f"  {human(waste):>10}  {per_bucket_files[bucket]:>7,} files  {bucket}")

    print(f"\nTop {top} match sets by reclaimable space:")
    for waste, size, count, buckets, sample in sorted(biggest, reverse=True)[:top]:
        print(f"  {human(waste):>10}  {count:>3}x {human(size):>9}  [{', '.join(buckets)}]")
        print(f"              {sample.relative_to(root)}")

    print(f"\nTo actually reclaim it (APFS copy-on-write clones, non-destructive):")
    print(f"  jdupes -r -B {root}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Report duplicate files under a directory via jdupes.")
    ap.add_argument("root", nargs="?", default="~/Applications", help="directory to scan")
    ap.add_argument("--top", type=int, default=20, help="how many largest match sets to list")
    ap.add_argument("--hash-db", help="jdupes hash database file, speeds up repeat runs")
    ap.add_argument("--quick", action="store_true", help="skip byte-for-byte confirmation (hash only)")
    args = ap.parse_args()

    if not shutil.which("jdupes"):
        sys.exit("jdupes not found; install with `brew install jdupes`")

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")

    hashdb = Path(args.hash_db).expanduser() if args.hash_db else None
    report(root, run_jdupes(root, hashdb, args.quick), args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
