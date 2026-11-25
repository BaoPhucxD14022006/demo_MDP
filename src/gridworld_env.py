"""Môi trường mô phỏng GridWorld 4x4 theo chuẩn Gymnasium.

Mô phỏng bài toán MDP trên slide 09:
- 16 trạng thái rời rạc (lưới 4x4, hàng 1 ở đáy, hàng 4 ở đỉnh).
- 4 hành động: Lên (0), Xuống (1), Trái (2), Phải (3).
- Đích (4, 4) thưởng +10; Bẫy (3, 3) và (2, 3) phạt -10.
- Xác suất di chuyển: 80% đúng hướng, 10% trượt trái, 10% trượt phải.
"""

from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np


class GridWorldEnv(gym.Env):
    """Môi trường GridWorld 4x4 tuân thủ Gymnasium Env."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 10}

    # Định nghĩa chuyển dời tọa độ: (d_hàng, d_cột) với hàng 1 ở dưới cùng
    ACTION_DELTAS: dict[int, tuple[int, int]] = {
        0: (1, 0),   # Up
        1: (-1, 0),  # Down
        2: (0, -1),  # Left
        3: (0, 1),   # Right
    }

    # Hướng trượt tương đối theo hướng đi: action -> (left_action, right_action)
    SLIP_MAP: dict[int, tuple[int, int]] = {
        0: (2, 3),  # Up: trượt trái thành Left, trượt phải thành Right
        1: (3, 2),  # Down: trượt trái thành Right, trượt phải thành Left
        2: (1, 0),  # Left: trượt trái thành Down, trượt phải thành Up
        3: (0, 1),  # Right: trượt trái thành Up, trượt phải thành Down
    }

    def __init__(
        self,
        slip: float = 0.2,
        step_cost: float = -0.04,
        wall_cost: float = -0.2,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        self.n: int = 4
        self.start_cell: tuple[int, int] = (1, 1)
        self.goal_cell: tuple[int, int] = (4, 4)
        self.trap_cells: set[tuple[int, int]] = {(3, 3), (2, 3)}
        self.slip: float = slip
        self.step_cost: float = step_cost
        self.wall_cost: float = wall_cost
        self.render_mode: str | None = render_mode

        self.observation_space: spaces.Discrete = spaces.Discrete(self.n * self.n)
        self.action_space: spaces.Discrete = spaces.Discrete(4)

        # Trạng thái hiện tại dưới dạng chỉ số 0..15
        self.state_idx: int = self._to_idx(self.start_cell)
        # Bảng xác suất chuyển trạng thái P[s][a] = [(prob, next_s, reward, terminated)]
        self.P: dict[int, dict[int, list[tuple[float, int, float, bool]]]] = self._build_transition_model()

    def _to_idx(self, cell: tuple[int, int]) -> int:
        """Chuyển tọa độ (hàng, cột) 1-indexed thành chỉ số trạng thái 0-indexed."""
        r, c = cell
        return (r - 1) * self.n + (c - 1)

    def _to_cell(self, idx: int) -> tuple[int, int]:
        """Chuyển chỉ số trạng thái 0-indexed thành tọa độ (hàng, cột) 1-indexed."""
        r = (idx // self.n) + 1
        c = (idx % self.n) + 1
        return (r, c)

    def _move(self, cell: tuple[int, int], action: int) -> tuple[int, int]:
        """Tính ô kế tiếp khi thực hiện hành động, va tường thì giữ nguyên ô."""
        r, c = cell
        dr, dc = self.ACTION_DELTAS[action]
        nr, nc = r + dr, c + dc
        # Kiểm tra biên lưới 4x4
        if 1 <= nr <= self.n and 1 <= nc <= self.n:
            return (nr, nc)
        return cell

    def _build_transition_model(
        self,
    ) -> dict[int, dict[int, list[tuple[float, int, float, bool]]]]:
        """Xây dựng ma trận chuyển P[s][a] đầy đủ cho 16 trạng thái."""
        transitions: dict[int, dict[int, list[tuple[float, int, float, bool]]]] = {}
        terminal_cells = {self.goal_cell} | self.trap_cells

        for s in range(self.n * self.n):
            transitions[s] = {}
            cell = self._to_cell(s)

            # Nếu là trạng thái kết thúc (đích hoặc bẫy), robot đứng yên và giữ terminated=True
            if cell in terminal_cells:
                for a in range(4):
                    transitions[s][a] = [(1.0, s, 0.0, True)]
                continue

            # Xử lý các trạng thái bình thường
            for a in range(4):
                a_left, a_right = self.SLIP_MAP[a]
                # Danh sách (xác suất, hành động thực tế)
                outcomes: list[tuple[float, int]] = [
                    (1.0 - self.slip, a),
                    (self.slip / 2.0, a_left),
                    (self.slip / 2.0, a_right),
                ]

                # Gom nhóm các kết quả cùng dẫn tới một next_state
                merged: dict[int, list[float | float | bool]] = {}
                for prob, actual_a in outcomes:
                    r, c = cell
                    dr, dc = self.ACTION_DELTAS[actual_a]
                    nr, nc = r + dr, c + dc
                    hit_wall = not (1 <= nr <= self.n and 1 <= nc <= self.n)
                    next_cell = cell if hit_wall else (nr, nc)
                    next_s = self._to_idx(next_cell)

                    if next_cell == self.goal_cell:
                        reward = 10.0
                        terminated = True
                    elif next_cell in self.trap_cells:
                        reward = -10.0
                        terminated = True
                    else:
                        reward = self.step_cost + (self.wall_cost if hit_wall else 0.0)
                        terminated = False

                    if next_s not in merged:
                        merged[next_s] = [prob, reward, terminated]
                    else:
                        merged[next_s][0] += prob

                transitions[s][a] = [
                    (float(p), next_s, float(r), bool(term))
                    for next_s, (p, r, term) in merged.items()
                ]

        return transitions

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[int, dict]:
        """Khởi tạo lại môi trường về ô xuất phát (1, 1)."""
        super().reset(seed=seed)
        self.state_idx = self._to_idx(self.start_cell)
        return self.state_idx, {"cell": self.start_cell}

    def step(self, action: int) -> tuple[int, float, bool, bool, dict]:
        """Thực hiện một bước chuyển trạng thái theo bảng P."""
        outcomes = self.P[self.state_idx][action]
        probs = [item[0] for item in outcomes]
        choice_idx = int(self.np_random.choice(len(outcomes), p=probs))

        _, next_s, reward, terminated = outcomes[choice_idx]
        self.state_idx = next_s
        return self.state_idx, reward, terminated, False, {"cell": self._to_cell(self.state_idx)}
