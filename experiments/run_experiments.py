"""Run BFS, DFS, UCS, and A* on the fixed test set and save CSV/JSON results."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from game import Engine, State, parse_board
from experiments.benchmark import SOLVERS, run_with_timeout

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = EXPERIMENTS_DIR / "test_set.json"
DEFAULT_RESULTS = EXPERIMENTS_DIR / "results.csv"
CSV_FIELDS = [
    "run_id", "case_id", "group", "difficulty", "source_level", "algorithm",
    "status", "search_time_seconds", "peak_memory_mb", "expanded_nodes",
    "solution_length", "total_cost", "preprocessing_time_seconds", "error",
]


def load_dataset(path: Path) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    cases = dataset.get("cases")
    if not isinstance(cases, list) or len(cases) < 100:
        raise ValueError(
            f"Test set phải có ít nhất 100 mẫu; hiện có {len(cases) if isinstance(cases, list) else 0}."
        )
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case_id bị trùng trong test set.")
    if any("board" not in case for case in cases):
        raise ValueError("Mỗi case phải nhúng board; benchmark không dùng levels/ của GUI.")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout per solver/case in seconds.")
    parser.add_argument("--algorithms", nargs="+", choices=list(SOLVERS), default=list(SOLVERS))
    parser.add_argument("--repeat", type=int, default=1, help="Number of repetitions per solver/case.")
    args = parser.parse_args()
    if args.timeout <= 0 or args.repeat < 1:
        parser.error("--timeout phải > 0 và --repeat phải >= 1.")

    dataset = load_dataset(args.dataset)
    cases = dataset["cases"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    total = len(cases) * len(args.algorithms) * args.repeat
    done = 0
    for repeat_index in range(1, args.repeat + 1):
        for case in cases:
            # Mỗi case nhúng đầy đủ board; benchmark không đọc levels/ của GUI.
            engine = Engine(parse_board(case["board"]))
            initial_state = State.from_dict(case["initial_state"])
            for algorithm in args.algorithms:
                done += 1
                print(
                    f"[{done}/{total}] {case['case_id']} ({case['group']}) / {algorithm} "
                    f"/ repeat {repeat_index}",
                    flush=True,
                )
                metrics = run_with_timeout(
                    SOLVERS[algorithm], initial_state, engine, args.timeout
                )
                rows.append({
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "group": case["group"],
                    "difficulty": case["difficulty"],
                    "source_level": case["source_level"],
                    "algorithm": algorithm,
                    **metrics,
                })

    # Mỗi lần chạy tạo file kết quả riêng, không âm thầm trộn dữ liệu cũ.
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(args.dataset),
        "dataset_version": dataset.get("dataset_version"),
        "case_count": len(cases),
        "algorithms": args.algorithms,
        "repeat": args.repeat,
        "timeout_seconds_per_solver_case": args.timeout,
        "python_version": sys.version,
        "platform": platform.platform(),
        "result_csv": str(args.output),
        "metric_notes": {
            "search_time_seconds": "Solver-reported search time in seconds; A* excludes heuristic preprocessing.",
            "preprocessing_time_seconds": "A* heuristic build time, recorded separately.",
            "peak_memory_mb": "Peak tracemalloc memory in decimal MB as reported by the solver.",
            "expanded_nodes": "Solver's expanded-state counter; goal state is not counted.",
            "solution_length": "Number of actions in the returned path; blank when no solution.",
            "total_cost": "Sum of Engine.step_cost along the returned path; blank when no solution.",
        },
    }
    metadata_path = args.output.with_name(args.output.stem + "_metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    solved = sum(row["status"] == "solved" for row in rows)
    timeouts = sum(row["status"] == "timeout" for row in rows)
    errors = sum(row["status"] == "error" for row in rows)
    print("\nBenchmark complete.")
    print(f"Rows: {len(rows)} | solved: {solved} | timeout: {timeouts} | errors: {errors}")
    print(f"CSV: {args.output}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
