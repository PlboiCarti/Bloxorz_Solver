"""Benchmark the four required solvers on the levels available in the GUI."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.benchmark import SOLVERS, run_with_timeout
from game import Board, Engine, load_board

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = Path(__file__).resolve().parent
LEVELS_DIR = ROOT / "levels"
DEFAULT_RESULTS = EXPERIMENTS_DIR / "results.csv"

CSV_FIELDS = [
    "run_id",
    "case_id",
    "group",
    "difficulty",
    "source_level",
    "algorithm",
    "status",
    "search_time_seconds",
    "peak_memory_mb",
    "expanded_nodes",
    "solution_length",
    "total_cost",
    "preprocessing_time_seconds",
    "error",
]


def discover_gui_levels() -> list[Path]:
    """Return all playable GUI levels in natural numeric order."""
    paths = list(LEVELS_DIR.glob("level*.json"))

    def level_number(path: Path) -> int:
        match = re.fullmatch(r"level(\d+)\.json", path.name, re.IGNORECASE)
        if match is None:
            raise ValueError(f"Invalid GUI level filename: {path.name}")
        return int(match.group(1))

    paths.sort(key=level_number)
    if not paths:
        raise ValueError(f"No GUI levels found in {LEVELS_DIR}")
    return paths


def classify_level(board: Board) -> str:
    """Group levels by the advanced mechanics described in the assignment."""
    has_fragile = any("F" in row for row in board.grid_raw)
    has_switches_or_bridges = bool(board.bridges or board.switches)
    if has_fragile and has_switches_or_bridges:
        return "combined"
    if has_fragile:
        return "fragile"
    if has_switches_or_bridges:
        return "switches_bridges"
    return "basic"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS,
        help="CSV output path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Timeout per solver and GUI level in seconds.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=list(SOLVERS),
        default=list(SOLVERS),
        help="Algorithms to benchmark.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of repetitions per GUI level and algorithm.",
    )
    args = parser.parse_args()
    if args.timeout <= 0 or args.repeat < 1:
        parser.error("--timeout must be > 0 and --repeat must be >= 1.")

    level_paths = discover_gui_levels()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    total = len(level_paths) * len(args.algorithms) * args.repeat
    done = 0
    for repeat_index in range(1, args.repeat + 1):
        for level_path in level_paths:
            board = load_board(level_path)
            engine = Engine(board)
            initial_state = engine.get_initial_state()
            case_id = level_path.stem
            group = classify_level(board)

            for algorithm in args.algorithms:
                done += 1
                print(
                    f"[{done}/{total}] {case_id} ({group}) / {algorithm} "
                    f"/ repeat {repeat_index}",
                    flush=True,
                )
                metrics = run_with_timeout(
                    SOLVERS[algorithm], initial_state, engine, args.timeout
                )
                rows.append(
                    {
                        "run_id": run_id,
                        "case_id": case_id,
                        "group": group,
                        "difficulty": "",
                        "source_level": level_path.name,
                        "algorithm": algorithm,
                        **metrics,
                    }
                )

    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "levels_dir": str(LEVELS_DIR),
        "levels": [path.name for path in level_paths],
        "case_count": len(level_paths),
        "algorithms": args.algorithms,
        "repeat": args.repeat,
        "timeout_seconds_per_solver_case": args.timeout,
        "python_version": sys.version,
        "platform": platform.platform(),
        "result_csv": str(args.output),
        "metric_notes": {
            "search_time_seconds": "Solver-reported search time in seconds.",
            "peak_memory_mb": "Peak memory measured with tracemalloc in MB.",
            "expanded_nodes": "Number of expanded states; the goal state is not counted.",
            "solution_length": "Number of actions in the returned solution path.",
        },
    }
    metadata_path = args.output.with_name(args.output.stem + "_metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    solved = sum(row["status"] == "solved" for row in rows)
    unsolved = sum(row["status"] == "unsolved" for row in rows)
    timeouts = sum(row["status"] == "timeout" for row in rows)
    errors = sum(row["status"] == "error" for row in rows)
    print("\nBenchmark complete.")
    print(
        f"Rows: {len(rows)} | solved: {solved} | unsolved: {unsolved} "
        f"| timeout: {timeouts} | errors: {errors}"
    )
    print(f"CSV: {args.output}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
