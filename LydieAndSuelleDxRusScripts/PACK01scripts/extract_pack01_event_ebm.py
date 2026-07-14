#!/usr/bin/env python3
"""Batch-extract PACK01 event_en event_message_*.ebm to JSON via gust_ebm."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PACK01_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACK01_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from rus_scripts_common import (  # noqa: E402
    EBM_GLOB,
    GUST_EBM,
    PACK01_EVENT_EBM_EXTRACT,
    PACK01_EVENT_EN,
    PACK01_EXTRACT,
)


def extract_ebm_json(ebm_path: Path, gust_ebm: Path) -> Path:
    subprocess.run([str(gust_ebm), str(ebm_path)], check=True)
    json_path = ebm_path.with_suffix(".json")
    if not json_path.is_file():
        raise FileNotFoundError(f"gust_ebm did not create {json_path}")
    return json_path


def stage_symlink(ebm_src: Path, work_ebm: Path) -> None:
    work_ebm.parent.mkdir(parents=True, exist_ok=True)
    if work_ebm.is_symlink():
        if work_ebm.resolve() == ebm_src.resolve():
            return
        work_ebm.unlink()
    elif work_ebm.exists():
        if work_ebm.resolve() == ebm_src.resolve():
            return
        raise FileExistsError(f"not a symlink: {work_ebm}")
    os.symlink(ebm_src.resolve(), work_ebm)


def needs_extract(ebm_path: Path, json_path: Path, *, force: bool) -> bool:
    if force:
        return True
    if not json_path.is_file():
        return True
    return json_path.stat().st_mtime < ebm_path.stat().st_mtime


def extract_one(work_ebm: Path, gust_ebm: Path, *, force: bool) -> bool:
    json_path = work_ebm.with_suffix(".json")
    if not needs_extract(work_ebm, json_path, force=force):
        return False
    extract_ebm_json(work_ebm, gust_ebm)
    return True


def _extract_worker(args: tuple[str, str, str, bool]) -> tuple[str, bool]:
    work_ebm_str, rel, gust_ebm_str, force = args
    work_ebm = Path(work_ebm_str)
    gust_ebm = Path(gust_ebm_str)
    skipped = not extract_one(work_ebm, gust_ebm, force=force)
    return rel, skipped


def collect_ebm_sources(source: Path) -> list[Path]:
    return sorted(source.rglob(EBM_GLOB))


def run_extract(
    *,
    source: Path,
    work_dir: Path,
    gust_ebm: Path,
    force: bool,
    limit: int | None,
    jobs: int,
) -> dict[str, int]:
    if not gust_ebm.is_file():
        raise FileNotFoundError(f"gust_ebm not found: {gust_ebm}")

    sources = collect_ebm_sources(source)
    if limit is not None:
        sources = sources[:limit]

    work_event_en = work_dir / "event/event_en"
    staged: list[Path] = []
    for ebm_src in sources:
        rel = ebm_src.relative_to(source)
        work_ebm = work_event_en / rel
        stage_symlink(ebm_src, work_ebm)
        staged.append(work_ebm)

    extracted = 0
    skipped = 0

    if jobs <= 1:
        for i, work_ebm in enumerate(staged, 1):
            if extract_one(work_ebm, gust_ebm, force=force):
                extracted += 1
            else:
                skipped += 1
            if i % 50 == 0 or i == len(staged):
                print(f"  {i}/{len(staged)} — extracted {extracted}, skipped {skipped}")
    else:
        tasks = [
            (str(work_ebm), str(work_ebm.relative_to(work_event_en)), str(gust_ebm), force)
            for work_ebm in staged
        ]
        done = 0
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_extract_worker, t): t for t in tasks}
            for fut in as_completed(futures):
                _, was_skipped = fut.result()
                if was_skipped:
                    skipped += 1
                else:
                    extracted += 1
                done += 1
                if done % 50 == 0 or done == len(staged):
                    print(f"  {done}/{len(staged)} — extracted {extracted}, skipped {skipped}")

    return {
        "ebm_count": len(staged),
        "extracted": extracted,
        "skipped": skipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PACK01_EVENT_EN)
    parser.add_argument("--work-dir", type=Path, default=PACK01_EVENT_EBM_EXTRACT)
    parser.add_argument("--gust-ebm", type=Path, default=GUST_EBM)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if JSON is up to date",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only first N EBM files (smoke test)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="Parallel gust_ebm workers (default 1)",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    work_dir = args.work_dir.resolve()
    gust_ebm = args.gust_ebm.resolve()

    if not source.is_dir():
        hint = ""
        if not PACK01_EXTRACT.is_dir():
            hint = f"\nRun PACKutils_scripts/extract_packs.py first (expected {PACK01_EXTRACT})"
        raise SystemExit(f"source not found: {source}{hint}")

    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"Source: {source}")
    print(f"Work dir: {work_dir}")
    stats = run_extract(
        source=source,
        work_dir=work_dir,
        gust_ebm=gust_ebm,
        force=args.force,
        limit=args.limit,
        jobs=max(1, args.jobs),
    )
    print(
        f"Done: {stats['ebm_count']} EBM, "
        f"extracted {stats['extracted']}, skipped {stats['skipped']}"
    )


if __name__ == "__main__":
    main()
