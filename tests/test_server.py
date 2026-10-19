"""Kiểm thử HTTP adapter (server.py) theo hợp đồng `docs/gui_api.md` §2–§3."""

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app, raise_server_exceptions=False)


@pytest.fixture
def level1(client: TestClient) -> dict:
    response = client.get("/levels/level1.json")
    assert response.status_code == 200
    return response.json()


def _replays_to_goal(client: TestClient, level: str, state: dict, path: list[str]) -> bool:
    """Phát lại đường đi qua /transition, trả về isGoal của bước cuối."""
    goal = False
    for action in path:
        response = client.post(
            "/transition", json={"level": level, "state": state, "action": action}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        state = body["state"]
        goal = body["isGoal"]
    return goal


def test_list_levels_non_empty_and_loadable(client: TestClient):
    response = client.get("/levels")
    assert response.status_code == 200
    names = response.json()
    assert "level1.json" in names
    for name in names:
        assert client.get(f"/levels/{name}").status_code == 200


def test_get_level_board_shape(level1: dict):
    board = level1["board"]
    assert board["name"] == "level1"
    assert len(board["grid"]) == board["rows"]
    assert all(len(row) == board["cols"] for row in board["grid"])
    assert board["start"] == [1, 3]
    assert board["goal"] == [4, 6]
    assert "initial_state" in level1


def test_initial_state_shape(level1: dict):
    state = level1["initial_state"]
    assert set(state) == {
        "block_position",
        "orientation",
        "occupied_cells",
        "bridge_states",
        "split_mode",
        "cube1_position",
        "cube2_position",
        "active_cube",
    }
    assert state["orientation"] == "STANDING"
    assert state["occupied_cells"] == [state["block_position"]]
    assert state["split_mode"] is False
    assert state["cube1_position"] is None
    assert state["cube2_position"] is None
    assert state["active_cube"] is None


def test_transition_ok(client: TestClient, level1: dict):
    response = client.post(
        "/transition",
        json={
            "level": "level1.json",
            "state": level1["initial_state"],
            "action": "RIGHT",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["isGoal"] is False
    assert body["reason"] is None
    assert body["state"]["occupied_cells"] == [[1, 4], [1, 5]]


def test_transition_illegal_keeps_state_null(client: TestClient, level1: dict):
    response = client.post(
        "/transition",
        json={
            "level": "level1.json",
            "state": level1["initial_state"],
            "action": "SWITCH_CUBE",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "illegal"
    assert body["state"] is None
    assert body["reason"] == "switch_cube_not_split"


def test_solve_bfs_schema_and_replay(client: TestClient, level1: dict):
    response = client.post(
        "/solve",
        json={"level": "level1.json", "algorithm": "BFS", "state": level1["initial_state"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["solved"] is True
    assert body["solution_length"] == len(body["path"])
    assert body["total_cost"] > 0
    assert all(isinstance(n, (int, float)) for n in (body["search_time"], body["memory_usage"]))
    assert _replays_to_goal(client, "level1.json", level1["initial_state"], body["path"]) is True


@pytest.mark.parametrize(
    ("method", "path", "payload", "status", "code"),
    [
        ("get", "/levels/nope.json", None, 404, "LEVEL_NOT_FOUND"),
        ("get", "/does-not-exist", None, 404, "NOT_FOUND"),
        (
            "post",
            "/solve",
            {"level": "level1.json", "algorithm": "NOPE", "state": {}},
            400,
            "UNKNOWN_ALGORITHM",
        ),
        (
            "post",
            "/transition",
            {"level": "level1.json", "state": {}, "action": "TELEPORT"},
            400,
            "INVALID_ACTION",
        ),
    ],
)
def test_error_contract(client: TestClient, method, path, payload, status, code):
    response = getattr(client, method)(path, json=payload) if payload else getattr(client, method)(path)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
