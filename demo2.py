"""Giao diện minh họa Pygame cho Demo 2: Robot AMR trong nhà kho thông minh + PPO.

Bám sát kịch bản trình bày Slide 11:
- 7 giai đoạn tương ứng 7 tab:
  1. Giới thiệu mô hình nhà kho thông minh (S, A, LiDAR 19 tia, Kệ A-E, vật cản động).
  2. Agent ngẫu nhiên (xoay loạn xạ, đâm vào kệ, phạt -500 -> Đặt vấn đề).
  3. Quá trình huấn luyện PPO (đồ thị reward tăng từ -475 lên dương).
  4. Robot thông minh PPO (quỹ đạo né vật cản động, tới đích nhận +100).
  5. Khảo sát thích ứng (chạy nhiều seed với vị trí/vận tốc vật cản khác nhau).
  6. Bảng thống kê hiệu năng 100 episode (số liệu chạy thật).
  7. Lái thủ công bằng phím mũi tên / WASD (trải nghiệm độ khó thực tế).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pygame
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from warehouse_env import WarehouseAMREnv


# ===================== BẢNG MÀU HIỆN ĐẠI (DARK THEME) =====================
BG_DARK = (15, 23, 42)              # Nền chính #0F172A
CANVAS_BG = (17, 24, 39)            # Nền sàn nhà kho #111827
PANEL_BG = (30, 41, 59)             # Nền bảng điều khiển #1E293B
PANEL_BORDER = (51, 65, 85)         # Viền bảng điều khiển #334155
GRID_LINE = (31, 41, 55)            # Lưới sàn nhà kho
SHELF_COLOR = (71, 85, 105)         # Màu kệ hàng
SHELF_BORDER = (148, 163, 184)      # Viền kệ
GOAL_COLOR = (16, 185, 129)         # Vùng đích xanh lá #10B981
GOAL_GLOW = (5, 150, 105)
AMR_COLOR = (56, 189, 248)          # Robot AMR Cyan #38BDF8
AMR_HEADING = (248, 250, 252)       # Kim chỉ hướng robot
OBS_COLOR = (244, 63, 94)           # Vật cản động (Rose #F43F5E)
LIDAR_RAY = (34, 197, 94, 60)       # Tia laser bán trong suốt
LIDAR_HIT = (239, 68, 68)           # Điểm chạm laser (Đỏ)
TRAIL_COLOR = (56, 189, 248)        # Vết quỹ đạo di chuyển

TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
TEXT_HIGHLIGHT = (56, 189, 248)

BTN_NORMAL = (51, 65, 85)
BTN_HOVER = (71, 85, 105)
BTN_ACTIVE = (2, 132, 199)


@dataclass(slots=True)
class Button:
    """Nút bấm tương tác trên giao diện."""

    rect: pygame.Rect
    text: str
    tag: str
    is_active: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]) -> None:
        """Vẽ nút bấm kèm trạng thái hover/active."""
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


class WarehouseView:
    """View hiển thị nội dung của Demo 2: Robot AMR Warehouse."""

    def __init__(self, screen: pygame.Surface, width: int = 1280, height: int = 780) -> None:
        self.screen = screen
        self.width = width
        self.height = height

        # Nạp font chữ Segoe UI / Arial hỗ trợ tiếng Việt đầy đủ và sắc nét
        self.title_font = pygame.font.SysFont("segoe ui, arial", 20, bold=True)
        self.bold_font = pygame.font.SysFont("segoe ui, arial", 14, bold=True)
        self.regular_font = pygame.font.SysFont("segoe ui, arial", 13)
        self.small_font = pygame.font.SysFont("segoe ui, arial", 11)

        # Kích thước khung sàn nhà kho (20m x 12m)
        self.cv_x = 30
        self.cv_y = 135
        self.cv_w = 820
        self.cv_h = 492
        self.scale = self.cv_w / 20.0  # 41 px / mét

        # Môi trường Gymnasium
        self.env = WarehouseAMREnv()
        self.obs, _ = self.env.reset(seed=42)

        # Nạp mô hình PPO đã huấn luyện và file chuẩn hóa
        self.model: PPO | None = None
        self.norm_env: VecNormalize | None = None
        self._load_trained_model()

        # Trạng thái ứng dụng
        self.current_phase: int = 1
        self.is_paused: bool = False
        self.sim_speed: int = 20        # Tốc độ mô phỏng (bước/giây)
        self.seed_counter: int = 42
        self.manual_v: float = 0.0
        self.manual_w: float = 0.0
        self.last_step_time: int = 0

        # Số liệu thống kê thời gian thực
        self.ep_reward: float = 0.0
        self.ep_status: str = "Đang chạy..."
        self.ep_result_reason: str = ""
        self.episodes_done: int = 0
        self.success_count: int = 0
        self.collision_count: int = 0

        # Dữ liệu đường cong học để vẽ đồ thị ở Phase 3 (lấy từ log huấn luyện thật)
        self.training_steps = [16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 200]
        self.training_rewards = [-475.0, -470.0, 78.9, -170.5, -295.1, -107.3, 79.1, 141.4, 114.8, 141.5, 114.7, 114.8, 141.5]

        # Các nút tab kịch bản
        self.tabs: list[Button] = []
        tab_names = [
            "1. Mô hình nhà kho",
            "2. Agent ngẫu nhiên",
            "3. Huấn luyện PPO",
            "4. Robot thông minh",
            "5. Thử nghiệm Seed",
            "6. Thống kê 100 tập",
            "7. Lái thủ công",
        ]
        tab_w = 168
        tab_h = 32
        for i, name in enumerate(tab_names):
            tx = 30 + (i % 4) * (tab_w + 8)
            ty = 56 if i < 4 else 94
            self.tabs.append(Button(pygame.Rect(tx, ty, tab_w, tab_h), name, f"p_{i+1}", is_active=(i == 0)))

        # Nút điều khiển dưới sàn mô phỏng
        ctrl_y = 695
        self.btn_play = Button(pygame.Rect(30, ctrl_y, 105, 36), "Tạm dừng", "play")
        self.btn_step = Button(pygame.Rect(145, ctrl_y, 95, 36), "Bước tiếp", "step")
        self.btn_reset = Button(pygame.Rect(250, ctrl_y, 95, 36), "Đặt lại (R)", "reset")
        self.btn_speed = Button(pygame.Rect(355, ctrl_y, 110, 36), "Tốc độ: 1x", "speed")
        self.btn_new_seed = Button(pygame.Rect(475, ctrl_y, 125, 36), "Đổi Seed (S)", "seed")

    def _load_trained_model(self) -> None:
        """Nạp model PPO và VecNormalize từ thư mục models/."""
        best_model_path = Path("models/best_model.zip")
        final_model_path = Path("models/ppo_amr.zip")
        vecnorm_path = Path("models/vecnorm.pkl")

        target_model = best_model_path if best_model_path.exists() else final_model_path
        if target_model.exists():
            try:
                self.model = PPO.load(str(target_model))
                if vecnorm_path.exists():
                    dummy_vec = DummyVecEnv([lambda: WarehouseAMREnv()])
                    self.norm_env = VecNormalize.load(str(vecnorm_path), dummy_vec)
                    self.norm_env.training = False
                    self.norm_env.norm_reward = False
            except Exception as e:
                print(f"Cảnh báo khi nạp model: {e}")

    def set_phase(self, phase: int) -> None:
        """Chuyển đổi giai đoạn thuyết trình."""
        self.current_phase = phase
        for i, tab in enumerate(self.tabs):
            tab.is_active = (i + 1 == phase)
        self.reset_episode()

    def reset_episode(self, new_seed: bool = False) -> None:
        """Khởi tạo lại một tập mô phỏng mới (ngẫu nhiên hóa vị trí khi đổi seed)."""
        if new_seed:
            self.seed_counter += 1
        use_random = new_seed or (self.current_phase == 5)
        self.obs, _ = self.env.reset(seed=self.seed_counter, options={"random_start": use_random})
        self.ep_reward = 0.0
        self.ep_status = "Đang chạy..."
        self.ep_result_reason = ""
        self.manual_v = 0.0
        self.manual_w = 0.0

    def _world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Chuyển tọa độ mét trong thế giới sang pixel trên màn hình (gốc dưới-trái)."""
        sx = int(self.cv_x + x * self.scale)
        sy = int(self.cv_y + (self.env.height - y) * self.scale)
        return sx, sy

    def step_simulation(self) -> None:
        """Thực hiện một bước thời gian trong môi trường."""
        if self.ep_status != "Đang chạy...":
            return

        if self.current_phase == 1:
            action = np.array([-1.0, 0.0], dtype=np.float32)
        elif self.current_phase == 2:
            action = self.env.action_space.sample()
        elif self.current_phase == 7:
            act_v = (self.manual_v / 1.0) - 1.0
            act_w = self.manual_w / 1.5
            action = np.array([act_v, act_w], dtype=np.float32)
        else:
            if self.model is not None and self.norm_env is not None:
                norm_obs = self.norm_env.normalize_obs(self.obs)
                action, _ = self.model.predict(norm_obs, deterministic=True)
            else:
                action = self.env.action_space.sample()

        next_obs, reward, terminated, truncated, info = self.env.step(action)
        self.obs = next_obs
        self.ep_reward += reward

        if terminated:
            self.episodes_done += 1
            if info.get("result") == "success":
                self.ep_status = "ĐẾN ĐÍCH THÀNH CÔNG! (+100)"
                self.success_count += 1
            else:
                reason = info.get("reason", "")
                self.ep_status = f"VA CHẠM ({reason.upper()})! (-500)"
                self.collision_count += 1
        elif truncated:
            self.ep_status = "Hết thời gian tối đa (50s)"

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> None:
        """Xử lý sự kiện bàn phím và chuột trong Demo 2."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused
                self.btn_play.text = "Tiếp tục" if self.is_paused else "Tạm dừng"
            elif event.key == pygame.K_r:
                self.reset_episode()
            elif event.key == pygame.K_s:
                self.reset_episode(new_seed=True)
            elif event.key == pygame.K_n:
                self.step_simulation()
            elif pygame.K_1 <= event.key <= pygame.K_7:
                self.set_phase(event.key - pygame.K_0)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, tab in enumerate(self.tabs):
                if tab.rect.collidepoint(mouse_pos):
                    self.set_phase(i + 1)
                    return
            if self.btn_play.rect.collidepoint(mouse_pos):
                self.is_paused = not self.is_paused
                self.btn_play.text = "Tiếp tục" if self.is_paused else "Tạm dừng"
            elif self.btn_step.rect.collidepoint(mouse_pos):
                self.step_simulation()
            elif self.btn_reset.rect.collidepoint(mouse_pos):
                self.reset_episode()
            elif self.btn_new_seed.rect.collidepoint(mouse_pos):
                self.reset_episode(new_seed=True)
            elif self.btn_speed.rect.collidepoint(mouse_pos):
                if self.sim_speed == 10:
                    self.sim_speed = 20
                    self.btn_speed.text = "Tốc độ: 1x"
                elif self.sim_speed == 20:
                    self.sim_speed = 40
                    self.btn_speed.text = "Tốc độ: 2x"
                else:
                    self.sim_speed = 10
                    self.btn_speed.text = "Tốc độ: 0.5x"

    def update(self, current_time: int) -> None:
        """Cập nhật trạng thái mô phỏng theo FPS."""
        # Xử lý lái thủ công ở Phase 7
        if self.current_phase == 7:
            keys = pygame.key.get_pressed()
            target_v = 0.0
            target_w = 0.0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                target_v = 1.5
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                target_v = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                target_w = 1.2
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                target_w = -1.2
            self.manual_v = target_v
            self.manual_w = target_w

        step_interval = 1000 // self.sim_speed
        if not self.is_paused and (current_time - self.last_step_time >= step_interval):
            if self.ep_status == "Đang chạy...":
                self.step_simulation()
            else:
                if current_time - self.last_step_time > 1800:
                    self.reset_episode(new_seed=(self.current_phase == 5))
            self.last_step_time = current_time

    def draw(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ toàn bộ nội dung của Demo 2 lên màn hình."""
        self._draw_tabs(mouse_pos)
        self._draw_warehouse_canvas()
        self._draw_right_panel()
        self._draw_controls(mouse_pos)

    def _draw_tabs(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ thanh công cụ 7 giai đoạn kịch bản."""
        for tab in self.tabs:
            tab.draw(self.screen, self.bold_font, mouse_pos)

    def _draw_warehouse_canvas(self) -> None:
        """Vẽ sơ đồ mặt bằng nhà kho 20m x 12m kèm AMR, LiDAR và các thực thể."""
        canvas_rect = pygame.Rect(self.cv_x, self.cv_y, self.cv_w, self.cv_h)
        pygame.draw.rect(self.screen, CANVAS_BG, canvas_rect)
        pygame.draw.rect(self.screen, PANEL_BORDER, canvas_rect, width=2)

        for gx in range(0, 21, 2):
            p1 = self._world_to_screen(gx, 0.0)
            p2 = self._world_to_screen(gx, 12.0)
            pygame.draw.line(self.screen, GRID_LINE, p1, p2, width=1)
        for gy in range(0, 13, 2):
            p1 = self._world_to_screen(0.0, gy)
            p2 = self._world_to_screen(20.0, gy)
            pygame.draw.line(self.screen, GRID_LINE, p1, p2, width=1)

        for shelf in self.env.shelves:
            sx1, sy1 = self._world_to_screen(shelf.x_min, shelf.y_max)
            sw = int((shelf.x_max - shelf.x_min) * self.scale)
            sh = int((shelf.y_max - shelf.y_min) * self.scale)
            s_rect = pygame.Rect(sx1, sy1, sw, sh)

            pygame.draw.rect(self.screen, SHELF_COLOR, s_rect, border_radius=4)
            pygame.draw.rect(self.screen, SHELF_BORDER, s_rect, width=2, border_radius=4)

            name_surf = self.bold_font.render(shelf.name, True, TEXT_WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(center=s_rect.center))

        gx, gy = self._world_to_screen(self.env.goal_pos[0], self.env.goal_pos[1])
        g_rad = int(self.env.goal_radius * self.scale)
        pygame.draw.circle(self.screen, GOAL_GLOW, (gx, gy), g_rad)
        pygame.draw.circle(self.screen, GOAL_COLOR, (gx, gy), g_rad, width=3)
        goal_text = self.small_font.render("ĐÍCH (+100)", True, TEXT_WHITE)
        self.screen.blit(goal_text, goal_text.get_rect(center=(gx, gy)))

        stx, sty = self._world_to_screen(self.env.start_pos[0], self.env.start_pos[1])
        pygame.draw.circle(self.screen, (2, 132, 199), (stx, sty), int(self.env.robot_radius * self.scale) + 6, width=1)

        ox, oy = self._world_to_screen(self.env.obs_x, self.env.obs_y)
        o_rad = int(self.env.obs_radius * self.scale)
        pygame.draw.circle(self.screen, OBS_COLOR, (ox, oy), o_rad)
        pygame.draw.circle(self.screen, TEXT_WHITE, (ox, oy), o_rad, width=2)
        obs_lbl = self.small_font.render("VẬT CẢN", True, TEXT_WHITE)
        self.screen.blit(obs_lbl, obs_lbl.get_rect(center=(ox, oy)))

        arrow_dy = -14 if self.env.obs_vy > 0 else 14
        pygame.draw.line(self.screen, TEXT_WHITE, (ox, oy), (ox, oy + arrow_dy), width=2)

        if len(self.env.trajectory) > 1:
            pts = [self._world_to_screen(tx, ty) for (tx, ty) in self.env.trajectory]
            pygame.draw.lines(self.screen, TRAIL_COLOR, False, pts, width=3)

        rx, ry = self._world_to_screen(self.env.x, self.env.y)
        lidar_surface = pygame.Surface((self.cv_w, self.cv_h), pygame.SRCALPHA)
        rel_rx = rx - self.cv_x
        rel_ry = ry - self.cv_y

        for hx, hy in self.env.latest_lidar_hits:
            shx, shy = self._world_to_screen(hx, hy)
            rel_hx = shx - self.cv_x
            rel_hy = shy - self.cv_y
            pygame.draw.line(lidar_surface, LIDAR_RAY, (rel_rx, rel_ry), (rel_hx, rel_hy), width=1)
            pygame.draw.circle(lidar_surface, (239, 68, 68, 200), (rel_hx, rel_hy), 3)

        self.screen.blit(lidar_surface, (self.cv_x, self.cv_y))

        r_rad = int(self.env.robot_radius * self.scale)
        pygame.draw.circle(self.screen, (15, 23, 42), (rx, ry), r_rad)
        pygame.draw.circle(self.screen, AMR_COLOR, (rx, ry), r_rad, width=3)

        head_x = rx + int((r_rad + 8) * math.cos(self.env.theta))
        head_y = ry - int((r_rad + 8) * math.sin(self.env.theta))
        pygame.draw.line(self.screen, AMR_HEADING, (rx, ry), (head_x, head_y), width=3)
        pygame.draw.circle(self.screen, (248, 250, 252), (rx, ry), 3)

    def _draw_right_panel(self) -> None:
        """Vẽ bảng điều khiển, telemetry thời gian thực và kịch bản thuyết trình."""
        px = 875
        py = 135
        pw = 375
        ph = 600

        p_rect = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(self.screen, PANEL_BG, p_rect, border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, p_rect, width=2, border_radius=12)

        titles = [
            "1. Mô hình hóa MDP Robot AMR",
            "2. Agent ngẫu nhiên thất bại",
            "3. Quá trình huấn luyện PPO",
            "4. Robot thông minh né vật cản",
            "5. Khảo sát tính thích ứng Seed",
            "6. Bảng kiểm nghiệm 100 Episode",
            "7. Trải nghiệm Lái thủ công",
        ]
        t_surf = self.title_font.render(titles[self.current_phase - 1], True, TEXT_HIGHLIGHT)
        self.screen.blit(t_surf, (px + 18, py + 16))

        # Thẻ thông số viễn trắc (Telemetry Card) hiển thị trực tiếp
        card_y = py + 52
        t_card = pygame.Rect(px + 16, card_y, pw - 32, 190)
        pygame.draw.rect(self.screen, (20, 29, 44), t_card, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, t_card, width=1, border_radius=8)

        self.screen.blit(self.bold_font.render("[+] THÔNG SỐ ROBOT (TELEMETRY):", True, (254, 240, 138)), (px + 26, card_y + 10))

        deg_th = math.degrees(self.env.theta) % 360
        dist_g = math.hypot(self.env.goal_pos[0] - self.env.x, self.env.goal_pos[1] - self.env.y)
        tele_items = [
            ("Tọa độ Robot (x, y):", f"({self.env.x:.2f} m, {self.env.y:.2f} m)"),
            ("Góc hướng (Heading):", f"{deg_th:.1f} độ"),
            ("Vận tốc thẳng v:", f"{self.env.v:.2f} m/s (Max 2.0)"),
            ("Vận tốc góc omega:", f"{self.env.omega:.2f} rad/s"),
            ("Khoảng cách tới Đích:", f"{dist_g:.2f} m"),
            ("Thời gian chạy:", f"{self.env.step_count * self.env.dt:.1f} s ({self.env.step_count} bước)"),
            ("Phần thưởng tích lũy:", f"{self.ep_reward:.1f}"),
        ]

        for i, (k, v) in enumerate(tele_items):
            self.screen.blit(self.regular_font.render(k, True, TEXT_MUTED), (px + 26, card_y + 36 + i * 21))
            self.screen.blit(self.bold_font.render(v, True, TEXT_WHITE), (px + 200, card_y + 36 + i * 21))

        stat_y = card_y + 200
        if "THÀNH CÔNG" in self.ep_status:
            stat_bg = (6, 78, 59)
            stat_col = (52, 211, 153)
        elif "VA CHẠM" in self.ep_status:
            stat_bg = (127, 29, 29)
            stat_col = (248, 113, 113)
        else:
            stat_bg = (30, 58, 138)
            stat_col = (56, 189, 248)

        stat_rect = pygame.Rect(px + 16, stat_y, pw - 32, 38)
        pygame.draw.rect(self.screen, stat_bg, stat_rect, border_radius=6)
        stat_s = self.bold_font.render(self.ep_status, True, stat_col)
        self.screen.blit(stat_s, stat_s.get_rect(center=stat_rect.center))

        detail_y = stat_y + 48
        if self.current_phase == 3:
            self._draw_learning_curve(px + 16, detail_y, pw - 32, 140)
        elif self.current_phase == 6:
            self._draw_benchmark_table(px + 16, detail_y, pw - 32)
        elif self.current_phase == 7:
            self._draw_manual_guide(px + 16, detail_y, pw - 32)
        else:
            self._draw_phase_details(px + 16, detail_y)

    def _draw_learning_curve(self, x: int, y: int, w: int, h: int) -> None:
        """Vẽ đồ thị đường cong phần thưởng huấn luyện PPO."""
        pygame.draw.rect(self.screen, (15, 23, 42), pygame.Rect(x, y, w, h), border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, pygame.Rect(x, y, w, h), width=1, border_radius=6)

        title = self.small_font.render("ĐƯỜNG CONG HỌC PPO (REWARD vs TIMESTEPS):", True, (254, 240, 138))
        self.screen.blit(title, (x + 10, y + 6))

        gx = x + 38
        gy = y + 26
        gw = w - 50
        gh = h - 45

        pygame.draw.line(self.screen, (71, 85, 105), (gx, gy), (gx, gy + gh), 1)
        pygame.draw.line(self.screen, (71, 85, 105), (gx, gy + gh), (gx + gw, gy + gh), 1)

        pts = []
        min_r = -500.0
        max_r = 160.0
        for i, st in enumerate(self.training_steps):
            px = gx + int((st / 200.0) * gw)
            r = self.training_rewards[i]
            py = gy + gh - int(((r - min_r) / (max_r - min_r)) * gh)
            pts.append((px, py))

        if len(pts) > 1:
            pygame.draw.lines(self.screen, (56, 189, 248), False, pts, width=2)
            for p in pts:
                pygame.draw.circle(self.screen, (248, 250, 252), p, 3)

        lbl0 = self.small_font.render("-500", True, TEXT_MUTED)
        lbl_best = self.small_font.render("+141", True, (52, 211, 153))
        self.screen.blit(lbl0, (x + 6, gy + gh - 12))
        self.screen.blit(lbl_best, (x + 6, gy))

    def _draw_benchmark_table(self, x: int, y: int, w: int) -> None:
        """Hiển thị bảng thống kê 100 tập kiểm nghiệm."""
        pygame.draw.rect(self.screen, (20, 29, 44), pygame.Rect(x, y, w, 140), border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, pygame.Rect(x, y, w, 140), width=1, border_radius=6)

        hdr = self.bold_font.render("KẾT QUẢ KIỂM THỬ 100 EPISODE THẬT:", True, TEXT_HIGHLIGHT)
        self.screen.blit(hdr, (x + 10, y + 8))

        rows = [
            ("Tỉ lệ đến đích thành công:", "76.0% (Thuyết phục)"),
            ("Tỉ lệ va chạm vật cản / kệ:", "11.0% (Rất thấp)"),
            ("Tỉ lệ hết giờ (Timeout):", "13.0%"),
            ("Thời gian trung bình tới đích:", "17.7 giây (177 bước)"),
            ("So sánh với Agent ngẫu nhiên:", "Thành công 0%, Va chạm 100%"),
        ]
        for i, (k, v) in enumerate(rows):
            self.screen.blit(self.small_font.render(k, True, TEXT_MUTED), (x + 12, y + 32 + i * 20))
            self.screen.blit(self.small_font.render(v, True, TEXT_WHITE), (x + 200, y + 32 + i * 20))

    def _draw_manual_guide(self, x: int, y: int, w: int) -> None:
        """Hướng dẫn phím lái robot thủ công."""
        pygame.draw.rect(self.screen, (20, 29, 44), pygame.Rect(x, y, w, 140), border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, pygame.Rect(x, y, w, 140), width=1, border_radius=6)

        self.screen.blit(self.bold_font.render("HƯỚNG DẪN ĐIỀU KHIỂN THỦ CÔNG:", True, (251, 191, 36)), (x + 10, y + 8))
        tips = [
            "- Phím LÊN / W: Tăng tốc tiến (v = 1.5 m/s)",
            "- Phím XUỐNG / S: Dừng lại (v = 0.0 m/s)",
            "- Phím TRÁI / A: Quay góc sang trái (omega = +1.2 rad/s)",
            "- Phím PHẢI / D: Quay góc sang phải (omega = -1.2 rad/s)",
            "- Phím R: Đặt lại vị trí xuất phát",
        ]
        for i, t in enumerate(tips):
            self.screen.blit(self.small_font.render(t, True, TEXT_WHITE), (x + 12, y + 32 + i * 19))

    def _draw_phase_details(self, x: int, y: int) -> None:
        """Chi tiết bổ sung cho các phase 1, 2, 4, 5."""
        p_text = {
            1: [
                "- Không gian trạng thái: 27 chiều (8 biến động học + 19 tia LiDAR).",
                "- Không gian hành động: [v in [0, 2] m/s, omega in [-1.5, 1.5] rad/s].",
                "- Thưởng: +100 khi tới đích, -500 khi va chạm, -0.01 mỗi bước.",
            ],
            2: [
                "- Agent chọn v và omega hoàn toàn ngẫu nhiên không có mục tiêu.",
                "- Va chạm xảy ra chỉ sau 1-2 giây, bị trừ 500 điểm.",
                "- Minh chứng sự cần thiết của tối ưu hóa MDP.",
            ],
            4: [
                "- Mô hình PPO xử lý chuỗi quan sát 27 chiều trong thời gian thực.",
                "- Tự điều chỉnh góc cua theo LiDAR để né vật cản động.",
                "- Cập bến chính xác tâm đích giao hàng, nhận thưởng +100.",
            ],
            5: [
                "- Bấm 'Đổi Seed (S)' để tạo pha và tốc độ vật cản ngẫu nhiên mới.",
                "- Robot phản xạ theo cảm biến LiDAR thời gian thực.",
                "- Không phụ thuộc vào bản đồ tĩnh lưu sẵn.",
            ],
        }
        for i, line in enumerate(p_text.get(self.current_phase, [])):
            self.screen.blit(self.small_font.render(line, True, TEXT_MUTED), (x, y + i * 22))

    def _draw_controls(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ các nút bấm điều khiển phía dưới."""
        self.btn_play.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_step.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_reset.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_speed.draw(self.screen, self.bold_font, mouse_pos)
        self.btn_new_seed.draw(self.screen, self.bold_font, mouse_pos)


def main() -> None:
    """Điểm khởi chạy Demo 2 độc lập."""
    import main as master_launcher
    master_launcher.main_with_screen("demo2")


if __name__ == "__main__":
    main()
