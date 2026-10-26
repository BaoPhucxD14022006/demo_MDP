"""Thuật toán Value Iteration, Policy Iteration và Policy Evaluation cho GridWorld 4x4.

Bao gồm:
- ValueIterationSolver: Bellman Optimality Backup tìm V* và pi*
- PolicyIterationSolver: Luân phiên lặp Policy Evaluation và Policy Improvement
- evaluate_policy(): giải lặp V^pi cho một chính sách bất kỳ
- simulate_policy(): chạy Monte Carlo thống kê tỉ lệ tới đích, tỉ lệ rơi bẫy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import gymnasium as gym


@dataclass(slots=True)
class SimulationMetrics:
    """Chứa số liệu thống kê sau khi chạy mô phỏng N episode."""

    episodes: int
    success_rate: float
    trap_rate: float
    timeout_rate: float
    avg_reward: float
    avg_steps: float


@dataclass(slots=True)
class PolicyIterationStep:
    """Lưu trữ trạng thái một bước trong thuật toán Policy Iteration."""

    iter_idx: int
    phase: str          # "evaluation" hoặc "improvement"
    policy: np.ndarray  # mảng 16 phần tử
    V: np.ndarray       # mảng 16 phần tử
    eval_substeps: int  # số vòng lặp đánh giá giải hệ Bellman
    is_stable: bool     # đã hội tụ hay chưa
    notes: str          # ghi chú giải thích toán học


class ValueIterationSolver:
    """Bộ giải thuật toán Value Iteration trên mô hình MDP dạng bảng."""

    def __init__(
        self,
        P: dict[int, dict[int, list[tuple[float, int, float, bool]]]],
        n_states: int = 16,
        n_actions: int = 4,
        gamma: float = 0.99,
        theta: float = 1e-4,
    ) -> None:
        self.P = P
        self.n_states = n_states
        self.n_actions = n_actions
        self.gamma = gamma
        self.theta = theta

    def solve(
        self,
    ) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[float]]:
        """Chạy vòng lặp Bellman tìm V* và rút trích chính sách tối ưu pi*."""
        V = np.zeros(self.n_states, dtype=np.float64)
        history: list[np.ndarray] = [V.copy()]
        deltas: list[float] = []

        while True:
            delta = 0.0
            V_new = V.copy()

            for s in range(self.n_states):
                # Tính Q(s, a) cho từng hành động
                q_values = [
                    sum(
                        prob * (reward + self.gamma * V[next_s] * (not done))
                        for prob, next_s, reward, done in self.P[s][a]
                    )
                    for a in range(self.n_actions)
                ]
                V_new[s] = max(q_values)
                delta = max(delta, abs(V_new[s] - V[s]))

            V = V_new
            history.append(V.copy())
            deltas.append(delta)

            if delta < self.theta:
                break

        policy = self.extract_policy(V)
        return V, policy, history, deltas

    def extract_policy(self, V: np.ndarray) -> np.ndarray:
        """Rút trích chính sách tham lam (greedy policy) từ hàm giá trị V."""
        policy = np.zeros(self.n_states, dtype=np.int32)

        for s in range(self.n_states):
            q_values = [
                sum(
                    prob * (reward + self.gamma * V[next_s] * (not done))
                    for prob, next_s, reward, done in self.P[s][a]
                )
                for a in range(self.n_actions)
            ]
            policy[s] = int(np.argmax(q_values))

        return policy

    def evaluate_policy(
        self,
        policy: np.ndarray,
        theta: float = 1e-5,
    ) -> np.ndarray:
        """Tính chính xác kỳ vọng V^pi cho một chính sách cố định."""
        V = np.zeros(self.n_states, dtype=np.float64)

        while True:
            delta = 0.0
            V_new = V.copy()

            for s in range(self.n_states):
                a = int(policy[s])
                expected_v = sum(
                    prob * (reward + self.gamma * V[next_s] * (not done))
                    for prob, next_s, reward, done in self.P[s][a]
                )
                V_new[s] = expected_v
                delta = max(delta, abs(V_new[s] - V[s]))

            V = V_new
            if delta < theta:
                break

        return V

    @staticmethod
    def simulate_policy(
        env: gym.Env,
        policy: np.ndarray | None,
        n_episodes: int = 1000,
        max_steps_per_episode: int = 50,
        seed: int = 42,
    ) -> SimulationMetrics:
        """Mô phỏng Monte Carlo để đo đạc tỉ lệ thành công và phần thưởng thực tế."""
        successes = 0
        traps = 0
        timeouts = 0
        total_rewards: list[float] = []
        total_steps: list[int] = []

        for ep in range(n_episodes):
            s, _ = env.reset(seed=seed + ep)
            ep_reward = 0.0
            step_count = 0
            terminated = False

            while not terminated and step_count < max_steps_per_episode:
                action = int(env.action_space.sample()) if policy is None else int(policy[s])
                s, r, terminated, _, info = env.step(action)
                ep_reward += r
                step_count += 1

                if terminated:
                    cell = info["cell"]
                    if cell == (4, 4):
                        successes += 1
                    else:
                        traps += 1
                    break

            if not terminated:
                timeouts += 1

            total_rewards.append(ep_reward)
            total_steps.append(step_count)

        return SimulationMetrics(
            episodes=n_episodes,
            success_rate=successes / n_episodes,
            trap_rate=traps / n_episodes,
            timeout_rate=timeouts / n_episodes,
            avg_reward=float(np.mean(total_rewards)),
            avg_steps=float(np.mean(total_steps)),
        )


class PolicyIterationSolver:
    """Bộ giải thuật toán Policy Iteration (Lập chính sách) cho GridWorld 4x4.

    Gồm 2 pha luân phiên:
    1. Policy Evaluation: Đánh giá V^pi qua hệ phương trình Bellman tuyến tính.
    2. Policy Improvement: Cải tiến chính sách tham lam theo argmax Q(s, a).
    Dừng lặp khi chính sách không còn thay đổi (Policy Stable).
    """

    def __init__(
        self,
        P: dict[int, dict[int, list[tuple[float, int, float, bool]]]],
        n_states: int = 16,
        n_actions: int = 4,
        gamma: float = 0.99,
        theta: float = 1e-4,
    ) -> None:
        self.P = P
        self.n_states = n_states
        self.n_actions = n_actions
        self.gamma = gamma
        self.theta = theta

    def solve(
        self,
        initial_policy: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[PolicyIterationStep]]:
        """Chạy Policy Iteration luân phiên giữa Policy Evaluation và Policy Improvement."""
        if initial_policy is None:
            # Khởi tạo chính sách ban đầu: tất cả hành động là 0 (Lên)
            policy = np.zeros(self.n_states, dtype=np.int32)
        else:
            policy = initial_policy.copy()

        V = np.zeros(self.n_states, dtype=np.float64)
        history: list[PolicyIterationStep] = []

        iter_count = 0
        while True:
            # --- PHA 1: POLICY EVALUATION (Đánh giá chính sách) ---
            eval_substeps = 0
            while True:
                delta = 0.0
                V_new = V.copy()
                for s in range(self.n_states):
                    a = int(policy[s])
                    expected_v = sum(
                        prob * (reward + self.gamma * V[next_s] * (not done))
                        for prob, next_s, reward, done in self.P[s][a]
                    )
                    V_new[s] = expected_v
                    delta = max(delta, abs(V_new[s] - V[s]))
                V = V_new
                eval_substeps += 1
                if delta < self.theta:
                    break

            # Lưu lại trạng thái sau khi đánh giá chính sách
            history.append(
                PolicyIterationStep(
                    iter_idx=iter_count,
                    phase="evaluation",
                    policy=policy.copy(),
                    V=V.copy(),
                    eval_substeps=eval_substeps,
                    is_stable=False,
                    notes=f"Pha 1 (Đánh giá V^pi): Đánh giá chính sách hiện tại, hội tụ sau {eval_substeps} bước lặp Bellman tuyến tính.",
                )
            )

            # --- PHA 2: POLICY IMPROVEMENT (Cải tiến chính sách tham lam) ---
            policy_stable = True
            new_policy = policy.copy()

            for s in range(self.n_states):
                old_a = policy[s]
                q_values = [
                    sum(
                        prob * (reward + self.gamma * V[next_s] * (not done))
                        for prob, next_s, reward, done in self.P[s][a]
                    )
                    for a in range(self.n_actions)
                ]
                best_a = int(np.argmax(q_values))
                new_policy[s] = best_a
                if best_a != old_a:
                    policy_stable = False

            policy = new_policy
            history.append(
                PolicyIterationStep(
                    iter_idx=iter_count,
                    phase="improvement",
                    policy=policy.copy(),
                    V=V.copy(),
                    eval_substeps=eval_substeps,
                    is_stable=policy_stable,
                    notes="Pha 2 (Cải tiến): Cập nhật hướng mũi tên theo argmax Q(s, a)." if not policy_stable else "Chính sách đã ổn định hoàn toàn! Đạt chính sách tối ưu pi* tuyệt đối!",
                )
            )

            if policy_stable or iter_count >= 10:
                break

            iter_count += 1

        return V, policy, history


    @staticmethod
    def simulate_policy(
        env: gym.Env,
        policy: np.ndarray | None,
        n_episodes: int = 1000,
        max_steps_per_episode: int = 50,
        seed: int = 42,
    ) -> SimulationMetrics:
        """Mô phỏng Monte Carlo để đo đạc tỉ lệ thành công và phần thưởng thực tế."""
        successes = 0
        traps = 0
        timeouts = 0
        total_rewards: list[float] = []
        total_steps: list[int] = []

        for ep in range(n_episodes):
            s, _ = env.reset(seed=seed + ep)
            ep_reward = 0.0
            step_count = 0
            terminated = False

            while not terminated and step_count < max_steps_per_episode:
                # Nếu policy là None thì chọn ngẫu nhiên
                action = int(env.action_space.sample()) if policy is None else int(policy[s])
                s, r, terminated, _, info = env.step(action)
                ep_reward += r
                step_count += 1

                if terminated:
                    cell = info["cell"]
                    if cell == (4, 4):
                        successes += 1
                    else:
                        traps += 1
                    break

            if not terminated:
                timeouts += 1

            total_rewards.append(ep_reward)
            total_steps.append(step_count)

        return SimulationMetrics(
            episodes=n_episodes,
            success_rate=successes / n_episodes,
            trap_rate=traps / n_episodes,
            timeout_rate=timeouts / n_episodes,
            avg_reward=float(np.mean(total_rewards)),
            avg_steps=float(np.mean(total_steps)),
        )
