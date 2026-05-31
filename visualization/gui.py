from __future__ import annotations
import sys
import threading
import os

from visualization.terminal import COLOR_MAP
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = ''
import pygame
from parsing.parser import Parser
from pathfinding.routing import Pathfinder
from simulation.engine import COLORS, RESET, Simulation

NODE_COLORS = {
    "start_hub":  (0, 170, 85),
    "end_hub":    (170, 0, 68),
    "hub":        (51, 68, 102),
    "restricted": (95, 42, 30),
    "blocked":    (58, 0, 0),
    "priority":   (30, 95, 42),
}

DRONE_COLORS = [(0, 255, 255), (255, 136, 0), (255, 0, 255), (255, 255, 0)]
PLAY_INTERVAL = 0.4
ANIM_SPEED = 0.35


class GUI:
    def __init__(self, map_path: str) -> None:
        self.steps      = []
        self.cur        = 0
        self.playing    = False
        self.play_timer = 0.0

        self.scale = 1.0
        self.ox    = 50.0
        self.oy    = 50.0


        self.drag  = False
        self.drag0 = (0, 0)
        self.ox0   = 0.0
        self.oy0   = 0.0

        # Animation state
        self.src: dict[int, tuple[float, float]] = {}
        self.tgt: dict[int, tuple[float, float]] = {}
        self.t:   dict[int, float] = {}

        self._lead_map_file(map_path)
        self._init_pygame()
        self._run_gui()

    # ── Setup ─────────────────────────────────────────────────────────

    def _lead_map_file(self, path):
        with open(path) as f:
            try:
                parsed = Parser(f)
                self.nodes  = parsed.nodes
                self.drones = parsed.drones
            except Exception as err:
                print(COLOR_MAP["red"],"Error: ", err, RESET)
                sys.exit(1)

    def _init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1300, 950), pygame.RESIZABLE)
        icon = pygame.image.load('icons/drone-icon.png')
        pygame.display.set_icon(icon)
        pygame.display.set_caption("Drone Simulation")
        self.font = pygame.font.SysFont("Consolas", 13, bold=True)

    def _run_gui(self) -> None:
        raw   = {n.name: (float(n.x), float(n.y)) for n in self.nodes}
        max_y = max(y for _, y in raw.values())
        self.pos = {k: (x, max_y - y -1) for k, (x, y) in raw.items()}

        self._fit_view()
        self._reset_anim()
        try:
            Pathfinder(self.drones, self.nodes)
        except Exception as err:
            print(COLORS[0],"Error: ", err, RESET)
            sys.exit(1)

        sim = Simulation(self.drones, self.nodes)
        threading.Thread(
            target=sim.run,
            kwargs={"on_step": lambda _t, snap: self.steps.append(snap)},
            daemon=True,
        ).start()

    def _fit_view(self) -> None:
        W, H = self.screen.get_size()
        xs   = [p[0] for p in self.pos.values()]
        ys   = [p[1] for p in self.pos.values()]
        self.scale = min((W - 160) / max(max(xs) - min(xs), 1),
                         (H - 210) / max(max(ys) - min(ys), 1))
        self.ox = (W - (max(xs) - min(xs)) * self.scale) / 2 - min(xs) * self.scale
        self.oy = (H - (max(ys) - min(ys)) * self.scale) / 2 - min(ys) * self.scale

    def _reset_anim(self) -> None:
        start = self.pos.get(self.nodes[0].name, (0.0, 0.0))
        for d in self.drones:
            self.src[d.id] = start
            self.tgt[d.id] = start
            self.t[d.id] = 1.0

    # ── Helpers ───────────────────────────────────────────────────────

    def _to_screen(self, x: float, y: float) -> tuple[int, int]:
        return (int(x * self.scale + self.ox),
                int(y * self.scale + self.oy + 50))

    def _interp(self, did: int) -> tuple[float, float]:
        """Smooth interpolation between source and target positions."""
        p = self.t[did]
        # Smoothstep easing
        e = p * p * (3 - 2 * p)
        sx, sy = self.src[did]
        tx, ty = self.tgt[did]
        return sx + (tx - sx) * e, sy + (ty - sy) * e

    def _label(self, text: str, color: tuple, cx: int, cy: int) -> None:
        surf = self.font.render(str(text), True, color)
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _drone_color(self, did: int) -> tuple:
        return DRONE_COLORS[(did - 1) % len(DRONE_COLORS)]

    def _current_zones(self) -> set[str]:
        if not (self.steps and self.cur > 0):
            return set()
        return {info.get("zone", "")
                for info in self.steps[self.cur - 1].values()
                if isinstance(info, dict)}

    # ── Playback ──────────────────────────────────────────────────────

    def _apply_step(self, index: int) -> None:
        if not (self.steps and 0 <= index < len(self.steps)):
            return
        for d in self.drones:
            info = self.steps[index].get(d.id, {})
            zone = info.get("zone", "")
            if zone not in self.pos:
                continue
            wx, wy = self.pos[zone]
            # Start animation if position changed
            if (wx, wy) != self.tgt[d.id]:
                self.src[d.id] = self._interp(d.id)
                self.tgt[d.id] = (wx, wy)
                self.t[d.id] = 0.0

    def _fwd(self) -> None:
        if self.steps and self.cur < len(self.steps):
            self._apply_step(self.cur)
            self.cur += 1

    def _bwd(self) -> None:
        if self.cur <= 0:
            return
        self.cur -= 1
        self._apply_step(self.cur - 1) if self.cur > 0 else self._reset()

    def _reset(self) -> None:
        self.playing = False
        self.cur = 0
        self._reset_anim()

    def _toggle_play(self) -> None:
        if not self.steps:
            return
        self.playing = not self.playing
        if self.playing and self.cur >= len(self.steps):
            self.cur = 0

    # ── Drawing ───────────────────────────────────────────────────────

    def _draw(self) -> None:
        self.screen.fill((15, 15, 30))
        self._draw_edges()
        self._draw_nodes()
        self._draw_drones()
        self._draw_toolbar()
        pygame.display.flip()

    def _draw_edges(self) -> None:
        seen: set[frozenset] = set()
        for node in self.nodes:
            for nb, _ in node.connections:
                key = frozenset([node.name, nb])
                if key in seen or nb not in self.pos:
                    continue
                seen.add(key)
                pygame.draw.line(self.screen, (40, 60, 80),
                                 self._to_screen(*self.pos[node.name]),
                                 self._to_screen(*self.pos[nb]), 2)

    def _draw_nodes(self) -> None:
        occupied = self._current_zones()
        icons    = {"start_hub": "S", "end_hub": "E", "hub": "H"}
        for node in self.nodes:
            if node.name not in self.pos:
                continue
            cx, cy = self._to_screen(*self.pos[node.name])
            active = node.name in occupied
            
            # Fix zone specific coloring for normal/restricted/blocked hubs
            if node.map_definition == "hub":
                color = NODE_COLORS.get(node.zone, NODE_COLORS["hub"])
            else:
                color = NODE_COLORS.get(node.map_definition, (51, 68, 102))
                
            pygame.draw.circle(self.screen, color, (cx, cy), 20)
            pygame.draw.circle(self.screen,
                               (255, 255, 255) if active else (68, 102, 136),
                               (cx, cy), 20, 3 if active else 1)
            self._label(icons.get(node.map_definition, "."), (255, 255, 255), cx, cy)
            self._label(node.name, (170, 187, 204), cx, cy + 30)


    def _group_offset(self, index: int, group_size: int) -> tuple[int, int]:
        """
        Calculate (dx, dy) pixel offset for a drone within a group sharing
        the same node so all drones remain visible without overlapping.

        Layout strategy:
        - 1 drone  → no offset (centered on node)
        - 2 drones → side by side horizontally
        - 3+ drones → arranged in a circle around the node center
        """
        if group_size == 1:
            return (0, 0)

        if group_size == 2:
            # Simple horizontal split: left and right
            offsets = [(-10, 0), (10, 0)]
            return offsets[index]

        # For 3 or more, distribute evenly around a circle
        import math
        radius = 10 + (group_size - 3) * 2   # Slightly expand radius for larger groups
        angle = (2 * math.pi / group_size) * index - math.pi / 2  # Start from top
        dx = int(round(radius * math.cos(angle)))
        dy = int(round(radius * math.sin(angle)))
        return (dx, dy)

    def _draw_drones(self) -> None:
        # Group drones by their interpolated screen position (snapped to grid)
        position_groups: dict[tuple[int, int], list[int]] = {}

        for d in self.drones:
            cx, cy = self._to_screen(*self._interp(d.id))
            key = (cx, cy)
            position_groups.setdefault(key, []).append(d.id)

        # Build a lookup: drone_id -> (cx, cy, index_in_group, group_size)
        drone_render_info: dict[int, tuple[int, int, int, int]] = {}
        for (cx, cy), group in position_groups.items():
            for index, did in enumerate(group):
                drone_render_info[did] = (cx, cy, index, len(group))

        for d in self.drones:
            cx, cy, index, group_size = drone_render_info[d.id]

            # Calculate offset so drones fan out when sharing a node
            offset_x, offset_y = self._group_offset(index, group_size)
            cx += offset_x
            cy += offset_y

            color = self._drone_color(d.id)

            arrived = False
            if self.steps and self.cur > 0:
                arrived = self.steps[self.cur - 1].get(d.id, {}).get("arrived", False)

            pygame.draw.circle(self.screen, color, (cx, cy), 9)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 9, 2)
            self._label("!" if arrived else f"D{d.id}", (0, 0, 0), cx, cy)

    def _draw_toolbar(self) -> None:
        W      = self.screen.get_width()
        mx, my = pygame.mouse.get_pos()
        pygame.draw.rect(self.screen, (22, 33, 62), (0, 0, W, 50))
        for bx, label in [(10, "Pause" if self.playing else "Play"),
                          (110, "Reset"), (210, "< Back"), (310, "Fwd >")]:
            rect = pygame.Rect(bx, 8, 90, 34)
            pygame.draw.rect(self.screen,
                             (26, 90, 154) if rect.collidepoint(mx, my) else (15, 52, 96),
                             rect, border_radius=4)
            self._label(label, (255, 255, 255), *rect.center)
        surf = self.font.render(f"Step {self.cur} / {len(self.steps)}",
                                True, (170, 170, 170))
        self.screen.blit(surf, (W - surf.get_width() - 16, 16))

    # ── Events ────────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            elif event.type == pygame.KEYDOWN:
                {pygame.K_RIGHT:  self._fwd,
                 pygame.K_LEFT:   self._bwd,
                 pygame.K_r:      self._reset,
                 pygame.K_SPACE:  self._toggle_play,
                 pygame.K_ESCAPE: (lambda: (pygame.quit(), exit())),
                 }.get(event.key, lambda: None)()

            elif event.type == pygame.VIDEORESIZE:
                self._fit_view()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my < 50:
                    if   10  <= mx <= 100: self._toggle_play()
                    elif 110 <= mx <= 200: self._reset()
                    elif 210 <= mx <= 300: self._bwd()
                    elif 310 <= mx <= 400: self._fwd()
                else:
                    self.drag  = True
                    self.drag0 = event.pos
                    self.ox0, self.oy0 = self.ox, self.oy

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.drag = False

            elif event.type == pygame.MOUSEMOTION and self.drag:
                self.ox = self.ox0 + event.pos[0] - self.drag0[0]
                self.oy = self.oy0 + event.pos[1] - self.drag0[1]

            elif event.type == pygame.MOUSEWHEEL:
                f = 1.1 if event.y > 0 else 0.9
                mx, my = pygame.mouse.get_pos()
                self.scale *= f
                self.ox = mx - f * (mx - self.ox)
                self.oy = my - f * (my - self.oy)

    # ── Main loop ─────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        # Update animation progress for all drones
        for d in self.drones:
            if self.t[d.id] < 1.0:
                self.t[d.id] = min(1.0, self.t[d.id] + dt / ANIM_SPEED)

        # Auto-play
        if self.playing and self.steps:
            self.play_timer += dt
            if self.play_timer >= PLAY_INTERVAL:
                self.play_timer = 0.0
                if self.cur < len(self.steps):
                    self._fwd()
                else:
                    self.playing = False

    def run(self) -> None:
        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(60) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()