"""Bộ vẽ đồ họa phong cách "hoạt hình đá" cho GridWorld (Demo 1).

Gồm các thành phần vẽ bằng thuần pygame (không cần file ảnh):
- Ô nền đá có vân và vết nứt (get_tile): đá thường, ô bẫy nứt nâu đỏ, ô đích phát sáng xanh.
- Kim cương xanh có số thưởng (draw_gem) cho ô đích.
- Vụ nổ cam có số phạt (draw_explosion) cho ô bẫy.
- Robot nhìn từ trên xuống với 3 mũi tên xanh lá: tiến (80%), trượt trái / phải (10% mỗi bên).
- Chữ khắc chìm trên đá (draw_engraved_text).
"""

from __future__ import annotations

import math
import random

import pygame

Color = tuple[int, int, int]
Point = tuple[float, float]

# Vector hướng trên màn hình (0: Lên, 1: Xuống, 2: Trái, 3: Phải)
HEADING_VEC: dict[int, Point] = {0: (0.0, -1.0), 1: (0.0, 1.0), 2: (-1.0, 0.0), 3: (1.0, 0.0)}
# Góc xoay ngược chiều kim đồng hồ để đưa robot đang hướng lên sang hướng khác
HEADING_ROT: dict[int, int] = {0: 0, 1: 180, 2: 90, 3: -90}

STONE_BASE: Color = (98, 90, 82)
TRAP_BASE: Color = (128, 76, 54)
TILE_EDGE: Color = (34, 29, 26)

_tile_cache: dict[tuple[str, int, int], pygame.Surface] = {}
_font_cache: dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    """Font đậm Segoe UI / Arial theo kích thước (có cache)."""
    size = max(8, size)
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("segoe ui, arial", size, bold=True)
    return _font_cache[size]


def _shade(color: Color, delta: int) -> Color:
    """Làm sáng / tối một màu."""
    return tuple(max(0, min(255, ch + delta)) for ch in color)  # type: ignore[return-value]


def render_outlined_text(
    text: str,
    font: pygame.font.Font,
    color: Color,
    outline: Color,
    thickness: int = 2,
) -> pygame.Surface:
    """Render chữ có viền để nổi bật trên mọi nền."""
    base = font.render(text, True, color)
    border = font.render(text, True, outline)
    surf = pygame.Surface(
        (base.get_width() + 2 * thickness, base.get_height() + 2 * thickness), pygame.SRCALPHA
    )
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx * dx + dy * dy <= thickness * thickness + 1:
                surf.blit(border, (thickness + dx, thickness + dy))
    surf.blit(base, (thickness, thickness))
    return surf


def draw_engraved_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    center: tuple[int, int],
) -> None:
    """Vẽ chữ khắc chìm trên đá (tối, có vệt sáng bên dưới)."""
    light = font.render(text, True, (150, 140, 128))
    dark = font.render(text, True, (38, 32, 28))
    rect = dark.get_rect(center=center)
    surface.blit(light, rect.move(1, 1))
    surface.blit(dark, rect)


