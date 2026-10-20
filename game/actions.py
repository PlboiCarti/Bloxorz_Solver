"""Định nghĩa các hành động (Action) và hướng khối (Orientation)."""

from enum import Enum


class Action(Enum):
    """Các hành động mà người chơi hoặc solver có thể thực hiện."""

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    SWITCH_CUBE = "SWITCH_CUBE"  # Chỉ hợp lệ khi đang ở chế độ split (TV2)


class Orientation(Enum):
    """Các hướng khả dĩ của khối hộp 1x1x2."""

    STANDING = "STANDING"      # Khối đứng trên 1 ô: (r, c)
    HORIZONTAL = "HORIZONTAL"  # Khối nằm ngang trên 2 ô: (r, c) và (r, c+1)
    VERTICAL = "VERTICAL"      # Khối nằm dọc trên 2 ô: (r, c) và (r+1, c)
