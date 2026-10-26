"""Trình điều phối trung tâm (Master Application) cho hệ thống mô phỏng MDP.

Tích hợp thống nhất trên một cửa sổ Pygame duy nhất:
- Màn hình rộng rãi hơn (Mặc định 1440 x 840, cho phép mở Toàn màn hình Fullscreen F11 hoặc tùy biến kích thước).
- Thanh điều hướng (Top Navigation Bar) luôn hiển thị ở trên cùng mọi màn hình:
  [ Menu chính (M) ] | [ 1. GridWorld (F1) ] | [ 2. AMR Warehouse (F2) ] | [ ⛶ Toàn màn hình (F11) ]
- Cho phép chuyển đổi tức thì qua lại giữa Menu, Demo 1 và Demo 2 bất kỳ lúc nào mà không bị tắt hay gián đoạn.
- Sử dụng font chữ Segoe UI / Arial chuẩn tương thích 100% tiếng Việt trên Windows.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
import pygame

# Thiết lập DPI awareness trên Windows để font chữ sắc nét
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from demo1 import GridWorldView
from demo2 import WarehouseView


# ===================== BẢNG MÀU GIAO DIỆN =====================
BG_DARK = (15, 23, 42)          # #0F172A
NAVBAR_BG = (17, 24, 39)        # #111827
NAVBAR_BORDER = (51, 65, 85)    # #334155
CARD_BG = (30, 41, 59)          # #1E293B
CARD_BORDER = (51, 65, 85)      # #334155
CARD_HOVER = (45, 60, 85)

TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
CYAN_ACCENT = (56, 189, 248)
GREEN_ACCENT = (52, 211, 153)
AMBER_ACCENT = (251, 191, 36)

NAV_BTN_NORMAL = (30, 41, 59)
NAV_BTN_HOVER = (51, 65, 85)
NAV_BTN_ACTIVE = (2, 132, 199)


@dataclass(slots=True)
class NavButton:
    """Nút bấm trên thanh điều hướng đầu trang."""

    rect: pygame.Rect
    text: str
    target_screen: str

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int], is_active: bool) -> None:
        """Vẽ nút bấm điều hướng với trạng thái active/hover."""
        if is_active:
            bg_col = NAV_BTN_ACTIVE
            border_col = CYAN_ACCENT
        elif self.rect.collidepoint(mouse_pos):
            bg_col = NAV_BTN_HOVER
            border_col = (100, 116, 139)
        else:
            bg_col = NAV_BTN_NORMAL
            border_col = NAVBAR_BORDER

        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=6)

        text_col = TEXT_WHITE if is_active else (226, 232, 240)
        text_surf = font.render(self.text, True, text_col)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))


class TopNavBar:
    """Thanh điều hướng cố định trên cùng màn hình."""

    def __init__(self, width: int = 1280, height: int = 46) -> None:
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont("segoe ui, arial", 13, bold=True)
        self.logo_font = pygame.font.SysFont("segoe ui, arial", 15, bold=True)

        # 4 Nút trên thanh điều hướng (Menu, Demo 1, Demo 2, Fullscreen)
        self.buttons = [
            NavButton(pygame.Rect(440, 6, 135, 32), "[ Menu (M) ]", "menu"),
            NavButton(pygame.Rect(585, 6, 215, 32), "[ 1. GridWorld (F1) ]", "demo1"),
            NavButton(pygame.Rect(810, 6, 225, 32), "[ 2. AMR Warehouse (F2) ]", "demo2"),
            NavButton(pygame.Rect(1045, 6, 215, 32), "[ ⛶ Toàn màn hình (F11) ]", "toggle_fullscreen"),
        ]

    def draw(self, surface: pygame.Surface, active_screen: str, mouse_pos: tuple[int, int]) -> None:
        """Vẽ thanh điều hướng."""
        bar_rect = pygame.Rect(0, 0, self.width, self.height)
        pygame.draw.rect(surface, NAVBAR_BG, bar_rect)
        pygame.draw.line(surface, NAVBAR_BORDER, (0, self.height), (self.width, self.height), width=1)

        # Tiêu đề logo ứng dụng
        logo_text = self.logo_font.render("MDP SIMULATION SUITE", True, CYAN_ACCENT)
        surface.blit(logo_text, (20, 13))

        sub_logo = self.font.render("|  AI & Reinforcement Learning", True, TEXT_MUTED)
        surface.blit(sub_logo, (215, 13))

        # Các nút chuyển màn hình
        for btn in self.buttons:
            is_active = (btn.target_screen == active_screen)
            btn.draw(surface, self.font, mouse_pos, is_active)

    def handle_click(self, mouse_pos: tuple[int, int]) -> str | None:
        """Kiểm tra chuột có click trúng nút điều hướng nào không."""
        for btn in self.buttons:
            if btn.rect.collidepoint(mouse_pos):
                return btn.target_screen
        return None


class MenuView:
    """Màn hình Menu chọn lựa bài thuyết trình."""

    def __init__(self, screen: pygame.Surface, width: int = 1280, height: int = 780) -> None:
        self.screen = screen
        self.width = width
        self.height = height

        self.title_font = pygame.font.SysFont("segoe ui, arial", 24, bold=True)
        self.subtitle_font = pygame.font.SysFont("segoe ui, arial", 15)
        self.card_title_font = pygame.font.SysFont("segoe ui, arial", 19, bold=True)
        self.bold_font = pygame.font.SysFont("segoe ui, arial", 14, bold=True)
        self.regular_font = pygame.font.SysFont("segoe ui, arial", 13)
        self.small_font = pygame.font.SysFont("segoe ui, arial", 11)

        # 2 Khung lựa chọn Demo 1 và Demo 2
        self.card1_rect = pygame.Rect(110, 175, 490, 470)
        self.card2_rect = pygame.Rect(680, 175, 490, 470)

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> str | None:
        """Xử lý sự kiện click chọn thẻ hoặc bấm phím tắt."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                return "demo1"
            elif event.key == pygame.K_2:
                return "demo2"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.card1_rect.collidepoint(mouse_pos):
                return "demo1"
            elif self.card2_rect.collidepoint(mouse_pos):
                return "demo2"
        return None

    def update(self, current_time: int) -> None:
        """Cập nhật logic menu nếu cần."""
        pass

    def draw(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ giao diện menu."""
        # Tiêu đề chính
        title = self.title_font.render("HỆ THỐNG MÔ PHỎNG MARKOV DECISION PROCESSES (MDP)", True, CYAN_ACCENT)
        self.screen.blit(title, title.get_rect(center=(self.width // 2, 85)))

        sub = self.subtitle_font.render("Bộ công cụ minh họa trực quan phục vụ bài thuyết trình môn Học Tăng Cường & CSAI", True, TEXT_MUTED)
        self.screen.blit(sub, sub.get_rect(center=(self.width // 2, 120)))

        msg = self.bold_font.render("Bấm phím [1] hoặc [2] (hoặc Click vào khung) để khởi chạy từng phần:", True, TEXT_WHITE)
        self.screen.blit(msg, msg.get_rect(center=(self.width // 2, 148)))

        self._draw_card1(mouse_pos)
        self._draw_card2(mouse_pos)
        self._draw_footer()

    def _draw_card1(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ thẻ lựa chọn Demo 1."""
        is_hover = self.card1_rect.collidepoint(mouse_pos)
        bg_col = CARD_HOVER if is_hover else CARD_BG
        border_col = CYAN_ACCENT if is_hover else CARD_BORDER

        pygame.draw.rect(self.screen, bg_col, self.card1_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_col, self.card1_rect, width=2, border_radius=12)

        badge_rect = pygame.Rect(self.card1_rect.x + 20, self.card1_rect.y + 20, 110, 28)
        pygame.draw.rect(self.screen, (2, 132, 199), badge_rect, border_radius=6)
        b_txt = self.bold_font.render("PHẦN 1", True, TEXT_WHITE)
        self.screen.blit(b_txt, b_txt.get_rect(center=badge_rect.center))

        t = self.card_title_font.render("GridWorld 4x4 & Quy hoạch động", True, TEXT_WHITE)
        self.screen.blit(t, (self.card1_rect.x + 20, self.card1_rect.y + 60))

        sub = self.small_font.render("Minh họa lý thuyết cốt lõi (Slide 09/12 trong Kịch bản)", True, CYAN_ACCENT)
        self.screen.blit(sub, (self.card1_rect.x + 20, self.card1_rect.y + 92))

        features = [
            ("Không gian trạng thái:", "16 ô lưới rời rạc, có 2 ô bẫy tử thần (-10)"),
            ("Động lực ngẫu nhiên:", "Xác suất trượt 80/10/10 (Stochastic dynamics)"),
            ("Thuật toán giải tối ưu:", "Value Iteration (48 vòng) & Policy Iteration (2 vòng)"),
            ("Bản chất toán học MDP:", "Toán Bellman tự cân bằng rủi ro để né bẫy"),
            ("So sánh trực tiếp:", "2 ma trận cạnh nhau: Tối ưu pi* vs Sát bẫy"),
        ]

        start_y = self.card1_rect.y + 130
        for i, (k, v) in enumerate(features):
            k_s = self.bold_font.render(f"• {k}", True, TEXT_WHITE)
            v_s = self.regular_font.render(v, True, TEXT_MUTED)
            self.screen.blit(k_s, (self.card1_rect.x + 25, start_y + i * 46))
            self.screen.blit(v_s, (self.card1_rect.x + 40, start_y + i * 46 + 20))

        btn_rect = pygame.Rect(self.card1_rect.x + 30, self.card1_rect.bottom - 65, self.card1_rect.w - 60, 44)
        btn_col = (2, 132, 199) if is_hover else (30, 58, 138)
        pygame.draw.rect(self.screen, btn_col, btn_rect, border_radius=8)
        btn_txt = self.bold_font.render("Khởi chạy Demo 1 [ Phím 1 / F1 ] ->", True, TEXT_WHITE)
        self.screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

    def _draw_card2(self, mouse_pos: tuple[int, int]) -> None:
        """Vẽ thẻ lựa chọn Demo 2."""
        is_hover = self.card2_rect.collidepoint(mouse_pos)
        bg_col = CARD_HOVER if is_hover else CARD_BG
        border_col = GREEN_ACCENT if is_hover else CARD_BORDER

        pygame.draw.rect(self.screen, bg_col, self.card2_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_col, self.card2_rect, width=2, border_radius=12)

        badge_rect = pygame.Rect(self.card2_rect.x + 20, self.card2_rect.y + 20, 110, 28)
        pygame.draw.rect(self.screen, (16, 185, 129), badge_rect, border_radius=6)
        b_txt = self.bold_font.render("PHẦN 2", True, TEXT_WHITE)
        self.screen.blit(b_txt, b_txt.get_rect(center=badge_rect.center))

        t = self.card_title_font.render("Robot AMR Warehouse & Deep RL (PPO)", True, TEXT_WHITE)
        self.screen.blit(t, (self.card2_rect.x + 20, self.card2_rect.y + 60))

        sub = self.small_font.render("Ứng dụng thực tế công nghiệp (Slide 11/12 trong Kịch bản)", True, GREEN_ACCENT)
        self.screen.blit(sub, (self.card2_rect.x + 20, self.card2_rect.y + 92))

        features = [
            ("Môi trường nhà kho 2D:", "Kích thước 20m x 12m, 5 kệ hàng A-E, 1 chướng ngại động"),
            ("Hệ cảm biến LiDAR:", "19 tia quét 180 độ mô phỏng thời gian thực"),
            ("Không gian liên tục:", "Vận tốc dài v in [0, 2] m/s, góc quay w in [-1.5, 1.5] rad/s"),
            ("Mô hình AI huấn luyện:", "Proximal Policy Optimization (PPO - 200,000 steps)"),
            ("Hiệu năng kiểm chứng:", "Tỉ lệ thành công 76-80%, né vật cản linh hoạt"),
        ]

        start_y = self.card2_rect.y + 130
        for i, (k, v) in enumerate(features):
            k_s = self.bold_font.render(f"• {k}", True, TEXT_WHITE)
            v_s = self.regular_font.render(v, True, TEXT_MUTED)
            self.screen.blit(k_s, (self.card2_rect.x + 25, start_y + i * 46))
            self.screen.blit(v_s, (self.card2_rect.x + 40, start_y + i * 46 + 20))

        btn_rect = pygame.Rect(self.card2_rect.x + 30, self.card2_rect.bottom - 65, self.card2_rect.w - 60, 44)
        btn_col = (16, 185, 129) if is_hover else (6, 95, 70)
        pygame.draw.rect(self.screen, btn_col, btn_rect, border_radius=8)
        btn_txt = self.bold_font.render("Khởi chạy Demo 2 [ Phím 2 / F2 ] ->", True, TEXT_WHITE)
        self.screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

    def _draw_footer(self) -> None:
        """Vẽ hướng dẫn chân trang."""
        hint = self.small_font.render("Phím tắt tiện lợi: [F1 / 1] Demo 1 | [F2 / 2] Demo 2 | [M] Menu chính | [F11] Toàn màn hình | [Q / Esc] Thoát", True, TEXT_MUTED)
        self.screen.blit(hint, hint.get_rect(center=(self.width // 2, self.height - 24)))


class MasterApp:
    """Ứng dụng tổng hợp điều phối luồng giao diện toàn bộ bài thuyết trình."""

    def __init__(self, initial_screen: str = "menu") -> None:
        pygame.init()
        pygame.font.init()

        # Kích thước canvas ảo chuẩn
        self.base_w = 1280
        self.base_h = 780
        self.virtual_surface = pygame.Surface((self.base_w, self.base_h))

        # Nhận diện kích thước màn hình thiết bị
        info = pygame.display.Info()
        self.monitor_w = info.current_w
        self.monitor_h = info.current_h

        # Kích thước cửa sổ mặc định to hơn, vừa mắt và sang trọng (1440x840 hoặc vừa màn hình)
        self.win_w = min(1440, self.monitor_w)
        self.win_h = min(840, self.monitor_h - 60)
        self.is_fullscreen = False

        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
        pygame.display.set_caption("MDP Simulation Suite – AI & Reinforcement Learning")
        self.clock = pygame.time.Clock()

        # Thanh điều hướng và các màn hình con (vẽ lên canvas ảo 1280x780)
        self.nav_bar = TopNavBar(self.base_w, 46)
        self.menu_view = MenuView(self.virtual_surface, self.base_w, self.base_h)
        self.demo1_view = GridWorldView(self.virtual_surface, self.base_w, self.base_h)
        self.demo2_view = WarehouseView(self.virtual_surface, self.base_w, self.base_h)

        self.current_screen = initial_screen

    def toggle_fullscreen(self) -> None:
        """Bật/tắt chế độ toàn màn hình Fullscreen không viền sắc nét trên Windows."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
            self.screen = pygame.display.set_mode((self.monitor_w, self.monitor_h), pygame.NOFRAME)
            self.nav_bar.buttons[3].text = "[ 🗗 Cửa sổ (F11) ]"
        else:
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
            self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
            self.nav_bar.buttons[3].text = "[ ⛶ Toàn màn hình (F11) ]"

    def get_virtual_mouse_pos(self, screen_mouse_pos: tuple[int, int]) -> tuple[int, int]:
        """Quy đổi tọa độ chuột từ cửa sổ thực tế sang canvas ảo 1280x780."""
        cur_w, cur_h = self.screen.get_size()
        scale = min(cur_w / self.base_w, cur_h / self.base_h)
        render_w = int(self.base_w * scale)
        render_h = int(self.base_h * scale)
        offset_x = (cur_w - render_w) // 2
        offset_y = (cur_h - render_h) // 2

        mx, my = screen_mouse_pos
        vx = int((mx - offset_x) / scale)
        vy = int((my - offset_y) / scale)
        return (max(0, min(self.base_w - 1, vx)), max(0, min(self.base_h - 1, vy)))

    def set_screen(self, screen_name: str) -> None:
        """Chuyển đổi màn hình hiển thị tức thì."""
        if screen_name in ("menu", "demo1", "demo2"):
            self.current_screen = screen_name
            if screen_name == "demo1":
                self.demo1_view.reset_agent()
            elif screen_name == "demo2":
                self.demo2_view.reset_episode()

    def run(self) -> None:
        """Vòng lặp chính của ứng dụng."""
        running = True

        while running:
            current_time = pygame.time.get_ticks()
            screen_mouse_pos = pygame.mouse.get_pos()
            virt_mouse_pos = self.get_virtual_mouse_pos(screen_mouse_pos)

            # 1. Xử lý sự kiện
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:
                        self.win_w = max(1000, event.w)
                        self.win_h = max(600, event.h)
                        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                        continue
                    elif event.key in (pygame.K_ESCAPE, pygame.K_q) and self.current_screen == "menu":
                        running = False
                    elif event.key == pygame.K_F1:
                        self.set_screen("demo1")
                        continue
                    elif event.key == pygame.K_F2:
                        self.set_screen("demo2")
                        continue
                    elif event.key == pygame.K_m or (event.key == pygame.K_ESCAPE and self.current_screen != "menu"):
                        self.set_screen("menu")
                        continue

                # Kiểm tra click vào thanh điều hướng trên cùng
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and virt_mouse_pos[1] <= self.nav_bar.height:
                    nav_target = self.nav_bar.handle_click(virt_mouse_pos)
                    if nav_target == "toggle_fullscreen":
                        self.toggle_fullscreen()
                        continue
                    elif nav_target is not None:
                        self.set_screen(nav_target)
                        continue

                # Phân phối sự kiện đến màn hình con đang kích hoạt
                if self.current_screen == "menu":
                    next_scr = self.menu_view.handle_event(event, virt_mouse_pos)
                    if next_scr is not None:
                        self.set_screen(next_scr)
                elif self.current_screen == "demo1":
                    self.demo1_view.handle_event(event, virt_mouse_pos)
                elif self.current_screen == "demo2":
                    self.demo2_view.handle_event(event, virt_mouse_pos)

            # 2. Cập nhật logic màn hình con
            if self.current_screen == "menu":
                self.menu_view.update(current_time)
            elif self.current_screen == "demo1":
                self.demo1_view.update(current_time)
            elif self.current_screen == "demo2":
                self.demo2_view.update(current_time)

            # 3. Vẽ đồ họa lên canvas ảo
            self.virtual_surface.fill(BG_DARK)

            if self.current_screen == "menu":
                self.menu_view.draw(virt_mouse_pos)
            elif self.current_screen == "demo1":
                self.demo1_view.draw(virt_mouse_pos)
            elif self.current_screen == "demo2":
                self.demo2_view.draw(virt_mouse_pos)

            # Luôn vẽ thanh điều hướng đè lên trên cùng canvas ảo
            self.nav_bar.draw(self.virtual_surface, self.current_screen, virt_mouse_pos)

            # 4. Scale canvas ảo lên màn hình thực tế (smoothscale)
            cur_w, cur_h = self.screen.get_size()
            scale = min(cur_w / self.base_w, cur_h / self.base_h)
            render_w = int(self.base_w * scale)
            render_h = int(self.base_h * scale)
            offset_x = (cur_w - render_w) // 2
            offset_y = (cur_h - render_h) // 2

            scaled_surf = pygame.transform.smoothscale(self.virtual_surface, (render_w, render_h))
            self.screen.fill((10, 15, 30))
            self.screen.blit(scaled_surf, (offset_x, offset_y))

            pygame.display.flip()
            self.clock.tick(30)

        pygame.quit()
        sys.exit()


def main_with_screen(initial_screen: str = "menu") -> None:
    """Khởi chạy ứng dụng với màn hình chỉ định."""
    app = MasterApp(initial_screen=initial_screen)
    app.run()


def main() -> None:
    """Điểm vào chương trình."""
    parser = argparse.ArgumentParser(description="MDP Simulation Launcher")
    parser.add_argument("--demo", type=int, choices=[1, 2], help="Launch demo directly (1 or 2)")
    args = parser.parse_args()

    screen_target = "menu"
    if args.demo == 1:
        screen_target = "demo1"
    elif args.demo == 2:
        screen_target = "demo2"

    main_with_screen(screen_target)


if __name__ == "__main__":
    main()