def _make_stone(size: int, base: Color, variant: int) -> pygame.Surface:
    """Tạo ô đá nền có vân hạt và vài vết nứt."""
    rng = random.Random(variant * 7919 + size)
    tile = pygame.Surface((size, size))
    tile.fill(base)

    # Mảng loang màu lớn cho cảm giác đá không đều
    for _ in range(10):
        r = rng.randint(size // 8, size // 3)
        blob = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        shade = rng.choice((-14, -8, 8, 12))
        pygame.draw.circle(blob, (*_shade(base, shade), 70), (r, r), r)
        tile.blit(blob, (rng.randint(-r, size - r), rng.randint(-r, size - r)))

    # Hạt li ti
    for _ in range(size * size // 45):
        px, py = rng.randint(0, size - 1), rng.randint(0, size - 1)
        tile.set_at((px, py), _shade(base, rng.choice((-22, -14, 14, 20))))

    # Vết nứt mảnh
    for _ in range(rng.randint(1, 3)):
        x, y = rng.randint(0, size), rng.randint(0, size)
        pts = [(x, y)]
        for _ in range(rng.randint(3, 5)):
            x += rng.randint(-size // 6, size // 6)
            y += rng.randint(-size // 6, size // 6)
            pts.append((x, y))
        pygame.draw.lines(tile, _shade(base, -38), False, pts, 1)

    # Viền nổi: sáng trên-trái, tối dưới-phải
    pygame.draw.line(tile, _shade(base, 26), (0, 0), (size - 1, 0), 2)
    pygame.draw.line(tile, _shade(base, 26), (0, 0), (0, size - 1), 2)
    pygame.draw.line(tile, _shade(base, -34), (0, size - 1), (size - 1, size - 1), 2)
    pygame.draw.line(tile, _shade(base, -34), (size - 1, 0), (size - 1, size - 1), 2)
    return tile


def _make_trap(size: int, variant: int) -> pygame.Surface:
    """Ô bẫy: nền nâu đỏ nứt tỏa tròn từ tâm."""
    rng = random.Random(variant * 104729 + size)
    tile = _make_stone(size, TRAP_BASE, variant)
    c = size / 2

    # Vầng tối ở rìa để ô trũng xuống
    vignette = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(6):
        pygame.draw.rect(vignette, (30, 12, 6, 28), vignette.get_rect().inflate(-i * 6, -i * 6), width=6)
    tile.blit(vignette, (0, 0))

    # Vết nứt tỏa ra từ tâm
    crack = (52, 24, 16)
    for i in range(9):
        ang = 2 * math.pi * i / 9 + rng.uniform(-0.2, 0.2)
        x, y = c, c
        pts = [(x, y)]
        for _ in range(4):
            ang += rng.uniform(-0.35, 0.35)
            step = size * rng.uniform(0.09, 0.15)
            x += math.cos(ang) * step
            y += math.sin(ang) * step
            pts.append((x, y))
        pygame.draw.lines(tile, crack, False, pts, 2)
    return tile


def _make_goal(size: int, variant: int) -> pygame.Surface:
    """Ô đích: đá thường có quầng sáng xanh quanh viên kim cương."""
    tile = _make_stone(size, STONE_BASE, variant)
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(8, 0, -1):
        pygame.draw.circle(glow, (90, 170, 255, 12), (size // 2, int(size * 0.45)), int(size * 0.14 * i * 0.6) + 4)
    tile.blit(glow, (0, 0))
    return tile


def get_tile(kind: str, size: int, variant: int = 0) -> pygame.Surface:
    """Lấy ô nền (kind: 'stone' | 'trap' | 'goal'), có cache theo kích thước và biến thể."""
    key = (kind, size, variant % 8)
    if key not in _tile_cache:
        if kind == "trap":
            _tile_cache[key] = _make_trap(size, variant % 8)
        elif kind == "goal":
            _tile_cache[key] = _make_goal(size, variant % 8)
        else:
            _tile_cache[key] = _make_stone(size, STONE_BASE, variant % 8)
    return _tile_cache[key]


def draw_tile_edge(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Đường kẻ tối giữa các ô đá."""
    pygame.draw.rect(surface, TILE_EDGE, rect, width=2)


def draw_gem(surface: pygame.Surface, center: tuple[int, int], size: float, label: str = "") -> None:
    """Viên kim cương xanh có nhãn phần thưởng (vd '+10') ở giữa."""
    cx, cy = center

    def P(x: float, y: float) -> tuple[int, int]:
        return (int(cx + x * size), int(cy + y * size))

    top_l, top_r = (-0.55, -0.75), (0.55, -0.75)
    left, right, bottom = (-1.0, -0.15), (1.0, -0.15), (0.0, 0.95)
    mid_l, mid_r = (-0.38, -0.15), (0.38, -0.15)

    shadow = pygame.Surface((int(size * 2.6), int(size * 0.8)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
    surface.blit(shadow, shadow.get_rect(center=(cx, int(cy + size * 1.0))))

    facets: list[tuple[Color, list[tuple[float, float]]]] = [
        ((120, 190, 255), [top_l, top_r, mid_r, mid_l]),
        ((70, 140, 245), [left, top_l, mid_l]),
        ((40, 100, 215), [right, top_r, mid_r]),
        ((40, 100, 215), [left, mid_l, bottom]),
        ((62, 130, 240), [mid_l, mid_r, bottom]),
        ((26, 76, 186), [mid_r, right, bottom]),
    ]
    for col, pts in facets:
        pygame.draw.polygon(surface, col, [P(*p) for p in pts])
    outline = [P(*p) for p in (top_l, top_r, right, bottom, left)]
    pygame.draw.polygon(surface, (14, 40, 120), outline, width=2)

    # Tia lấp lánh
    pygame.draw.line(surface, (235, 245, 255), P(-0.35, -0.6), P(-0.15, -0.6), 2)

    if label:
        txt = render_outlined_text(label, _font(int(size * 0.7)), (255, 255, 255), (15, 45, 130), 2)
        surface.blit(txt, txt.get_rect(center=P(0, -0.05)))


_EXPLOSION_SPIKES = (1.0, 0.82, 1.08, 0.9, 0.78, 1.04, 0.86, 1.0, 0.8, 1.06, 0.88, 0.96)


def draw_explosion(surface: pygame.Surface, center: tuple[int, int], radius: float, label: str = "") -> None:
    """Vụ nổ cam nhiều gai có nhãn phạt (vd '-10') ở giữa."""
    cx, cy = center
    n = len(_EXPLOSION_SPIKES)

    def star(scale: float, inner_ratio: float) -> list[tuple[int, int]]:
        pts: list[tuple[int, int]] = []
        for i in range(n):
            a_out = 2 * math.pi * i / n - math.pi / 2
            a_in = a_out + math.pi / n
            r_out = radius * scale * _EXPLOSION_SPIKES[i]
            r_in = radius * scale * inner_ratio
            pts.append((int(cx + math.cos(a_out) * r_out), int(cy + math.sin(a_out) * r_out)))
            pts.append((int(cx + math.cos(a_in) * r_in), int(cy + math.sin(a_in) * r_in)))
        return pts

    pygame.draw.polygon(surface, (232, 96, 18), star(1.0, 0.62))
    pygame.draw.polygon(surface, (150, 48, 8), star(1.0, 0.62), width=2)
    pygame.draw.polygon(surface, (255, 150, 28), star(0.82, 0.62))
    pygame.draw.polygon(surface, (255, 214, 70), star(0.58, 0.62))

    if label:
        txt = render_outlined_text(label, _font(int(radius * 0.8)), (255, 255, 255), (170, 60, 8), 2)
        surface.blit(txt, txt.get_rect(center=(cx, cy)))


def _green_arrow(
    surface: pygame.Surface,
    start: Point,
    vec: Point,
    length: float,
    shaft: float,
    head: float,
) -> None:
    """Mũi tên xanh lá có viền đậm, xuất phát từ `start` theo hướng `vec`."""
    vx, vy = vec
    px, py = -vy, vx
    sx, sy = start
    ex, ey = sx + vx * (length - head), sy + vy * (length - head)
    tx, ty = sx + vx * length, sy + vy * length
    hw = shaft * 2.3
    pts = [
        (sx + px * shaft, sy + py * shaft),
        (ex + px * shaft, ey + py * shaft),
        (ex + px * hw, ey + py * hw),
        (tx, ty),
        (ex - px * hw, ey - py * hw),
        (ex - px * shaft, ey - py * shaft),
        (sx - px * shaft, sy - py * shaft),
    ]
    pygame.draw.polygon(surface, (58, 214, 74), pts)
    pygame.draw.polygon(surface, (16, 96, 34), pts, width=1)


def _robot_body(radius: int) -> pygame.Surface:
    """Thân robot nhìn từ trên xuống, đang hướng lên trên."""
    size = int(radius * 3.4)
    body = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2

    pygame.draw.ellipse(
        body, (0, 0, 0, 80), pygame.Rect(0, 0, int(radius * 2.5), int(radius * 2.2)).move(c - int(radius * 1.25) + 3, c - int(radius * 1.1) + 5)
    )
    # Hai bánh / tay bên hông
    for side in (-1, 1):
        pod = pygame.Rect(0, 0, max(4, int(radius * 0.42)), int(radius * 0.9))
        pod.center = (c + side * int(radius * 1.0), c)
        pygame.draw.rect(body, (112, 118, 130), pod, border_radius=3)
        pygame.draw.rect(body, (52, 56, 66), pod, width=2, border_radius=3)

    pygame.draw.circle(body, (232, 235, 240), (c, c), radius)
    pygame.draw.circle(body, (70, 75, 88), (c, c), radius, width=2)
    pygame.draw.circle(body, (186, 192, 204), (c, c), int(radius * 0.66))
    pygame.draw.circle(body, (110, 116, 128), (c, c), int(radius * 0.66), width=1)
    pygame.draw.circle(body, (36, 40, 48), (c, c), int(radius * 0.44))
    pygame.draw.circle(body, (228, 44, 44), (c, c), int(radius * 0.31))
    pygame.draw.circle(body, (255, 175, 175), (c - int(radius * 0.09), c - int(radius * 0.09)), max(1, int(radius * 0.09)))
    return body


def draw_robot(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    heading: int = 0,
    show_arrows: bool = True,
) -> None:
    """Vẽ robot nhìn từ trên xuống + 3 mũi tên xanh (tiến, trái, phải) theo hướng `heading`."""
    cx, cy = center
    body = pygame.transform.rotate(_robot_body(radius), HEADING_ROT[heading])
    surface.blit(body, body.get_rect(center=(cx, cy)))

    if not show_arrows:
        return
    fx, fy = HEADING_VEC[heading]
    left = (fy, -fx)
    right = (-fy, fx)
    shaft = max(2.0, radius * 0.11)
    head = radius * 0.5

    _green_arrow(surface, (cx + fx * radius * 1.15, cy + fy * radius * 1.15), (fx, fy), radius * 1.0, shaft, head)
    for vec in (left, right):
        _green_arrow(
            surface,
            (cx + vec[0] * radius * 1.4, cy + vec[1] * radius * 1.4),
            vec,
            radius * 0.55,
            shaft * 0.8,
            radius * 0.34,
        )


def heading_from_path(path: list[tuple[int, int]], default: int = 0) -> int:
    """Suy ra hướng nhìn của robot từ bước di chuyển gần nhất (hàng tăng = Lên)."""
    for i in range(len(path) - 1, 0, -1):
        (r1, c1), (r0, c0) = path[i], path[i - 1]
        if (r1, c1) != (r0, c0):
            if r1 > r0:
                return 0
            if r1 < r0:
                return 1
            return 3 if c1 > c0 else 2
    return default

