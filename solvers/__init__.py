"""Gói Solver: các thuật toán tìm kiếm dùng chung Engine API (TV3/TV4).

Mỗi module `bfs`/`dfs`/`ucs`/`astar` đều cung cấp hàm `solve(initial_state, engine)`.
Package cũng tái xuất các hàm này dưới tên thống nhất `solve_bfs`, `solve_dfs`,
`solve_ucs`, `solve_astar`.
"""

from solvers.astar import solve as solve_astar
from solvers.base_solver import finalize, path_cost, reconstruct_path
from solvers.bfs import solve as solve_bfs
from solvers.dfs import solve as solve_dfs
from solvers.search_result import SearchResult
from solvers.ucs import solve as solve_ucs

__all__ = [
    "SearchResult",
    "finalize",
    "path_cost",
    "reconstruct_path",
    "solve_astar",
    "solve_bfs",
    "solve_dfs",
    "solve_ucs",
]
