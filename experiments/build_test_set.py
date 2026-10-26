"""Gộp 20 level GUI vào test set cố định: 100 case độc lập + 20 case GUI = 120.

Chạy lại được nhiều lần: các case GUI cũ (``origin == "gui_level"``) bị thay
bằng bản dựng mới từ ``levels/level*.json``; 100 case độc lập giữ nguyên.
Board được nhúng vào JSON nên runner không đọc ``levels/`` khi benchmark.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from game import Board, Engine, parse_board
from solvers import solve_bfs

ROOT = Path(__file__).resolve().parents[1]
LEVELS_DIR = ROOT / "levels"
DEFAULT_DATASET = Path(__file__).resolve().parent / "test_set.json"
GUI_ORIGIN = "gui_level"
ADVANCED_GROUP = "advanced_switches"
GROUPS = ("basic", "fragile", "switches_bridges", "combined", ADVANCED_GROUP)
ADVANCED_DEFINITION = (
    "Heavy and/or split switches, with any mix of fragile tiles, bridges and soft "
    "switches. Only GUI levels use these mechanics."
)


def level_number(path: Path) -> int:
    match = re.fullmatch(r"level(\d+)\.json", path.name)
    if match is None:
        raise ValueError(f"Tên level GUI không hợp lệ: {path.name}")
    return int(match.group(1))


def gui_level_paths() -> list[Path]:
    """Trả level GUI theo thứ tự số: level1, level2, ..., level20."""
    paths = sorted(LEVELS_DIR.glob("level*.json"), key=level_number)
    if not paths:
        raise ValueError(f"Không có level GUI trong {LEVELS_DIR}")
    return paths


def classify(board: Board) -> str:
    """Gán nhóm theo mechanics có trên board, khớp ``group_definitions``.

    Bốn nhóm của 100 case độc lập chỉ có fragile, bridge và soft switch. Level
    có heavy hoặc split switch thuộc nhóm riêng ``advanced_switches``.
    """
    if any(switch.get("type") in ("heavy", "split") for switch in board.switches):
        return ADVANCED_GROUP
    has_fragile = any("F" in row for row in board.grid_raw)
    has_switches_or_bridges = bool(board.bridges or board.switches)
    if has_fragile and has_switches_or_bridges:
        return "combined"
    if has_fragile:
        return "fragile"
    if has_switches_or_bridges:
        return "switches_bridges"
    return "basic"


def difficulty(solution_length: int) -> str:
    """Cùng ngưỡng với test set độc lập: easy <22, medium 22-31, hard >=32."""
    if solution_length < 22:
        return "easy"
    if solution_length < 32:
        return "medium"
    return "hard"


def features(board: Board) -> list[str]:
    found = []
    if any("F" in row for row in board.grid_raw):
        found.append("fragile tiles")
    if board.bridges:
        found.append("bridges")
    for kind in ("soft", "heavy", "split"):
        if any(switch.get("type") == kind for switch in board.switches):
            found.append(f"{kind} switch")
    return found


def gui_case(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    board = parse_board(raw)
    engine = Engine(board)
    initial_state = engine.get_initial_state()
    reference = solve_bfs(initial_state, engine)
    if not reference.solved:
        raise ValueError(f"BFS không giải được {path.name}; không đưa vào test set.")
    return {
        # Theo số trong tên file để ID không lệch khi thêm/xoá level.
        "case_id": f"GUI-{level_number(path):03d}",
        "group": classify(board),
        "difficulty": difficulty(reference.solution_length),
        "source_level": path.name,
        "board": raw,
        "initial_state": initial_state.to_dict(),
        "reference_solution_length": reference.solution_length,
        "reference_expanded_nodes": reference.expanded_nodes,
        "design_notes": {"origin": GUI_ORIGIN, "features": features(board)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed the 20 GUI levels into the fixed test set (100 + 20 = 120 cases)."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    independent = [
        case for case in dataset["cases"]
        if case.get("design_notes", {}).get("origin") != GUI_ORIGIN
    ]
    gui_cases = [gui_case(path) for path in gui_level_paths()]
    cases = independent + gui_cases
    counts = {group: sum(case["group"] == group for case in cases) for group in GROUPS}
    constraints = dataset["design_constraints"]

    dataset["dataset_version"] = 3
    dataset["case_count"] = len(cases)
    dataset["selection_method"] = (
        f"{len(independent)} unique independently generated 13x17 board layouts "
        f"plus the {len(gui_cases)} GUI levels from levels/ (case_id GUI-xxx). "
        "Each case embeds its complete board definition and canonical initial state, "
        "so benchmark runs never read levels/. All cases were solved and validated "
        "with BFS before inclusion; fixed JSON is shared by every algorithm."
    )
    dataset["groups"] = list(GROUPS)
    constraints["independent_cases_per_group"] = {
        group: sum(case["group"] == group for case in independent)
        for group in GROUPS[:4]
    }
    constraints["cases_per_group"] = counts
    constraints["group_definitions"][ADVANCED_GROUP] = ADVANCED_DEFINITION
    constraints["gui_cases"] = (
        "GUI levels are embedded as-is (all mechanics, including heavy and split "
        "switches). Group is assigned by mechanics present on the board: levels "
        "with heavy or split switches go to advanced_switches, the rest use the "
        "four independent groups. GUI levels are not filtered by the minimum "
        "length/expanded-node constraints above, and their fragile tiles may lie "
        "on the solution path."
    )
    dataset["cases"] = cases
    args.dataset.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{args.dataset}: {len(independent)} independent + "
        f"{len(gui_cases)} GUI = {len(cases)} cases; per group {counts}"
    )


if __name__ == "__main__":
    main()
