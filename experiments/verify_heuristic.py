"""Kiểm chứng thực nghiệm admissible/consistent của heuristic trên test set.

Với mỗi case: duyệt toàn bộ concrete state đạt được từ initial state (chỉ cạnh
``OK``), tính chi phí tối ưu thật h* bằng reverse Dijkstra từ mọi goal state,
rồi kiểm tra cho từng heuristic:

- admissible: h(s) <= h*(s) với mọi state đạt được;
- consistent: h(s) <= c(s, a, s') + h(s') với mọi cạnh OK;
- h(goal) = 0.

Heuristic được kiểm tra:

- ``H2``: đúng hàm A* đang dùng (``inf`` được fallback về 0);
- ``H2_inf``: khoảng cách abstract d_alpha giữ nguyên ``inf`` (``H2Heuristic.distance``);
- ``H1``: baseline Manhattan.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import itertools
import math
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from experiments.run_experiments import DEFAULT_DATASET, load_dataset
from game import Engine, State, TransitionStatus, parse_board
from solvers import build_h1, build_h2

EPS = 1e-9
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "heuristic_check.csv"
HEURISTICS = ("H2", "H2_inf", "H1")


def explore(engine: Engine, start: State) -> tuple[list[State], list[tuple[State, State, float]]]:
    """Toàn bộ state đạt được và mọi cạnh OK cùng chi phí ``Engine.step_cost``."""
    seen = {start}
    stack = [start]
    edges: list[tuple[State, State, float]] = []
    while stack:
        state = stack.pop()
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            if result.status is not TransitionStatus.OK or result.state is None:
                continue
            nxt = result.state
            edges.append((state, nxt, engine.step_cost(state, action, nxt)))
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return list(seen), edges


def true_costs(
    engine: Engine,
    states: list[State],
    edges: list[tuple[State, State, float]],
) -> dict[State, float]:
    """h*(s): chi phí tối ưu tới goal, ``inf`` nếu không tới được."""
    reverse: dict[State, list[tuple[State, float]]] = defaultdict(list)
    for source, target, cost in edges:
        reverse[target].append((source, cost))
    distance = {state: math.inf for state in states}
    serial = itertools.count()
    frontier: list[tuple[float, int, State]] = []
    for state in states:
        if engine.is_goal(state):
            distance[state] = 0.0
            frontier.append((0.0, next(serial), state))
    heapq.heapify(frontier)
    while frontier:
        current, _, state = heapq.heappop(frontier)
        if current != distance[state]:
            continue
        for predecessor, cost in reverse[state]:
            candidate = current + cost
            if candidate < distance[predecessor]:
                distance[predecessor] = candidate
                heapq.heappush(frontier, (candidate, next(serial), predecessor))
    return distance


def check(
    estimate: Callable[[State], float],
    engine: Engine,
    states: list[State],
    edges: list[tuple[State, State, float]],
    optimal: dict[State, float],
) -> dict[str, int]:
    values = {state: estimate(state) for state in states}
    return {
        "admissible_violations": sum(values[s] > optimal[s] + EPS for s in states),
        "consistent_violations": sum(
            values[source] > cost + values[target] + EPS for source, target, cost in edges
        ),
        "goal_nonzero": sum(engine.is_goal(s) and values[s] != 0 for s in states),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check admissibility and consistency of H1/H2 on every reachable state."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cases = load_dataset(args.dataset)["cases"]
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases, 1):
        engine = Engine(parse_board(case["board"]))
        start = State.from_dict(case["initial_state"])
        states, edges = explore(engine, start)
        optimal = true_costs(engine, states, edges)
        context = engine.get_heuristic_context()
        h2 = build_h2(context)
        estimates = {"H2": h2, "H2_inf": h2.distance, "H1": build_h1(context)}
        row: dict[str, Any] = {
            "case_id": case["case_id"],
            "source_level": case["source_level"],
            "states": len(states),
            "edges": len(edges),
            "dead_end_states": sum(math.isinf(optimal[s]) for s in states),
        }
        for name in HEURISTICS:
            for key, value in check(estimates[name], engine, states, edges, optimal).items():
                row[f"{name}_{key}"] = value
        rows.append(row)
        print(f"[{index}/{len(cases)}] {case['case_id']}: {len(states)} states, {len(edges)} edges", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"\nCases: {len(rows)} | states: {sum(r['states'] for r in rows)} "
        f"| edges: {sum(r['edges'] for r in rows)}"
    )
    for name in HEURISTICS:
        summary = []
        for key in ("admissible_violations", "consistent_violations", "goal_nonzero"):
            column = f"{name}_{key}"
            bad = [r["case_id"] for r in rows if r[column]]
            summary.append(f"{key}={sum(r[column] for r in rows)} in {len(bad)} cases {bad[:6]}")
        print(f"{name}: " + " | ".join(summary))
    print(f"CSV: {args.output}")


if __name__ == "__main__":
    main()
