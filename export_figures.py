"""Xuất ảnh đồ thị độ phân giải cao phục vụ chèn slide PowerPoint.

Xuất ra thư mục figures/:
1. demo1_heatmap_values.png: Bản đồ nhiệt giá trị V*(s) trên lưới 4x4.
2. demo1_policy_arrows.png: Mũi tên chính sách tối ưu pi*(s).
3. demo1_convergence.png: Đồ thị hội tụ max |Delta V| qua các vòng lặp.
4. demo1_policy_comparison.png: So sánh quỹ đạo tối ưu vs quỹ đạo sát bẫy.
5. demo2_ppo_learning_curve.png: Đồ thị phần thưởng huấn luyện PPO.
"""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from gridworld_env import GridWorldEnv
from value_iteration import ValueIterationSolver


def export_all_figures() -> None:
    """Tạo toàn bộ ảnh biểu đồ và lưu vào thư mục figures/."""
    out_dir = Path("figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # ================= 1. DEMO 1: GRIDWORLD 4x4 =================
    env = GridWorldEnv(slip=0.2, step_cost=-0.04, wall_cost=-0.2)
    solver = ValueIterationSolver(env.P, gamma=0.99, theta=1e-4)
    V, policy, history, deltas = solver.solve()

    # Chuyển đổi V thành ma trận 4x4 (Hàng 4 ở trên cùng, Hàng 1 ở đáy)
    V_grid = np.zeros((4, 4))
    for r in range(1, 5):
        for c in range(1, 5):
            s = (r - 1) * 4 + (c - 1)
            V_grid[4 - r, c - 1] = V[s]

    # --- Hình 1: Heatmap V*(s) ---
    fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
    im = ax.imshow(V_grid, cmap="YlGnBu", interpolation="nearest")
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Giá trị kỳ vọng V*(s)", fontsize=11, fontweight="bold")

    for r in range(1, 5):
        for c in range(1, 5):
            val = V_grid[4 - r, c - 1]
            label = f"{val:.2f}"
            if (r, c) == (4, 4):
                label += "\n(GOAL)"
            elif (r, c) in {(3, 3), (2, 3)}:
                label = "-10.0\n(TRAP)"
            elif (r, c) == (1, 1):
                label += "\n(START)"
            ax.text(c - 1, 4 - r, label, ha="center", va="center", color="black", fontsize=9, fontweight="bold")

    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.set_xticklabels([f"Cột {c}" for c in range(1, 5)], fontweight="bold")
    ax.set_yticklabels([f"Hàng {r}" for r in range(4, 0, -1)], fontweight="bold")
    ax.set_title("Demo 1: Bản đồ nhiệt hàm giá trị V*(s) (Value Iteration)", fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(out_dir / "demo1_heatmap_values.png")
    plt.close(fig)

    # --- Hình 2: Đồ thị hội tụ Bellman ---
    fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
    ax.plot(range(1, len(deltas) + 1), deltas, color="#0284C7", linewidth=2.2, label=r"max $|\Delta V|$")
    ax.axhline(1e-4, color="#EF4444", linestyle="--", linewidth=1.5, label=r"Ngưỡng dừng $\theta = 10^{-4}$")
    ax.set_yscale("log")
    ax.set_xlabel("Số vòng lặp Bellman (Iterations)", fontsize=10, fontweight="bold")
    ax.set_ylabel(r"Sai số cực đại $\max |V_{k+1} - V_k|$ (log scale)", fontsize=10, fontweight="bold")
    ax.set_title(f"Demo 1: Tốc độ hội tụ của Value Iteration ({len(deltas)} vòng lặp)", fontsize=11, fontweight="bold")
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(out_dir / "demo1_convergence.png")
    plt.close(fig)

    # --- Hình 3: Mũi tên chính sách tối ưu pi* ---
    fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
    ax.imshow(np.zeros((4, 4)), cmap="Blues", alpha=0.1)
    arrow_map = {0: (0, 0.35), 1: (0, -0.35), 2: (-0.35, 0), 3: (0.35, 0)}

    for r in range(1, 5):
        for c in range(1, 5):
            s = (r - 1) * 4 + (c - 1)
            cx = c - 1
            cy = 4 - r
            if (r, c) == (4, 4):
                ax.add_patch(plt.Rectangle((cx - 0.45, cy - 0.45), 0.9, 0.9, color="#10B981", alpha=0.6))
                ax.text(cx, cy, "ĐÍCH\n+10", ha="center", va="center", fontweight="bold", color="white")
            elif (r, c) in {(3, 3), (2, 3)}:
                ax.add_patch(plt.Rectangle((cx - 0.45, cy - 0.45), 0.9, 0.9, color="#EF4444", alpha=0.6))
                ax.text(cx, cy, "BẪY\n-10", ha="center", va="center", fontweight="bold", color="white")
            else:
                act = policy[s]
                dx, dy = arrow_map[act]
                # Lưu ý dy đảo chiều do trục y của đồ thị
                ax.arrow(cx, cy, dx, -dy, head_width=0.15, head_length=0.12, fc="#0284C7", ec="#0284C7", linewidth=2)
                if (r, c) == (1, 1):
                    ax.text(cx, cy + 0.35, "START", ha="center", va="center", color="#0284C7", fontweight="bold")

    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.set_xticklabels([f"Cột {c}" for c in range(1, 5)], fontweight="bold")
    ax.set_yticklabels([f"Hàng {r}" for r in range(4, 0, -1)], fontweight="bold")
    ax.set_title("Demo 1: Chính sách tối ưu π*(s) (Tự động né 2 bẫy)", fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(out_dir / "demo1_policy_arrows.png")
    plt.close(fig)

    # ================= 2. DEMO 2: PPO LEARNING CURVE =================
    steps_k = [16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 200]
    rewards = [-475.0, -470.0, 78.9, -170.5, -295.1, -107.3, 79.1, 141.4, 114.8, 141.5, 114.7, 114.8, 141.5]

    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
    ax.plot(steps_k, rewards, marker="o", color="#10B981", linewidth=2.2, label="Phần thưởng TB / tập")
    ax.axhline(0, color="gray", linestyle=":", linewidth=1)
    ax.axhline(100, color="#0284C7", linestyle="--", linewidth=1.2, label="Thưởng tới đích (+100)")
    ax.set_xlabel("Số bước huấn luyện (x 1,000 timesteps)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Phần thưởng trung bình (Episode Reward)", fontsize=10, fontweight="bold")
    ax.set_title("Demo 2: Đường cong học của Robot AMR bằng thuật toán PPO", fontsize=11, fontweight="bold")
    ax.legend(frameon=True, loc="lower right")
    plt.tight_layout()
    fig.savefig(out_dir / "demo2_ppo_learning_curve.png")
    plt.close(fig)

    print(f"Exported all 4 high-res figures to folder: {out_dir.name}")


if __name__ == "__main__":
    export_all_figures()
