"""Xuất dữ liệu mô phỏng thực nghiệm GridWorld 4x4 ra web/data.js cho demo HTML."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.gridworld_env import GridWorldEnv
from src.value_iteration import (
    PolicyIterationSolver,
    SimulationMetrics,
    ValueIterationSolver,
)

DELTA_TO_ACTION: dict[tuple[int, int], int] = {
    (1, 0): 0,   # Lên
    (-1, 0): 1,  # Xuống
    (0, -1): 2,  # Trái
    (0, 1): 3,   # Phải
}


def _round_list(arr: np.ndarray | list[float], digits: int = 4) -> list[float]:
    return [round(float(x), digits) for x in arr]


def _metrics_to_dict(m: SimulationMetrics) -> dict[str, float | int]:
    d = asdict(m)
    return {
        "episodes": int(d["episodes"]),
        "success_rate": round(float(d["success_rate"]), 4),
        "trap_rate": round(float(d["trap_rate"]), 4),
        "timeout_rate": round(float(d["timeout_rate"]), 4),
        "avg_reward": round(float(d["avg_reward"]), 4),
        "avg_steps": round(float(d["avg_steps"]), 4),
    }


def _record_episodes(
    policy: np.ndarray | None,
    n_episodes: int = 25,
    max_steps: int = 50,
    slip: float = 0.2,
    step_cost: float = -0.04,
    wall_cost: float = -0.2,
) -> list[dict]:
    """Ghi lại 25 tập mô phỏng thực tế bằng GridWorldEnv."""
    env = GridWorldEnv(slip=slip, step_cost=step_cost, wall_cost=wall_cost)
    episodes: list[dict] = []

    for i in range(n_episodes):
        s, _ = env.reset(seed=100 + i)
        rng = np.random.default_rng(1000 + i) if policy is None else None

        states: list[int] = [int(s)]
        actions: list[int] = []
        intended: list[int] = []
        total_reward = 0.0
        outcome = "timeout"

        for _ in range(max_steps):
            a = int(rng.integers(4)) if policy is None else int(policy[s])
            prev_cell = env._to_cell(s)
            next_s, r, terminated, _, info = env.step(a)
            next_cell = info["cell"]

            dr = next_cell[0] - prev_cell[0]
            dc = next_cell[1] - prev_cell[1]
            actual_a = DELTA_TO_ACTION.get((dr, dc), a)

            intended.append(a)
            actions.append(int(actual_a))
            states.append(int(next_s))
            total_reward += float(r)
            s = next_s

            if terminated:
                outcome = "goal" if next_cell == env.goal_cell else "trap"
                break

        episodes.append(
            {
                "states": states,
                "actions": actions,
                "intended": intended,
                "outcome": outcome,
                "total_reward": round(total_reward, 4),
            }
        )

    return episodes


def build_web_data() -> dict:
    """Tính toàn bộ dữ liệu thực nghiệm từ GridWorldEnv và các bộ giải DP."""
    slip = 0.2
    step_cost = -0.04
    wall_cost = -0.2
    gamma = 0.99
    theta = 1e-4

    env = GridWorldEnv(slip=slip, step_cost=step_cost, wall_cost=wall_cost)
    vi_solver = ValueIterationSolver(env.P, gamma=gamma, theta=theta)
    V_star, pi_star, vi_history, vi_deltas = vi_solver.solve()

    pi_solver = PolicyIterationSolver(env.P, gamma=gamma, theta=theta)
    _, _, pi_history = pi_solver.solve()

    # Chính sách đi tắt sát bẫy: hàng 1 đi Phải (3), các ô còn lại đi Lên (0)
    pi_risky = np.zeros(16, dtype=np.int32)
    for r in range(1, 5):
        for c in range(1, 5):
            s = (r - 1) * 4 + (c - 1)
            pi_risky[s] = 3 if (r == 1 and c < 4) else 0

    V_risky = vi_solver.evaluate_policy(pi_risky)

    # Thống kê Monte Carlo 1000 tập (cố định seed action_space để số liệu lặp lại chính xác)
    env_rand = GridWorldEnv(slip=slip, step_cost=step_cost, wall_cost=wall_cost)
    env_rand.action_space.seed(237)
    stats_random = vi_solver.simulate_policy(
        env_rand,
        None,
        n_episodes=1000,
    )
    stats_optimal = vi_solver.simulate_policy(
        GridWorldEnv(slip=slip, step_cost=step_cost, wall_cost=wall_cost),
        pi_star,
        n_episodes=1000,
    )
    stats_risky = vi_solver.simulate_policy(
        GridWorldEnv(slip=slip, step_cost=step_cost, wall_cost=wall_cost),
        pi_risky,
        n_episodes=1000,
    )

    pi_steps_json = [
        {
            "iter": int(step.iter_idx),
            "phase": str(step.phase),
            "policy": [int(a) for a in step.policy.tolist()],
            "V": _round_list(step.V),
            "eval_substeps": int(step.eval_substeps),
            "is_stable": bool(step.is_stable),
        }
        for step in pi_history
    ]
    pi_iterations = (max(s["iter"] for s in pi_steps_json) + 1) if pi_steps_json else 0

    return {
        "params": {
            "slip": slip,
            "step_cost": step_cost,
            "wall_cost": wall_cost,
            "gamma": gamma,
            "theta": theta,
            "start": [1, 1],
            "goal": [4, 4],
            "traps": [[3, 3], [2, 3]],
        },
        "vi": {
            "history": [_round_list(v) for v in vi_history],
            "deltas": [round(float(d), 6) for d in vi_deltas],
            "V_star": _round_list(V_star),
            "pi_star": [int(a) for a in pi_star.tolist()],
            "iterations": len(vi_deltas),
        },
        "pi": {
            "steps": pi_steps_json,
            "iterations": pi_iterations,
        },
        "risky": {
            "policy": [int(a) for a in pi_risky.tolist()],
            "V": _round_list(V_risky),
        },
        "stats": {
            "random": _metrics_to_dict(stats_random),
            "optimal": _metrics_to_dict(stats_optimal),
            "risky": _metrics_to_dict(stats_risky),
        },
        "episodes": {
            "random": _record_episodes(None),
            "optimal": _record_episodes(pi_star),
            "risky": _record_episodes(pi_risky),
        },
    }


def export_web_data(out_path: Path = ROOT_DIR / "web" / "data.js") -> dict:
    """Xuất dữ liệu ra file JS tĩnh để mở trực tiếp qua file://."""
    data = build_web_data()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "window.MDP_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
    out_path.write_text(payload, encoding="utf-8")
    return data


if __name__ == "__main__":
    result = export_web_data()
    print("VI iterations:", result["vi"]["iterations"])
    print("PI iterations:", result["pi"]["iterations"])
    print("V*(start):", round(result["vi"]["V_star"][0], 2))
    print("V_risky(start):", round(result["risky"]["V"][0], 2))
    print("Stats random:", result["stats"]["random"])
    print("Stats optimal:", result["stats"]["optimal"])
    print("Stats risky:", result["stats"]["risky"])
    for kind in ("random", "optimal", "risky"):
        outcomes = [ep["outcome"] for ep in result["episodes"][kind]]
        print(f"Episodes {kind}:", outcomes)
