"""Giao diện minh họa Pygame cho Demo 1: GridWorld 4x4, Value Iteration & Policy Iteration.

Bao gồm:
1. Vẽ mũi tên vector sắc nét (draw_vector_arrow), không dùng ký tự bàn phím (^, v, <, >) tránh nhầm chữ.
2. Thiết lập DPI awareness tránh mờ chữ trên màn hình độ phân giải cao.
3. Tab 1: Mô hình ban đầu (không hiển thị V hay mũi tên).
4. Tab 2: Agent ngẫu nhiên đi lang thang và rơi bẫy.
5. Tab 3: Quy hoạch động gồm 2 thuật toán:
   - 1. Value Iteration (Lập giá trị tối ưu Bellman Backup, 48 vòng lặp)
   - 2. Policy Iteration (Lập chính sách: Luân phiên Evaluation & Improvement, hội tụ sau 2-3 vòng)
6. Tab 4: Rút trích chính sách pi*(s) (chỉ hiển thị mũi tên vector và Robot chạy theo đường tối ưu, loại bỏ số V gây rối).
7. Tab 5: So sánh đối chiếu trực tiếp HAI MA TRẬN 4x4 CẠNH NHAU (Ma trận Tối ưu vs Ma trận Sát bẫy) kèm bảng phân tích và mô phỏng đua song song.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pygame

# Thiết lập DPI awareness trên Windows để font chữ sắc nét
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from gridworld_env import GridWorldEnv
from value_iteration import (
    ValueIterationSolver,
    PolicyIterationSolver,
    PolicyIterationStep,
    SimulationMetrics,
)


# ===================== BẢNG MÀU DARK SLATE =====================
BG_DARK = (15, 23, 42)          # Nền chính #0F172A
PANEL_BG = (30, 41, 59)         # Nền card panel #1E293B
PANEL_BORDER = (51, 65, 85)     # Viền panel #334155
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
TEXT_HIGHLIGHT = (56, 189, 248) # Cyan sáng

CELL_NORMAL = (30, 41, 59)
CELL_BORDER = (71, 85, 105)
START_COLOR = (2, 132, 199)     # Xanh dương Start #0284C7
GOAL_COLOR = (16, 185, 129)     # Xanh lá Đích #10B981
TRAP_COLOR = (239, 68, 68)      # Đỏ Bẫy #EF4444
AGENT_COLOR = (245, 158, 11)    # Vàng Hổ phách #F59E0B
TRAIL_COLOR = (56, 189, 248)    # Cyan đường đi
TRAIL_RISKY = (244, 63, 94)     # Đỏ đường sát bẫy

BTN_NORMAL = (51, 65, 85)
BTN_HOVER = (71, 85, 105)
BTN_ACTIVE = (2, 132, 199)


def draw_vector_arrow(
    surface: pygame.Surface,
    center: tuple[int, int],
    direction: int,
    color: tuple[int, int, int],
    length: int = 15,
    head_size: int = 6,
) -> None:
    """Vẽ mũi tên vector chỉ hướng hình học sắc nét (0: Lên, 1: Xuống, 2: Trái, 3: Phải)."""
    cx, cy = center
    dx_map = {0: 0, 1: 0, 2: -1, 3: 1}
    dy_map = {0: -1, 1: 1, 2: 0, 3: 0}
    dx = dx_map[direction]
    dy = dy_map[direction]

    start_pos = (cx - dx * length, cy - dy * length)
    end_pos = (cx + dx * length, cy + dy * length)
    pygame.draw.line(surface, color, start_pos, end_pos, width=3)

    if dx == 0:
        p1 = end_pos
        p2 = (end_pos[0] - head_size, end_pos[1] - dy * head_size)
        p3 = (end_pos[0] + head_size, end_pos[1] - dy * head_size)
    else:
        p1 = end_pos
        p2 = (end_pos[0] - dx * head_size, end_pos[1] - head_size)
        p3 = (end_pos[0] - dx * head_size, end_pos[1] + head_size)
    pygame.draw.polygon(surface, color, [p1, p2, p3])


@dataclass(slots=True)
class Button:
    """Nút bấm tương tác trên giao diện."""

    rect: pygame.Rect
    text: str
    tag: str
    is_active: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]) -> None:
        """Vẽ nút với hiệu ứng hover và active."""
        if self.is_active:
            bg_col = BTN_ACTIVE
        elif self.rect.collidepoint(mouse_pos):
            bg_col = BTN_HOVER
        else:
            bg_col = BTN_NORMAL

        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=1, border_radius=6)

        text_surf = font.render(self.text, True, TEXT_WHITE)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))


class GridWorldView:
    """View hiển thị toàn bộ nội dung của Demo 1: GridWorld 4x4."""

    def __init__(self, screen: pygame.Surface, width: int = 1280, height: int = 780) -> None:
        self.screen = screen
        self.width = width
        self.height = height

        # Nạp font chữ Segoe UI / Arial chuẩn hiển thị tiếng Việt sắc nét không bị lỗi
        self.title_font = pygame.font.SysFont("segoe ui, arial", 20, bold=True)
        self.bold_font = pygame.font.SysFont("segoe ui, arial", 14, bold=True)
        self.regular_font = pygame.font.SysFont("segoe ui, arial", 13)
        self.small_font = pygame.font.SysFont("segoe ui, arial", 11)
        self.mini_font = pygame.font.SysFont("segoe ui, arial", 10)

        # Môi trường Gymnasium (phạt va tường -0.2 để ô (4,3) chọn Phải về đích)
        self.slip = 0.2
        self.env = GridWorldEnv(slip=self.slip, step_cost=-0.04, wall_cost=-0.2)

        # Thuật toán 1: Value Iteration
        self.solver = ValueIterationSolver(self.env.P, gamma=0.99, theta=1e-4)
        self.V_star, self.pi_star, self.history, self.deltas = self.solver.solve()

        # Thuật toán 2: Policy Iteration (Lập chính sách)
        self.pi_solver = PolicyIterationSolver(self.env.P, gamma=0.99, theta=1e-4)
        self.V_pi, self.pi_opt, self.pi_history = self.pi_solver.solve()

        # Chế độ thuật toán ở Tab 3: "VI" (Value Iteration) hoặc "PI" (Policy Iteration)
        self.dp_algo_mode: str = "VI"
        self.pi_step_idx: int = 0

        # Nút chuyển đổi thuật toán trong Tab 3
        self.btn_mode_vi = Button(pygame.Rect(565, 120, 310, 34), "1. Value Iteration (Lập giá trị)", "set_vi", is_active=True)
        self.btn_mode_pi = Button(pygame.Rect(895, 120, 335, 34), "2. Policy Iteration (Lập chính sách)", "set_pi", is_active=False)

        # Tính chính sách "Đi sát bẫy" (Risky policy): dọc hàng 1 rồi lên cột 4
        self.pi_risky = np.zeros(16, dtype=np.int32)
        for r in range(1, 5):
            for c in range(1, 5):
                s = (r - 1) * 4 + (c - 1)
                if r == 1 and c < 4:
                    self.pi_risky[s] = 3  # Phải
                else:
                    self.pi_risky[s] = 0  # Lên

        self.V_risky = self.solver.evaluate_policy(self.pi_risky)

        # Chạy trước mô phỏng Monte Carlo 1000 tập
        self.stats_rand = self.solver.simulate_policy(self.env, None, n_episodes=1000)
        self.stats_opt = self.solver.simulate_policy(self.env, self.pi_star, n_episodes=1000)
        self.stats_risky = self.solver.simulate_policy(self.env, self.pi_risky, n_episodes=1000)

        # Trạng thái giao diện (5 giai đoạn tinh gọn)
        self.current_phase: int = 1
        self.is_paused: bool = False
        self.sim_speed: int = 4
        self.last_step_time: int = 0
        self.vi_iter_idx: int = len(self.history) - 1

        # Trạng thái mô phỏng Agent cho Tab 1, 2, 4
        self.agent_state: int = self.env._to_idx((1, 1))
        self.agent_path: list[tuple[int, int]] = [(1, 1)]
        self.agent_reward_sum: float = 0.0
        self.agent_step_count: int = 0
        self.agent_status: str = "Đang chạy..."
        self.agent_last_action_name: str = "Xuất phát"
        self.episodes_run: int = 0
        self.ep_success: int = 0
        self.ep_trap: int = 0

        # Mô phỏng song song cho Tab 5 (Đua cả 2 robot cùng lúc)
        self.tab5_env_opt = GridWorldEnv(slip=self.slip, step_cost=-0.04, wall_cost=-0.2)
        self.tab5_env_risky = GridWorldEnv(slip=self.slip, step_cost=-0.04, wall_cost=-0.2)
        self.tab5_opt_state, _ = self.tab5_env_opt.reset()
        self.tab5_risky_state, _ = self.tab5_env_risky.reset()
        self.tab5_opt_path: list[tuple[int, int]] = [(1, 1)]
        self.tab5_risky_path: list[tuple[int, int]] = [(1, 1)]
        self.tab5_opt_status: str = "Đang chạy..."
        self.tab5_risky_status: str = "Đang chạy..."

        # Tọa độ và kích thước bàn cờ đơn 4x4 (dùng cho Tab 1, 2, 3, 4)
        self.grid_x = 40
        self.grid_y = 120
        self.grid_size = 480
        self.cell_size = self.grid_size // 4

        # Thiết lập 5 tab trên đúng 1 hàng duy nhất
        self.tabs: list[Button] = []
        tab_titles = [
            "1. Mô hình MDP",
            "2. Agent ngẫu nhiên",
            "3. Quy hoạch động (VI / PI)",
            "4. Chính sách tối ưu (pi*)",
            "5. So sánh 2 chính sách",
        ]
        tab_w = 175
        tab_h = 36
        for i, title in enumerate(tab_titles):
            tx = 40 + i * (tab_w + 12)
            ty = 60
            self.tabs.append(Button(pygame.Rect(tx, ty, tab_w, tab_h), title, f"phase_{i+1}", is_active=(i == 0)))

        # Nút điều khiển đặt gọn gàng phía dưới bàn cờ
        ctrl_y = 660
        self.btn_play = Button(pygame.Rect(40, ctrl_y, 110, 38), "Tạm dừng", "toggle_play")
        self.btn_step = Button(pygame.Rect(160, ctrl_y, 100, 38), "Bước tiếp", "step")
        self.btn_reset = Button(pygame.Rect(270, ctrl_y, 100, 38), "Đặt lại (R)", "reset")
        self.btn_speed = Button(pygame.Rect(380, ctrl_y, 110, 38), "Tốc độ: 2x", "speed")

    def set_phase(self, phase: int) -> None:
        """Chuyển đổi giữa 5 giai đoạn thuyết trình."""
        self.current_phase = phase
        for i, tab in enumerate(self.tabs):
            tab.is_active = (i + 1 == phase)

        if phase == 3:
            self.vi_iter_idx = 0
            self.pi_step_idx = 0
        else:
            self.vi_iter_idx = len(self.history) - 1
            self.pi_step_idx = len(self.pi_history) - 1

        self.reset_agent()

    def reset_agent(self) -> None:
        """Đặt lại vị trí của robot về ô Start cho tất cả các tab."""
        self.agent_state, _ = self.env.reset()
        self.agent_path = [(1, 1)]
        self.agent_reward_sum = 0.0
        self.agent_step_count = 0
        self.agent_status = "Đang chạy..."
        self.agent_last_action_name = "Xuất phát"

        # Đặt lại mô phỏng cho Tab 5
        self.tab5_opt_state, _ = self.tab5_env_opt.reset()
        self.tab5_risky_state, _ = self.tab5_env_risky.reset()
        self.tab5_opt_path = [(1, 1)]
        self.tab5_risky_path = [(1, 1)]
        self.tab5_opt_status = "Đang chạy..."
        self.tab5_risky_status = "Đang chạy..."

    def step_simulation(self) -> None:
        """Thực hiện một bước mô phỏng robot theo chính sách tương ứng."""
        if self.current_phase == 5:
            # Mô phỏng song song 2 robot trên 2 ma trận ở Tab 5
            if self.tab5_opt_status == "Đang chạy...":
                a_opt = int(self.pi_star[self.tab5_opt_state])
                next_s, _, term, _, info = self.tab5_env_opt.step(a_opt)
                self.tab5_opt_state = next_s
                self.tab5_opt_path.append(info["cell"])
                if term:
                    self.tab5_opt_status = "THÀNH CÔNG! (+10)" if info["cell"] == (4, 4) else "RƠI BẪY! (-10)"

            if self.tab5_risky_status == "Đang chạy...":
                a_risky = int(self.pi_risky[self.tab5_risky_state])
                next_s, _, term, _, info = self.tab5_env_risky.step(a_risky)
                self.tab5_risky_state = next_s
                self.tab5_risky_path.append(info["cell"])
                if term:
                    self.tab5_risky_status = "THÀNH CÔNG! (+10)" if info["cell"] == (4, 4) else "RƠI BẪY! (-10)"
            return

        if self.agent_status != "Đang chạy...":
            return

        if self.current_phase == 2:
            action = int(self.env.action_space.sample())
        elif self.current_phase == 4:
            action = int(self.pi_star[self.agent_state])
        else:
            return

        action_names = {0: "Lên", 1: "Xuống", 2: "Trái", 3: "Phải"}
        self.agent_last_action_name = action_names.get(action, "")

        next_s, reward, terminated, _, info = self.env.step(action)
        self.agent_state = next_s
        cell = info["cell"]
        self.agent_path.append(cell)
        self.agent_reward_sum += reward
        self.agent_step_count += 1

        if terminated:
            self.episodes_run += 1
            if cell == (4, 4):
                self.agent_status = "TỚI ĐÍCH THÀNH CÔNG! (+10)"
                self.ep_success += 1
            else:
                self.agent_status = "RƠI VÀO BẪY NGUY HIỂM! (-10)"
                self.ep_trap += 1
        elif self.agent_step_count >= 50:
            self.agent_status = "Hết số bước tối đa (50 bước)"

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> None:
        """Xử lý sự kiện bàn phím và chuột trong Demo 1."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused
                self.btn_play.text = "Tiếp tục" if self.is_paused else "Tạm dừng"
            elif event.key == pygame.K_r:
                self.reset_agent()
                if self.current_phase == 3:
                    self.vi_iter_idx = 0
                    self.pi_step_idx = 0
            elif event.key == pygame.K_n:
                if self.current_phase == 3:
                    if self.dp_algo_mode == "VI":
                        self.vi_iter_idx = min(len(self.history) - 1, self.vi_iter_idx + 1)
                    else:
                        self.pi_step_idx = min(len(self.pi_history) - 1, self.pi_step_idx + 1)
                else:
                    self.step_simulation()
            elif pygame.K_1 <= event.key <= pygame.K_5:
                self.set_phase(event.key - pygame.K_0)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, tab in enumerate(self.tabs):
                if tab.rect.collidepoint(mouse_pos):
                    self.set_phase(i + 1)
                    return

            # Xử lý bấm nút chuyển đổi thuật toán ở Tab 3
            if self.current_phase == 3:
                if self.btn_mode_vi.rect.collidepoint(mouse_pos):
                    self.dp_algo_mode = "VI"
                    self.btn_mode_vi.is_active = True
                    self.btn_mode_pi.is_active = False
                    return
                elif self.btn_mode_pi.rect.collidepoint(mouse_pos):
                    self.dp_algo_mode = "PI"
                    self.btn_mode_vi.is_active = False
                    self.btn_mode_pi.is_active = True
                    return

            if self.btn_play.rect.collidepoint(mouse_pos):
                self.is_paused = not self.is_paused
                self.btn_play.text = "Tiếp tục" if self.is_paused else "Tạm dừng"
            elif self.btn_step.rect.collidepoint(mouse_pos):
                if self.current_phase == 3:
                    if self.dp_algo_mode == "VI":
                        self.vi_iter_idx = min(len(self.history) - 1, self.vi_iter_idx + 1)
                    else:
                        self.pi_step_idx = min(len(self.pi_history) - 1, self.pi_step_idx + 1)
                else:
                    self.step_simulation()
            elif self.btn_reset.rect.collidepoint(mouse_pos):
                self.reset_agent()
                if self.current_phase == 3:
                    self.vi_iter_idx = 0
                    self.pi_step_idx = 0
            elif self.btn_speed.rect.collidepoint(mouse_pos):
                if self.sim_speed == 2:
                    self.sim_speed = 4
                    self.btn_speed.text = "Tốc độ: 2x"
                elif self.sim_speed == 4:
                    self.sim_speed = 8
                    self.btn_speed.text = "Tốc độ: 4x"
                else:
                    self.sim_speed = 2
                    self.btn_speed.text = "Tốc độ: 1x"

    def update(self, current_time: int) -> None:
        """Cập nhật trạng thái mô phỏng theo FPS."""
        step_interval = 1000 // self.sim_speed
        if not self.is_paused and (current_time - self.last_step_time > step_interval):
            if self.current_phase in (2, 4):
                if self.agent_status == "Đang chạy...":
                    self.step_simulation()
                else:
                    if current_time - self.last_step_time > 1500:
                        self.reset_agent()
            elif self.current_phase == 3:
                if self.dp_algo_mode == "VI":
                    if self.vi_iter_idx < len(self.history) - 1:
                        self.vi_iter_idx += 1
                else:
                    if self.pi_step_idx < len(self.pi_history) - 1:
                        self.pi_step_idx += 1
            elif self.current_phase == 5:
                if self.tab5_opt_status == "Đang chạy..." or self.tab5_risky_status == "Đang chạy...":
                    self.step_simulation()
                else:
                    if current_time - self.last_step_time > 2000:
                        self.reset_agent()
            self.last_step_time = current_time

    def draw(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ toàn bộ nội dung của Demo 1 lên màn hình."""
        self._draw_tabs(mouse_pos)

        # Tab 5 đặc biệt: Vẽ 2 ma trận so sánh cạnh nhau
        if self.current_phase == 5:
            self._draw_two_matrices_comparison(mouse_pos)
        else:
            self._draw_single_grid()
            self._draw_right_dashboard(mouse_pos)
            self._draw_controls(mouse_pos)

    def _draw_tabs(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ thanh công cụ 5 tab trên 1 hàng duy nhất."""
        for tab in self.tabs:
            tab.draw(self.screen, self.bold_font, mouse_pos)

    def _draw_single_grid(self) -> None:
        """Vẽ ma trận đơn 4x4 dùng cho các Tab 1, 2, 3, 4."""
        panel_rect = pygame.Rect(self.grid_x - 10, self.grid_y - 10, self.grid_size + 20, self.grid_size + 20)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel_rect, width=2, border_radius=12)

        if self.current_phase == 3:
            if self.dp_algo_mode == "VI":
                current_V = self.history[self.vi_iter_idx]
            else:
                cur_pi_step = self.pi_history[self.pi_step_idx]
                current_V = cur_pi_step.V
        else:
            current_V = self.V_star

        for r in range(1, 5):
            for c in range(1, 5):
                draw_x = self.grid_x + (c - 1) * self.cell_size
                draw_y = self.grid_y + (4 - r) * self.cell_size
                cell_rect = pygame.Rect(draw_x, draw_y, self.cell_size, self.cell_size)

                s = (r - 1) * 4 + (c - 1)
                is_start = (r, c) == (1, 1)
                is_goal = (r, c) == (4, 4)
                is_trap = (r, c) in {(3, 3), (2, 3)}

                if is_goal:
                    bg_col = GOAL_COLOR
                elif is_trap:
                    bg_col = TRAP_COLOR
                elif is_start:
                    bg_col = START_COLOR
                elif self.current_phase == 3:
                    # Bản đồ nhiệt ở Tab 3: màu sắc biến đổi theo giá trị V
                    v_val = current_V[s]
                    norm = max(0.0, min(1.0, (v_val - 0.0) / 10.0))
                    bg_col = (
                        int(30 + norm * 20),
                        int(41 + norm * 120),
                        int(59 + norm * 150),
                    )
                else:
                    bg_col = CELL_NORMAL

                pygame.draw.rect(self.screen, bg_col, cell_rect)
                pygame.draw.rect(self.screen, CELL_BORDER, cell_rect, width=1)

                coord_text = self.small_font.render(f"({r},{c})", True, (148, 163, 184))
                self.screen.blit(coord_text, (draw_x + 6, draw_y + 4))

                if is_start:
                    txt = self.bold_font.render("START", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + self.cell_size // 2, draw_y + 24)))
                elif is_goal:
                    txt = self.bold_font.render("ĐÍCH (+10)", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + self.cell_size // 2, draw_y + 36)))
                elif is_trap:
                    txt = self.bold_font.render("BẪY (-10)", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + self.cell_size // 2, draw_y + 36)))

                # CHỈ HIỂN THỊ GIÁ TRỊ V Ở TAB 3
                if self.current_phase == 3:
                    v_val = current_V[s]
                    v_text = self.bold_font.render(f"V={v_val:.2f}", True, (254, 240, 138) if not (is_goal or is_trap) else TEXT_WHITE)
                    self.screen.blit(v_text, v_text.get_rect(center=(draw_x + self.cell_size // 2, draw_y + self.cell_size - 22)))

                # Ở Tab 3 chế độ Policy Iteration: VẼ MŨI TÊN CHÍNH SÁCH pi_k(s) TRỰC QUAN!
                if self.current_phase == 3 and self.dp_algo_mode == "PI" and not (is_goal or is_trap):
                    cur_pi_step = self.pi_history[self.pi_step_idx]
                    action = cur_pi_step.policy[s]
                    arrow_y = draw_y + self.cell_size // 2 + (8 if is_start else 0)
                    arrow_center = (draw_x + self.cell_size // 2, arrow_y)
                    draw_vector_arrow(self.screen, arrow_center, action, (56, 189, 248), length=16, head_size=7)

                # CHỈ HIỂN THỊ MŨI TÊN VECTOR Ở TAB 4 (Rút trích chính sách pi*)
                if self.current_phase == 4 and not (is_goal or is_trap):
                    action = self.pi_star[s]
                    arrow_y = draw_y + self.cell_size // 2 + (12 if is_start else 0)
                    arrow_center = (draw_x + self.cell_size // 2, arrow_y)
                    draw_vector_arrow(self.screen, arrow_center, action, (255, 255, 255), length=16, head_size=7)

        # Vẽ đường quỹ đạo ở Tab 2 hoặc Tab 4
        if len(self.agent_path) > 1 and self.current_phase in (2, 4):
            points = [
                (
                    self.grid_x + (c - 1) * self.cell_size + self.cell_size // 2,
                    self.grid_y + (4 - r) * self.cell_size + self.cell_size // 2,
                )
                for (r, c) in self.agent_path
            ]
            pygame.draw.lines(self.screen, TRAIL_COLOR, False, points, width=3)

        # Vẽ Robot Agent ở Tab 1, 2, 4 (TUYỆT ĐỐI KHÔNG vẽ ở Tab 3 để nhấn mạnh Tab 3 là tính toán Bellman offline)
        if self.current_phase in (1, 2, 4):
            cur_r, cur_c = self.agent_path[-1]
            center_x = self.grid_x + (cur_c - 1) * self.cell_size + self.cell_size // 2
            center_y = self.grid_y + (4 - cur_r) * self.cell_size + self.cell_size // 2
            pygame.draw.circle(self.screen, AGENT_COLOR, (center_x, center_y), 19)
            pygame.draw.circle(self.screen, TEXT_WHITE, (center_x, center_y), 19, width=2)
            pygame.draw.circle(self.screen, (15, 23, 42), (center_x, center_y), 9)
            pygame.draw.circle(self.screen, (56, 189, 248), (center_x, center_y), 4)

    def _draw_right_dashboard(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ bảng thông tin chi tiết bên phải cho Tab 1, 2, 3, 4."""
        dash_x = 555
        dash_y = 120
        dash_w = 685
        dash_h = 585

        panel_rect = pygame.Rect(dash_x, dash_y, dash_w, dash_h)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel_rect, width=2, border_radius=12)

        if self.current_phase == 3:
            self._draw_info_phase3(dash_x + 20, dash_y + 16, mouse_pos)
            return

        phase_names = [
            "Giai đoạn 1: Mô hình hóa MDP (Slide 09/12)",
            "Giai đoạn 2: Agent ngẫu nhiên thất bại (Tạo vấn đề)",
            "Giai đoạn 3: Quy hoạch động (Value Iteration vs Policy Iteration)",
            "Giai đoạn 4: Chính sách tối ưu pi*(s) & Mô phỏng đường đi",
        ]
        title_surf = self.title_font.render(phase_names[self.current_phase - 1], True, TEXT_HIGHLIGHT)
        self.screen.blit(title_surf, (dash_x + 24, dash_y + 20))

        info_y = dash_y + 65
        if self.current_phase == 1:
            self._draw_info_phase1(dash_x + 24, info_y)
        elif self.current_phase == 2:
            self._draw_info_phase2(dash_x + 24, info_y)
        elif self.current_phase == 4:
            self._draw_info_phase4(dash_x + 24, info_y)

    def _draw_info_phase1(self, x: int, y: int) -> None:
        """Chi tiết thông số 4 thành phần MDP."""
        lines = [
            ("Không gian trạng thái S:", "16 ô lưới rời rạc (Hàng 1..4, Cột 1..4). Hàng 1 ở đáy, Hàng 4 ở đỉnh."),
            ("Không gian hành động A:", "4 hành động cơ bản: {Lên (0), Xuống (1), Trái (2), Phải (3)}"),
            ("Hàm phần thưởng R(s, a):", "Đích (4,4): +10.0 | Bẫy (3,3) & (2,3): -10.0 | Mỗi bước đi: -0.04"),
            ("Động lực ngẫu nhiên P:", "80% đi đúng hướng; 10% trượt sang trái; 10% trượt sang phải."),
            ("Điều kiện biên & Va tường:", "Va vào tường giới hạn sẽ đứng yên tại chỗ và chịu phạt va chạm (-0.2)."),
            ("Hệ số chiết khấu gamma:", "gamma = 0.99 (Ưu tiên tối đa hóa phần thưởng dài hạn tới khi về đích)."),
            ("Mục tiêu bài toán:", "Tìm chính sách pi* tối ưu hóa tổng phần thưởng kỳ vọng tích lũy."),
        ]
        for i, (label, val) in enumerate(lines):
            card_r = pygame.Rect(x, y + i * 54, 635, 44)
            pygame.draw.rect(self.screen, (20, 29, 44), card_r, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, card_r, width=1, border_radius=6)

            lbl_s = self.bold_font.render(label, True, (56, 189, 248))
            val_s = self.regular_font.render(val, True, TEXT_WHITE)
            self.screen.blit(lbl_s, (x + 14, y + i * 54 + 13))
            self.screen.blit(val_s, (x + 225, y + i * 54 + 13))

    def _draw_info_phase2(self, x: int, y: int) -> None:
        """Chi tiết thống kê Agent ngẫu nhiên."""
        lbl = self.bold_font.render("KẾT QUẢ KIỂM CHỨNG MONTE CARLO (1000 EPISODES):", True, (248, 113, 113))
        self.screen.blit(lbl, (x, y))

        data = [
            ("Tỉ lệ tới đích thành công:", f"{self.stats_rand.success_rate*100:.1f}% (Thất bại gần như hoàn toàn)"),
            ("Tỉ lệ rơi vào bẫy tử thần:", f"{self.stats_rand.trap_rate*100:.1f}% (Rơi bẫy do không có chính sách)"),
            ("Phần thưởng tích lũy TB / tập:", f"{self.stats_rand.avg_reward:.2f} (Điểm số âm rất nặng)"),
            ("Số bước di chuyển trung bình:", f"{self.stats_rand.avg_steps:.1f} bước"),
            ("Hành động bước vừa rồi:", f"{self.agent_last_action_name}"),
            ("Trạng thái hiện tại của Robot:", f"{self.agent_status}"),
        ]
        for i, (k, v) in enumerate(data):
            card_r = pygame.Rect(x, y + 36 + i * 52, 635, 42)
            pygame.draw.rect(self.screen, (20, 29, 44), card_r, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, card_r, width=1, border_radius=6)

            k_s = self.bold_font.render(k, True, TEXT_MUTED)
            v_s = self.bold_font.render(v, True, TEXT_WHITE)
            self.screen.blit(k_s, (x + 14, y + 36 + i * 52 + 12))
            self.screen.blit(v_s, (x + 260, y + 36 + i * 52 + 12))

        concl = self.regular_font.render("=> Nhận xét: Hành vi ngẫu nhiên thất bại hoàn toàn. Cần thuật toán Quy hoạch động để tối ưu!", True, (251, 191, 36))
        self.screen.blit(concl, (x, y + 365))

    def _draw_info_phase3(self, x: int, y: int, mouse_pos: tuple[int, int]) -> None:
        """Chi tiết tiến trình Quy hoạch động: Lựa chọn Value Iteration hoặc Policy Iteration."""
        # 2 Nút chuyển đổi thuật toán
        self.btn_mode_vi.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_mode_pi.draw(self.screen, self.bold_font, mouse_pos)

        content_y = y + 46
        if self.dp_algo_mode == "VI":
            self._draw_info_vi(x, content_y)
        else:
            self._draw_info_pi(x, content_y)

    def _draw_info_vi(self, x: int, y: int) -> None:
        """Chi tiết thuật toán Value Iteration theo slide thuyết trình."""
        title = self.bold_font.render("1. THUẬT TOÁN VALUE ITERATION (LẬP GIÁ TRỊ TỐI ƯU)", True, (254, 240, 138))
        self.screen.blit(title, (x, y))

        cur_delta = self.deltas[self.vi_iter_idx - 1] if self.vi_iter_idx > 0 else self.deltas[0]
        rows = [
            ("Vòng lặp Bellman hiện tại:", f"Iteration {self.vi_iter_idx} / {len(self.history) - 1}"),
            ("Sai số hội tụ cực đại max |delta V|:", f"{cur_delta:.6f}"),
            ("Ngưỡng dừng thuật toán theta:", "1e-4 (0.0001)"),
            ("Tổng số vòng lặp để hội tụ hoàn toàn:", f"{len(self.deltas)} vòng lặp"),
            ("Giá trị kỳ vọng V*(Start) hiện thời:", f"{self.history[self.vi_iter_idx][0]:.3f}"),
        ]
        for i, (k, v) in enumerate(rows):
            card_r = pygame.Rect(x, y + 26 + i * 36, 640, 30)
            pygame.draw.rect(self.screen, (20, 29, 44), card_r, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, card_r, width=1, border_radius=6)

            k_s = self.bold_font.render(k, True, TEXT_MUTED)
            v_s = self.bold_font.render(v, True, TEXT_WHITE)
            self.screen.blit(k_s, (x + 14, y + 26 + i * 36 + 6))
            self.screen.blit(v_s, (x + 280, y + 26 + i * 36 + 6))

        # Khung lý thuyết theo slide bài giảng
        box_y = y + 218
        note_box = pygame.Rect(x, box_y, 640, 185)
        pygame.draw.rect(self.screen, (15, 23, 42), note_box, border_radius=8)
        pygame.draw.rect(self.screen, (254, 240, 138), note_box, width=1, border_radius=8)

        n1 = self.bold_font.render("[TOÁN TỬ CẬP NHẬT BELLMAN OPTIMALITY BACKUP]:", True, (254, 240, 138))
        n2 = self.regular_font.render("• Công thức: V_{k+1}(s) <- max_a [ R(s, a) + gamma * sum P(s'|s,a) V_k(s') ]", True, (56, 189, 248))
        n3 = self.regular_font.render("• Không cần giải hệ phương trình chính sách; cập nhật đồng loạt mảng giá trị sau mỗi bước.", True, TEXT_WHITE)
        n4 = self.regular_font.render("• Điều kiện dừng: ||V_{k+1} - V_k|| < theta. Trích xuất chính sách pi* 1 lần duy nhất bằng argmax.", True, TEXT_WHITE)
        n5 = self.bold_font.render("★ Đặc điểm: Cần nhiều vòng lặp nhỏ hơn (48 vòng), nhưng tính toán mỗi bước cực kỳ nhanh!", True, (52, 211, 153))
        self.screen.blit(n1, (x + 14, box_y + 12))
        self.screen.blit(n2, (x + 14, box_y + 40))
        self.screen.blit(n3, (x + 14, box_y + 70))
        self.screen.blit(n4, (x + 14, box_y + 100))
        self.screen.blit(n5, (x + 14, box_y + 140))

        tip = self.regular_font.render("(*) Bấm 'Bước tiếp' (hoặc phím N) để xem giá trị lan truyền từng vòng lặp Bellman.", True, (56, 189, 248))
        self.screen.blit(tip, (x, box_y + 200))

    def _draw_info_pi(self, x: int, y: int) -> None:
        """Chi tiết thuật toán Policy Iteration theo slide thuyết trình."""
        title = self.bold_font.render("2. THUẬT TOÁN POLICY ITERATION (LẬP CHÍNH SÁCH)", True, (56, 189, 248))
        self.screen.blit(title, (x, y))

        cur_step = self.pi_history[self.pi_step_idx]
        phase_name = "Pha 1: Policy Evaluation (Đánh giá V^pi)" if cur_step.phase == "evaluation" else "Pha 2: Policy Improvement (Cải tiến tham lam)"
        stable_status = "Chính sách ĐÃ ỔN ĐỊNH (Hội tụ tối ưu pi*)!" if cur_step.is_stable else "Đang cập nhật hướng mũi tên tham lam..."

        rows = [
            ("Bước thực thi Policy Iteration:", f"Bước {self.pi_step_idx + 1} / {len(self.pi_history)}"),
            ("Vòng lặp chính sách k:", f"Policy Iteration {cur_step.iter_idx}"),
            ("Pha hoạt động hiện tại:", phase_name),
            ("Số vòng lặp giải hệ Bellman:", f"{cur_step.eval_substeps} vòng (Đánh giá V^pi)"),
            ("Trạng thái chính sách:", stable_status),
            ("Giá trị kỳ vọng V^pi(Start):", f"{cur_step.V[0]:.3f}"),
        ]
        for i, (k, v) in enumerate(rows):
            card_r = pygame.Rect(x, y + 26 + i * 32, 640, 28)
            pygame.draw.rect(self.screen, (20, 29, 44), card_r, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, card_r, width=1, border_radius=6)

            k_s = self.bold_font.render(k, True, TEXT_MUTED)
            v_s = self.bold_font.render(v, True, (52, 211, 153) if "Hội tụ" in v else TEXT_WHITE)
            self.screen.blit(k_s, (x + 14, y + 26 + i * 32 + 5))
            self.screen.blit(v_s, (x + 250, y + 26 + i * 32 + 5))

        # Khung lý thuyết theo slide bài giảng
        box_y = y + 225
        note_box = pygame.Rect(x, box_y, 640, 185)
        pygame.draw.rect(self.screen, (15, 23, 42), note_box, border_radius=8)
        pygame.draw.rect(self.screen, (56, 189, 248), note_box, width=1, border_radius=8)

        n1 = self.bold_font.render("[LUÂN PHIÊN 2 PHA CHO ĐẾN KHI CHÍNH SÁCH KHÔNG ĐỔI]:", True, (56, 189, 248))
        n2 = self.regular_font.render("• Pha 1: Policy Evaluation - Giải hệ Bellman tuyến tính tìm chính xác hàm V^{pi_k}.", True, TEXT_WHITE)
        n3 = self.regular_font.render("• Pha 2: Policy Improvement - pi_{k+1}(s) = argmax_a [ R(s, a) + gamma * sum P V^{pi_k} ].", True, (254, 240, 138))
        n4 = self.regular_font.render("• Điều kiện dừng: Dừng lặp khi pi_{k+1}(s) == pi_k(s) với mọi trạng thái (Policy Stable).", True, TEXT_WHITE)
        n5 = self.bold_font.render("★ Đặc điểm: Số vòng lặp lớn RẤT ÍT (hội tụ chỉ sau 2-3 vòng!), nhưng mỗi vòng tính V rất nặng.", True, (52, 211, 153))
        self.screen.blit(n1, (x + 14, box_y + 12))
        self.screen.blit(n2, (x + 14, box_y + 40))
        self.screen.blit(n3, (x + 14, box_y + 70))
        self.screen.blit(n4, (x + 14, box_y + 100))
        self.screen.blit(n5, (x + 14, box_y + 140))

        tip = self.regular_font.render("(*) Bấm 'Bước tiếp' (hoặc phím N) để xem chính sách và giá trị thay đổi từng pha.", True, (56, 189, 248))
        self.screen.blit(tip, (x, box_y + 200))

    def _draw_info_phase4(self, x: int, y: int) -> None:
        """Chi tiết rút trích chính sách tối ưu pi* và mô phỏng thực tế."""
        lbl = self.bold_font.render("RÚT TRÍCH CHÍNH SÁCH TỐI ƯU pi*(s) & MÔ PHỎNG:", True, (52, 211, 153))
        self.screen.blit(lbl, (x, y))

        data = [
            ("Cơ chế rút trích chính sách:", "pi*(s) = argmax_a sum P(s'|s,a)[R + gamma*V*(s')] (từ bảng V* ở Tab 3)"),
            ("Tỉ lệ tới đích thành công:", f"{self.stats_opt.success_rate*100:.1f}% (Vượt trội hoàn toàn so với ngẫu nhiên)"),
            ("Tỉ lệ rơi vào bẫy:", f"{self.stats_opt.trap_rate*100:.1f}% (Do 10% rủi ro trượt tại ô (4,3) kề Đích)"),
            ("Phần thưởng tích lũy trung bình:", f"+{self.stats_opt.avg_reward:.2f} (Đạt điểm số dương cao)"),
            ("Số bước trung bình tới đích:", f"{self.stats_opt.avg_steps:.1f} bước (Lý thuyết 6 bước + bước trượt)"),
            ("Quỹ đạo tối ưu trên lưới:", "Lên dọc Cột 1 -> Sang phải dọc Hàng 4 về Đích"),
            ("Hướng đi tại ô (4,3) kề Đích:", "Mũi tên vector chỉ thẳng sang Phải hướng về Đích (+10)"),
            ("Trạng thái mô phỏng Robot:", f"{self.agent_status}"),
        ]
        for i, (k, v) in enumerate(data):
            card_r = pygame.Rect(x, y + 32 + i * 42, 635, 36)
            pygame.draw.rect(self.screen, (20, 29, 44), card_r, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, card_r, width=1, border_radius=6)

            k_s = self.bold_font.render(k, True, TEXT_MUTED)
            v_s = self.bold_font.render(v, True, TEXT_WHITE)
            self.screen.blit(k_s, (x + 14, y + 32 + i * 42 + 9))
            self.screen.blit(v_s, (x + 240, y + 32 + i * 42 + 9))

        # Khung giải thích vì sao Tab 4 đã có hướng đi mà không hiện số V
        expl_r = pygame.Rect(x, y + 380, 635, 55)
        pygame.draw.rect(self.screen, (15, 23, 42), expl_r, border_radius=6)
        pygame.draw.rect(self.screen, (52, 211, 153), expl_r, width=1, border_radius=6)
        c1 = self.bold_font.render("[GIẢI THÍCH]: Tab 4 nhận bảng V* từ Tab 3 để tạo ra các mũi tên pi*(s).", True, (52, 211, 153))
        c2 = self.regular_font.render("Các số V được ẩn đi trên lưới để tập trung quan sát hướng mũi tên và Robot di chuyển!", True, TEXT_WHITE)
        self.screen.blit(c1, (x + 14, y + 386))
        self.screen.blit(c2, (x + 14, y + 408))

    def _draw_two_matrices_comparison(self, mouse_pos: tuple[int, int]) -> None:
        """Tab 5: Hiển thị trực quan HAI MA TRẬN 4x4 CẠNH NHAU (Tối ưu vs Sát bẫy)."""
        mat_size = 340
        c_size = mat_size // 4  # 85 px

        # Ma trận 1: Bên trái (Chính sách tối ưu pi*)
        m1_x = 35
        m1_y = 115
        self._draw_matrix_card(
            title="1. CHÍNH SÁCH TỐI ƯU pi* (ĐƯỜNG XANH AN TOÀN)",
            title_color=(52, 211, 153),
            x=m1_x,
            y=m1_y,
            size=mat_size,
            cell_size=c_size,
            policy=self.pi_star,
            V_values=self.V_star,
            path=[(1, 1), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4)],
            trail_color=TRAIL_COLOR,
            route_desc="Hành trình: Cột 1 -> Hàng 4 (Né xa bẫy)",
            v_start=self.V_star[0],
            win_rate=self.stats_opt.success_rate,
            trap_rate=self.stats_opt.trap_rate,
            sim_path=self.tab5_opt_path,
            sim_status=self.tab5_opt_status,
        )

        # Ma trận 2: Ở giữa (Chính sách đi sát bẫy)
        m2_x = 395
        m2_y = 115
        self._draw_matrix_card(
            title="2. CHÍNH SÁCH SÁT BẪY (ĐƯỜNG ĐỎ THIỂN CẬN)",
            title_color=(244, 63, 94),
            x=m2_x,
            y=m2_y,
            size=mat_size,
            cell_size=c_size,
            policy=self.pi_risky,
            V_values=self.V_risky,
            path=[(1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (3, 4), (4, 4)],
            trail_color=TRAIL_RISKY,
            route_desc="Hành trình: Hàng 1 -> Cột 4 (Sát sạt bẫy)",
            v_start=self.V_risky[0],
            win_rate=self.stats_risky.success_rate,
            trap_rate=self.stats_risky.trap_rate,
            sim_path=self.tab5_risky_path,
            sim_status=self.tab5_risky_status,
        )

        # Bảng đối chiếu và giải thích bản chất toán học: Bên phải
        p_x = 755
        p_y = 115
        p_w = 490
        p_h = 635
        panel_rect = pygame.Rect(p_x, p_y, p_w, p_h)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel_rect, width=2, border_radius=12)

        p_title = self.title_font.render("Đối chiếu toán học 2 chính sách", True, TEXT_HIGHLIGHT)
        self.screen.blit(p_title, (p_x + 20, p_y + 14))

        # Bảng số liệu
        headers = ["Chỉ tiêu", "Chính sách pi* (Né)", "Chính sách sát bẫy"]
        col_w = [140, 160, 160]

        ty = p_y + 48
        pygame.draw.rect(self.screen, (51, 65, 85), pygame.Rect(p_x + 15, ty, sum(col_w), 30), border_radius=4)
        cx = p_x + 25
        for i, h in enumerate(headers):
            self.screen.blit(self.bold_font.render(h, True, TEXT_HIGHLIGHT), (cx, ty + 6))
            cx += col_w[i]

        rows = [
            ("Kỳ vọng V(Start)", f"{self.V_star[0]:.2f} (Cao)", f"{self.V_risky[0]:.2f} (Sụt giảm)"),
            ("Tỉ lệ thành công", f"{self.stats_opt.success_rate*100:.1f}%", f"{self.stats_risky.success_rate*100:.1f}%"),
            ("Tỉ lệ rơi vào bẫy", f"{self.stats_opt.trap_rate*100:.1f}% (An toàn)", f"{self.stats_risky.trap_rate*100:.1f}% (Rủi ro x2.5)"),
            ("Thưởng trung bình", f"+{self.stats_opt.avg_reward:.2f}", f"{self.stats_risky.avg_reward:.2f}"),
            ("Độ dài lý thuyết", "6 bước", "6 bước (BẰNG NHAU)"),
        ]

        for r_idx, r_data in enumerate(rows):
            row_y = ty + 32 + r_idx * 30
            bg = (30, 41, 59) if r_idx % 2 == 0 else (20, 29, 44)
            pygame.draw.rect(self.screen, bg, pygame.Rect(p_x + 15, row_y, sum(col_w), 28))
            cx = p_x + 25
            for c_idx, val in enumerate(r_data):
                col_text = self.regular_font.render(val, True, TEXT_WHITE)
                self.screen.blit(col_text, (cx, row_y + 5))
                cx += col_w[c_idx]

        # Khung phân tích cốt lõi
        box_y = ty + 195
        expl_box = pygame.Rect(p_x + 15, box_y, sum(col_w), 290)
        pygame.draw.rect(self.screen, (15, 23, 42), expl_box, border_radius=8)
        pygame.draw.rect(self.screen, (56, 189, 248), expl_box, width=1, border_radius=8)

        t1 = self.bold_font.render("[BẢN CHẤT TOÁN HỌC CỦA MDP & BELLMAN]:", True, (254, 240, 138))
        t2 = self.regular_font.render("1. Cả 2 con đường đều tốn đúng 6 bước lý thuyết:", True, TEXT_WHITE)
        t3 = self.regular_font.render("   • Đường né bẫy: 3 Lên + 3 Phải = 6 bước.", True, TEXT_MUTED)
        t4 = self.regular_font.render("   • Đường sát bẫy: 3 Phải + 3 Lên = 6 bước.", True, TEXT_MUTED)
        t5 = self.regular_font.render("2. Vì sao đường sát bẫy lại thất bại?", True, TEXT_WHITE)
        t6 = self.regular_font.render("   • Tại ô (1,3): Đi Phải nhưng 10% trượt Lên -> RƠI BẪY (2,3)!", True, (244, 63, 94))
        t7 = self.regular_font.render("   • Tại ô (2,4): Đi Lên nhưng 10% trượt Trái -> RƠI BẪY (2,3)!", True, (244, 63, 94))
        t8 = self.regular_font.render("   -> Rủi ro trượt kéo kỳ vọng V(Start) từ 6.78 sụt xuống chỉ còn 2.07!", True, (248, 113, 113))
        t9 = self.regular_font.render("3. Phương trình Bellman tự động tối ưu:", True, TEXT_WHITE)
        t10 = self.regular_font.render("   • Tự cân bằng giữa chi phí bước đi (-0.04) và rủi ro rơi bẫy (-10).", True, (52, 211, 153))
        t11 = self.regular_font.render("   • Tự chọn đường đi vòng an toàn mà KHÔNG CẦN code cứng!", True, (56, 189, 248))

        self.screen.blit(t1, (p_x + 25, box_y + 12))
        self.screen.blit(t2, (p_x + 25, box_y + 36))
        self.screen.blit(t3, (p_x + 25, box_y + 58))
        self.screen.blit(t4, (p_x + 25, box_y + 78))
        self.screen.blit(t5, (p_x + 25, box_y + 104))
        self.screen.blit(t6, (p_x + 25, box_y + 126))
        self.screen.blit(t7, (p_x + 25, box_y + 148))
        self.screen.blit(t8, (p_x + 25, box_y + 172))
        self.screen.blit(t9, (p_x + 25, box_y + 198))
        self.screen.blit(t10, (p_x + 25, box_y + 220))
        self.screen.blit(t11, (p_x + 25, box_y + 244))

        concl_s = self.bold_font.render("=> MDP tự sinh hành vi thông minh từ xác suất!", True, (56, 189, 248))
        self.screen.blit(concl_s, (p_x + 25, box_y + 266))

        # Vẽ các nút điều khiển mô phỏng đua 2 robot dưới 2 ma trận
        self._draw_controls(mouse_pos)

    def _draw_matrix_card(
        self,
        title: str,
        title_color: tuple[int, int, int],
        x: int,
        y: int,
        size: int,
        cell_size: int,
        policy: np.ndarray,
        V_values: np.ndarray,
        path: list[tuple[int, int]],
        trail_color: tuple[int, int, int],
        route_desc: str,
        v_start: float,
        win_rate: float,
        trap_rate: float,
        sim_path: list[tuple[int, int]],
        sim_status: str,
    ) -> None:
        """Vẽ 1 ma trận 4x4 hoàn chỉnh kèm mũi tên vector, giá trị V, đường quỹ đạo và số liệu."""
        card_rect = pygame.Rect(x - 8, y - 8, size + 16, size + 130)
        pygame.draw.rect(self.screen, PANEL_BG, card_rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, card_rect, width=2, border_radius=10)

        # Tiêu đề ma trận
        t_surf = self.bold_font.render(title, True, title_color)
        self.screen.blit(t_surf, (x + 4, y + 2))

        grid_top_y = y + 26
        for r in range(1, 5):
            for c in range(1, 5):
                draw_x = x + (c - 1) * cell_size
                draw_y = grid_top_y + (4 - r) * cell_size
                cell_rect = pygame.Rect(draw_x, draw_y, cell_size, cell_size)

                s = (r - 1) * 4 + (c - 1)
                is_start = (r, c) == (1, 1)
                is_goal = (r, c) == (4, 4)
                is_trap = (r, c) in {(3, 3), (2, 3)}

                if is_goal:
                    bg_col = GOAL_COLOR
                elif is_trap:
                    bg_col = TRAP_COLOR
                elif is_start:
                    bg_col = START_COLOR
                else:
                    bg_col = CELL_NORMAL

                pygame.draw.rect(self.screen, bg_col, cell_rect)
                pygame.draw.rect(self.screen, CELL_BORDER, cell_rect, width=1)

                coord_text = self.mini_font.render(f"({r},{c})", True, (148, 163, 184))
                self.screen.blit(coord_text, (draw_x + 4, draw_y + 2))

                if is_start:
                    txt = self.small_font.render("START", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + cell_size // 2, draw_y + 16)))
                    # Vẽ mũi tên chỉ hướng xuất phát tại Start
                    action = policy[s]
                    arrow_center = (draw_x + cell_size // 2, draw_y + cell_size // 2 + 2)
                    draw_vector_arrow(self.screen, arrow_center, action, (255, 255, 255), length=12, head_size=5)
                elif is_goal:
                    txt = self.small_font.render("ĐÍCH (+10)", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + cell_size // 2, draw_y + 24)))
                elif is_trap:
                    txt = self.small_font.render("BẪY (-10)", True, TEXT_WHITE)
                    self.screen.blit(txt, txt.get_rect(center=(draw_x + cell_size // 2, draw_y + 24)))
                else:
                    action = policy[s]
                    arrow_center = (draw_x + cell_size // 2, draw_y + cell_size // 2 - 2)
                    draw_vector_arrow(self.screen, arrow_center, action, (255, 255, 255), length=12, head_size=5)

                v_val = V_values[s]
                v_text = self.mini_font.render(f"V={v_val:.2f}", True, (254, 240, 138) if not (is_goal or is_trap) else TEXT_WHITE)
                self.screen.blit(v_text, v_text.get_rect(center=(draw_x + cell_size // 2, draw_y + cell_size - 12)))

        # Vẽ đường quỹ đạo lý thuyết
        points = [
            (
                x + (c - 1) * cell_size + cell_size // 2,
                grid_top_y + (4 - r) * cell_size + cell_size // 2,
            )
            for (r, c) in path
        ]
        pygame.draw.lines(self.screen, trail_color, False, points, width=3)

        # Vẽ Robot mô phỏng chạy thực tế trên ma trận
        if len(sim_path) > 0:
            cur_r, cur_c = sim_path[-1]
            center_x = x + (cur_c - 1) * cell_size + cell_size // 2
            center_y = grid_top_y + (4 - cur_r) * cell_size + cell_size // 2
            pygame.draw.circle(self.screen, AGENT_COLOR, (center_x, center_y), 14)
            pygame.draw.circle(self.screen, TEXT_WHITE, (center_x, center_y), 14, width=2)
            pygame.draw.circle(self.screen, (15, 23, 42), (center_x, center_y), 6)

        # Card thông số chi tiết dưới mỗi ma trận
        info_top = grid_top_y + size + 8
        r1 = self.small_font.render(route_desc, True, (56, 189, 248))
        r2 = self.bold_font.render(f"V(Start) = {v_start:.2f}  |  Thắng: {win_rate*100:.1f}%", True, TEXT_WHITE)
        r3 = self.small_font.render(f"Rơi bẫy: {trap_rate*100:.1f}%  |  Robot: {sim_status}", True, (248, 113, 113) if "RƠI" in sim_status else (52, 211, 153))

        self.screen.blit(r1, (x + 2, info_top))
        self.screen.blit(r2, (x + 2, info_top + 18))
        self.screen.blit(r3, (x + 2, info_top + 38))

    def _draw_controls(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ các nút điều khiển mô phỏng phía dưới bên trái."""
        self.btn_play.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_step.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_reset.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_speed.draw(self.screen, self.bold_font, mouse_pos)


def main() -> None:
    """Điểm khởi chạy Demo 1 độc lập."""
    import main as master_launcher
    master_launcher.main_with_screen("demo1")


if __name__ == "__main__":
    main()
