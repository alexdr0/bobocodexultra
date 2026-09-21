"""BCU terminal arcade: three original, offline games using stdlib curses."""

from __future__ import annotations

import curses
from collections import deque
import math
import random
import sys
import time
from dataclasses import dataclass


class GameError(Exception):
    pass


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_write(screen, row, col, value, style=0):
    height, width = screen.getmaxyx()
    if 0 <= row < height and 0 <= col < width:
        try:
            screen.addstr(row, col, str(value)[:max(0, width - col - 1)], style)
        except curses.error:
            pass


def palette():
    if not curses.has_colors():
        return lambda _: 0
    curses.start_color()
    try:
        curses.use_default_colors()
        background = -1
    except curses.error:
        background = curses.COLOR_BLACK
    for number, foreground in enumerate((curses.COLOR_CYAN, curses.COLOR_MAGENTA,
                                         curses.COLOR_GREEN, curses.COLOR_YELLOW,
                                         curses.COLOR_RED, curses.COLOR_BLUE), 1):
        curses.init_pair(number, foreground, background)
    return curses.color_pair


def frame(screen, minimum_width, minimum_height, render, update, key_handler, fps=15):
    screen.nodelay(True)
    screen.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    color = palette()
    paused = False
    next_frame = time.monotonic()
    while True:
        key = screen.getch()
        if key in (ord("q"), ord("Q"), 27):
            return
        if key in (ord("p"), ord("P")):
            paused = not paused
        elif not paused:
            key_handler(key)
        height, width = screen.getmaxyx()
        screen.erase()
        if width < minimum_width or height < minimum_height:
            safe_write(screen, 1, 2, f"Resize terminal to at least {minimum_width} x {minimum_height}.")
            safe_write(screen, 3, 2, "Q or Esc quits.")
            next_frame = time.monotonic() + 0.15
        else:
            now = time.monotonic()
            if not paused and now >= next_frame:
                update()
                next_frame = now + 1 / fps
            render(screen, color)
            if paused:
                safe_write(screen, height - 2, 2, "PAUSED · P resume · Q quit", color(4))
        screen.refresh()
        time.sleep(0.018)


class Snake:
    def __init__(self, width=48, height=20, rng=None):
        self.width, self.height = width, height
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        middle = (self.width // 2, self.height // 2)
        self.body = [(middle[0] - i, middle[1]) for i in range(4)]
        self.direction = (1, 0)
        self.turned = False
        self.score = 0
        self.alive = True
        self.won = False
        self.food = self.place_food()

    def place_food(self):
        empty = [(x, y) for y in range(self.height) for x in range(self.width)
                 if (x, y) not in self.body]
        return self.rng.choice(empty) if empty else None

    def turn(self, direction):
        if not self.turned and direction != self.direction and direction != tuple(-v for v in self.direction):
            self.direction = direction
            self.turned = True

    def step(self):
        if not self.alive:
            return
        head = tuple(a + b for a, b in zip(self.body[0], self.direction))
        eating = head == self.food
        occupied = self.body if eating else self.body[:-1]
        if not 0 <= head[0] < self.width or not 0 <= head[1] < self.height or head in occupied:
            self.alive = False
            return
        self.body.insert(0, head)
        if eating:
            self.score += 10
            self.food = self.place_food()
            if self.food is None:
                self.alive, self.won = False, True
        else:
            self.body.pop()
        self.turned = False


def play_snake(screen):
    height, width = screen.getmaxyx()
    game = Snake(clamp(width - 4, 26, 70), clamp(height - 8, 12, 28))
    ticks = 0

    def keys(key):
        directions = {curses.KEY_UP: (0, -1), ord("w"): (0, -1),
                      curses.KEY_DOWN: (0, 1), ord("s"): (0, 1),
                      curses.KEY_LEFT: (-1, 0), ord("a"): (-1, 0),
                      curses.KEY_RIGHT: (1, 0), ord("d"): (1, 0)}
        if key in directions:
            game.turn(directions[key])
        if key in (ord("r"), ord("R")):
            game.reset()

    def update():
        nonlocal ticks
        ticks += 1
        if ticks % max(2, 5 - game.score // 70) == 0:
            game.step()

    def render(screen, color):
        screen_height, screen_width = screen.getmaxyx()
        left = (screen_width - game.width - 2) // 2
        safe_write(screen, 1, left, "✦ S N A K E".ljust(game.width) + f"{game.score:>3}", color(3))
        safe_write(screen, 2, left, "╔" + "═" * game.width + "╗", color(1))
        body = set(game.body[1:])
        for row in range(game.height):
            cells = [" "] * game.width
            if game.food and game.food[1] == row:
                cells[game.food[0]] = "◆"
            for x, y in body:
                if y == row:
                    cells[x] = "●"
            if game.body[0][1] == row:
                cells[game.body[0][0]] = "◉"
            safe_write(screen, row + 3, left, "║" + "".join(cells) + "║", color(3))
        safe_write(screen, game.height + 3, left, "╚" + "═" * game.width + "╝", color(1))
        safe_write(screen, game.height + 5, left, "Arrows / WASD steer  ·  P pause  ·  R restart  ·  Q quit", color(1))
        if not game.alive:
            safe_write(screen, game.height + 6, left, "YOU WIN!" if game.won else "GAME OVER  ·  R to try again", color(4))

    frame(screen, 34, 20, render, update, keys, 18)


class Pong:
    def __init__(self, width=62, height=20, rng=None):
        self.width, self.height = width, height
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.player = self.ai = (self.height - 5) / 2
        self.points = [0, 0]
        self.ticks = 0
        self.winner = None
        self.serve(self.rng.choice((-1, 1)))

    def serve(self, direction):
        self.x, self.y = self.width / 2, self.height / 2
        self.vx, self.vy = direction * 0.8, self.rng.choice((-0.32, 0.32))

    def move(self, amount):
        self.player = clamp(self.player + amount, 1, self.height - 6)

    def step(self):
        if self.winner is not None:
            return
        self.ticks += 1
        self.ai = clamp(self.ai + clamp(self.y - (self.ai + 2) + math.sin(self.ticks / 12) * 1.6,
                                        -0.35, 0.35), 1, self.height - 6)
        self.x += self.vx
        self.y += self.vy
        if self.y <= 1 or self.y >= self.height - 2:
            self.y = clamp(self.y, 1, self.height - 2)
            self.vy = -self.vy
        if self.vx < 0 and self.x <= 4 and self.player - 0.5 <= self.y <= self.player + 4.5:
            self.x = 4
            self.vx = min(1.35, -self.vx + 0.045)
            self.vy = clamp(self.vy + (self.y - self.player - 2) * 0.12, -0.85, 0.85)
        elif self.vx > 0 and self.x >= self.width - 5 and self.ai - 0.5 <= self.y <= self.ai + 4.5:
            self.x = self.width - 5
            self.vx = max(-1.35, -self.vx - 0.045)
            self.vy = clamp(self.vy + (self.y - self.ai - 2) * 0.12, -0.85, 0.85)
        if self.x < 0 or self.x >= self.width:
            scorer = 1 if self.x < 0 else 0
            self.points[scorer] += 1
            if self.points[scorer] == 7:
                self.winner = scorer
            else:
                self.serve(1 if scorer == 0 else -1)


def play_pong(screen):
    height, width = screen.getmaxyx()
    game = Pong(clamp(width - 4, 42, 90), clamp(height - 7, 14, 26))

    def keys(key):
        if key in (curses.KEY_UP, ord("w"), ord("W")):
            game.move(-2)
        elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
            game.move(2)
        elif key in (ord("r"), ord("R")):
            game.reset()

    def render(screen, color):
        _, screen_width = screen.getmaxyx()
        left = (screen_width - game.width) // 2
        safe_write(screen, 1, left, f"✦ P O N G   YOU {game.points[0]} : {game.points[1]} CPU", color(1))
        for y in range(game.height):
            line = [" "] * game.width
            if y in (0, game.height - 1):
                line = ["─"] * game.width
            else:
                line[game.width // 2] = "┊"
                if int(game.player) <= y < int(game.player) + 5:
                    line[2] = "█"
                if int(game.ai) <= y < int(game.ai) + 5:
                    line[-3] = "█"
                if int(game.y) == y and 0 <= int(game.x) < game.width:
                    line[int(game.x)] = "●"
            safe_write(screen, y + 3, left, "".join(line), color(1))
        safe_write(screen, game.height + 4, left, "↑/↓ or W/S move  ·  First to 7  ·  P pause  ·  R restart  ·  Q quit", color(4))
        if game.winner is not None:
            safe_write(screen, game.height + 5, left, "YOU WIN!" if game.winner == 0 else "CPU WINS  ·  R rematch", color(3))

    frame(screen, 48, 21, render, game.step, keys, 24)


MAZE = (
    "########################",
    "#....E.................#",
    "#..###.....######......#",
    "#....#.................#",
    "#....#...E.......#.....#",
    "#....#...........#.....#",
    "#..............#.......#",
    "####..#####...#........#",
    "#..........#...........#",
    "#..E.......#...........#",
    "#......................#",
    "########################",
)


@dataclass
class Enemy:
    x: float
    y: float
    health: int = 2
    kind: str = "E"
    cooldown: int = 0


@dataclass
class Projectile:
    x: float
    y: float
    dx: float
    dy: float
    damage: int


LEVEL_NAMES = ("THE BREACH", "MIRROR HALL", "UNDERGROUND", "THE CROSSING",
               "KILL ZONE", "THE LAST GATE")
ENEMY_STATS = {"E": (2, 0.034, 8), "F": (1, 0.064, 6),
               "R": (2, 0.023, 5), "B": (8, 0.028, 18)}


def level_layout(index):
    """Six deterministic variants, with connected rooms and increasingly mixed threats."""
    rows = [list(row.replace("E", ".")) for row in MAZE]
    if index in (1, 3, 5):
        rows = [row[::-1] for row in rows]
    if index in (2, 3):
        rows = rows[::-1]
    # Open a different shortcut each time; never close a route or strand a pickup.
    for x, y in (((4, 2),), ((7, 2), (11, 7)), ((5, 7), (17, 4)),
                 ((10, 2), (14, 7)), ((4, 4), (12, 8), (18, 2)),
                 ((5, 2), (10, 7), (17, 4), (12, 8)))[index]:
        rows[y][x] = "."
    # Distinct cover and crossfire lanes in later stages. Keep the outside border sealed.
    barriers = {
        1: ((8, 5, 13, 5), (15, 9, 18, 9)),
        2: ((12, 1, 12, 3), (2, 6, 7, 6)),
        3: ((8, 1, 8, 3), (16, 6, 20, 6), (4, 8, 8, 8)),
        4: ((8, 5, 13, 5), (15, 8, 20, 8), (7, 10, 10, 10)),
        5: ((12, 1, 17, 1), (6, 10, 11, 10), (14, 3, 14, 6)),
    }
    for x1, y1, x2, y2 in barriers.get(index, ()):
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                rows[y][x] = "#"
    return tuple("".join(row) for row in rows)


class Doom:
    """Original raycast maze shooter; no copyrighted assets or game data."""
    def __init__(self, maze=None):
        self.custom_maze = maze is not None
        maze = maze if maze is not None else MAZE
        if not maze or any(len(row) != len(maze[0]) for row in maze):
            raise ValueError("The maze must be rectangular.")
        self.initial_maze = tuple(maze)
        self.level_count = 1 if self.custom_maze else len(LEVEL_NAMES)
        self.reset()

    def reset(self):
        self.health, self.ammo, self.score = 100, 24, 0
        self.level_index = 0
        self.won = False
        self.load_level(0)

    def load_level(self, index):
        self.level_index = index
        self.maze = self.initial_maze if self.custom_maze or index == 0 else level_layout(index)
        self.x = (len(self.maze[0]) - 2.5) if index in (1, 3, 5) else 2.5
        self.y = (len(self.maze) - 2.5) if index in (2, 3) else 1.5
        self.angle = math.pi if index in (1, 3, 5) else 0.0
        if self.custom_maze:
            self.x, self.y, self.angle = 2.5, 1.5, 0.0
        self.health = min(100, self.health + (18 if index else 0))
        self.ammo = min(48, self.ammo + (12 if index else 0))
        self.kills = self.ticks = self.flash = self.fire_cooldown = self.hurt_cooldown = 0
        self.projectiles = []
        self.message = "Eliminate hostiles, then reach the gate."
        self.message_ticks = 85
        self.enemies = [Enemy(x + 0.5, y + 0.5) for y, row in enumerate(self.maze)
                        for x, cell in enumerate(row) if cell == "E"]
        self.pickups = {}
        if self.custom_maze:
            self.exit = None
        else:
            distances = self.distances((int(self.x), int(self.y)))
            cells = [pos for pos, distance in distances.items() if distance >= 5]
            cells.sort(key=lambda pos: (-distances[pos], pos[1], pos[0]))
            self.exit = cells[0]
            if index:
                # Spread enemies around the arena instead of spawning a pack at the gate.
                chosen = []
                kinds = ("E", "F", "R", "E", "F", "R", "E", "B")
                for kind in kinds[:index + 3]:
                    eligible = [pos for pos in cells if pos != self.exit and pos not in chosen]
                    pos = max(eligible, key=lambda tile: (min((abs(tile[0] - x) + abs(tile[1] - y)
                                                              for x, y in chosen), default=distances[tile]),
                                                          distances[tile], -tile[1], -tile[0]))
                    chosen.append(pos)
                    self.enemies.append(Enemy(pos[0] + 0.5, pos[1] + 0.5,
                                              ENEMY_STATS[kind][0], kind))
            occupied = {(int(e.x), int(e.y)) for e in self.enemies}
            free = [pos for pos in cells if pos not in occupied and pos != self.exit]
            for pos, kind in zip((free[len(free) // 3], free[2 * len(free) // 3]), ("A", "H")):
                self.pickups[pos] = kind
        self.total = len(self.enemies)

    def distances(self, start):
        distances = {start: 0}
        pending = deque((start,))
        while pending:
            x, y = pending.popleft()
            for pos in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if pos not in distances and not self.wall(*pos):
                    distances[pos] = distances[(x, y)] + 1
                    pending.append(pos)
        return distances

    def wall(self, x, y):
        ix, iy = int(x), int(y)
        return (ix < 0 or iy < 0 or iy >= len(self.maze) or ix >= len(self.maze[0])
                or self.maze[iy][ix] == "#")

    def move(self, forward, sideways):
        if self.health <= 0 or self.won:
            return
        dx = math.cos(self.angle) * forward - math.sin(self.angle) * sideways
        dy = math.sin(self.angle) * forward + math.cos(self.angle) * sideways
        next_x, next_y = self.x + dx, self.y + dy
        if not self.wall(next_x + math.copysign(0.18, dx or 1), self.y):
            self.x = next_x
        if not self.wall(self.x, next_y + math.copysign(0.18, dy or 1)):
            self.y = next_y
        position = (int(self.x), int(self.y))
        item = self.pickups.pop(position, None)
        if item == "A":
            self.ammo = min(48, self.ammo + 12)
            self.announce("AMMO +12")
        elif item == "H":
            self.health = min(100, self.health + 30)
            self.announce("MEDKIT +30")
        if self.exit == position and self.kills == self.total:
            if self.level_index + 1 == self.level_count:
                self.won = True
                self.announce("YOU SURVIVED THE LAST GATE!")
            else:
                self.load_level(self.level_index + 1)

    def announce(self, message):
        self.message, self.message_ticks = message, 55

    def ray(self, angle, maximum=24):
        """Cast to the nearest wall, returning distance and which axis it hit."""
        direction_x, direction_y = math.cos(angle), math.sin(angle)
        cell_x, cell_y = int(self.x), int(self.y)
        step_x, step_y = (1 if direction_x >= 0 else -1), (1 if direction_y >= 0 else -1)
        delta_x = abs(1 / direction_x) if abs(direction_x) > 1e-9 else float("inf")
        delta_y = abs(1 / direction_y) if abs(direction_y) > 1e-9 else float("inf")
        side_x = ((cell_x + 1 - self.x) if step_x > 0 else (self.x - cell_x)) * delta_x
        side_y = ((cell_y + 1 - self.y) if step_y > 0 else (self.y - cell_y)) * delta_y
        while min(side_x, side_y) <= maximum:
            if side_x < side_y:
                distance, side_x, cell_x, side = side_x, side_x + delta_x, cell_x + step_x, 0
            else:
                distance, side_y, cell_y, side = side_y, side_y + delta_y, cell_y + step_y, 1
            if self.wall(cell_x, cell_y):
                return distance, side
        return maximum, 0

    def visible(self, enemy):
        return self.line_clear(self.x, self.y, enemy.x, enemy.y)

    def line_clear(self, x1, y1, x2, y2):
        distance = math.hypot(x2 - x1, y2 - y1)
        for step in range(1, max(1, int(distance / 0.08))):
            fraction = step * 0.08 / distance
            if self.wall(x1 + (x2 - x1) * fraction, y1 + (y2 - y1) * fraction):
                return False
        return True

    def shoot(self):
        if self.ammo <= 0 or self.health <= 0 or self.won or self.fire_cooldown:
            return False
        self.ammo -= 1
        self.flash, self.fire_cooldown = 3, 3
        candidates = []
        for enemy in self.enemies:
            if enemy.health <= 0:
                continue
            distance = math.hypot(enemy.x - self.x, enemy.y - self.y)
            difference = math.atan2(math.sin(math.atan2(enemy.y - self.y, enemy.x - self.x) - self.angle),
                                    math.cos(math.atan2(enemy.y - self.y, enemy.x - self.x) - self.angle))
            if distance < 12 and abs(difference) < max(0.09, 0.22 / distance) and self.visible(enemy):
                candidates.append((distance, enemy))
        if candidates:
            victim = min(candidates, key=lambda pair: pair[0])[1]
            victim.health -= 1
            if victim.health == 0:
                self.kills += 1
                self.score += {"E": 100, "F": 150, "R": 200, "B": 1000}[victim.kind]
                if self.kills % 3 == 0 and self.kills != self.total:
                    self.pickups[(int(victim.x), int(victim.y))] = "A"
                if self.kills == self.total:
                    if self.exit is None:
                        self.won = True
                        self.announce("ARENA CLEAR!")
                    else:
                        self.announce("AREA CLEAR — REACH THE GATE >")
            return True
        return False

    def step(self):
        if self.health <= 0 or self.won:
            return
        self.ticks += 1
        self.flash = max(0, self.flash - 1)
        self.fire_cooldown = max(0, self.fire_cooldown - 1)
        self.hurt_cooldown = max(0, self.hurt_cooldown - 1)
        self.message_ticks = max(0, self.message_ticks - 1)
        for shot in self.projectiles[:]:
            shot.x += shot.dx
            shot.y += shot.dy
            if self.wall(shot.x, shot.y):
                self.projectiles.remove(shot)
            elif math.hypot(self.x - shot.x, self.y - shot.y) < 0.38:
                self.projectiles.remove(shot)
                self.hurt(shot.damage)
        path = self.distances((int(self.x), int(self.y))) if self.ticks % 5 == 0 else None
        for enemy in self.enemies:
            if enemy.health <= 0:
                continue
            distance = math.hypot(enemy.x - self.x, enemy.y - self.y)
            enemy.cooldown = max(0, enemy.cooldown - 1)
            if distance > 12:
                continue
            if distance < 1.05:
                if not enemy.cooldown:
                    self.hurt(ENEMY_STATS[enemy.kind][2])
                    enemy.cooldown = 17 if enemy.kind == "F" else 22
                continue
            if enemy.kind == "R" and distance < 9 and self.visible(enemy) and not enemy.cooldown:
                self.projectiles.append(Projectile(enemy.x, enemy.y,
                                                   (self.x - enemy.x) / distance * 0.24,
                                                   (self.y - enemy.y) / distance * 0.24, 9))
                enemy.cooldown = 32
            if enemy.kind == "R" and distance < 3:
                continue
            speed = ENEMY_STATS[enemy.kind][1]
            if self.visible(enemy):
                dx, dy = (self.x - enemy.x) / distance, (self.y - enemy.y) / distance
            else:
                if path is None:
                    continue
                tile = (int(enemy.x), int(enemy.y))
                neighbors = ((tile[0] + 1, tile[1]), (tile[0] - 1, tile[1]),
                             (tile[0], tile[1] + 1), (tile[0], tile[1] - 1))
                options = [pos for pos in neighbors if path.get(pos, float("inf")) < path.get(tile, float("inf"))]
                if not options:
                    continue
                target = min(options, key=path.__getitem__)
                dx, dy = target[0] + 0.5 - enemy.x, target[1] + 0.5 - enemy.y
                length = math.hypot(dx, dy)
                dx, dy = dx / length, dy / length
            if not self.wall(enemy.x + dx * speed + math.copysign(0.18, dx), enemy.y):
                enemy.x += dx * speed
            if not self.wall(enemy.x, enemy.y + dy * speed + math.copysign(0.18, dy)):
                enemy.y += dy * speed
        if self.ammo == 0 and not any(kind == "A" for kind in self.pickups.values()) and self.ticks % 100 == 0:
            self.ammo = 6
            self.announce("EMERGENCY AMMO +6")

    def hurt(self, damage):
        if self.hurt_cooldown or self.health <= 0:
            return
        self.health = max(0, self.health - damage)
        self.hurt_cooldown = 8
        if not self.health:
            self.announce("YOU DIED — R TO RESTART")


def play_doom(screen):
    game = Doom()
    show_map = False

    def keys(key):
        nonlocal show_map
        if game.health <= 0 or game.won:
            if key in (ord("r"), ord("R")):
                game.reset()
            return
        if key in (ord("w"), ord("W"), curses.KEY_UP):
            game.move(0.28, 0)
        elif key in (ord("s"), ord("S"), curses.KEY_DOWN):
            game.move(-0.28, 0)
        elif key in (ord("a"), ord("A")):
            game.move(0, -0.28)
        elif key in (ord("d"), ord("D")):
            game.move(0, 0.28)
        elif key == curses.KEY_LEFT:
            game.angle = (game.angle - 0.17) % (2 * math.pi)
        elif key == curses.KEY_RIGHT:
            game.angle = (game.angle + 0.17) % (2 * math.pi)
        elif key == ord(" "):
            game.shoot()
        elif key in (ord("m"), ord("M")):
            show_map = not show_map
        elif key in (ord("r"), ord("R")):
            game.reset()

    def render(screen, color):
        rows, columns = screen.getmaxyx()
        width, height = min(columns - 4, 110), min(rows - 8, 30)
        left = (columns - width) // 2
        safe_write(screen, 1, left, "✦ B C U  /  D O O M     ORIGINAL TERMINAL MAZE SHOOTER", color(5))
        sky = height // 2
        image = [[" " if row < sky else "." for _ in range(width)] for row in range(height)]
        depths = []
        for column in range(width):
            offset = math.atan((2 * column / width - 1) * 0.66)
            raw_distance, side = game.ray(game.angle + offset)
            distance = max(0.12, raw_distance * math.cos(offset))
            depths.append(distance)
            size = min(height, int(height / distance))
            top = max(0, (height - size) // 2)
            shade = "█" if distance < 3 else "▓" if distance < 6 else "▒" if distance < 11 else "░"
            if side:
                shade = "▓" if shade == "█" else "▒" if shade == "▓" else shade
            for row in range(top, min(height, top + size)):
                image[row][column] = shade
        sprites = [(e.x, e.y, "W" if e.kind == "B" else e.kind) for e in game.enemies if e.health > 0]
        sprites.extend((x + 0.5, y + 0.5, "+" if kind == "H" else "=")
                       for (x, y), kind in game.pickups.items())
        sprites.extend((shot.x, shot.y, "*") for shot in game.projectiles)
        if game.exit and game.kills == game.total:
            sprites.append((game.exit[0] + 0.5, game.exit[1] + 0.5, ">"))
        for sprite_x, sprite_y, glyph in sorted(sprites,
                                                key=lambda item: math.hypot(item[0] - game.x, item[1] - game.y),
                                                reverse=True):
            distance = math.hypot(sprite_x - game.x, sprite_y - game.y)
            bearing = math.atan2(sprite_y - game.y, sprite_x - game.x) - game.angle
            bearing = math.atan2(math.sin(bearing), math.cos(bearing))
            if distance < 0.3 or abs(bearing) > 0.67 or not game.line_clear(game.x, game.y, sprite_x, sprite_y):
                continue
            center = int((math.tan(bearing) / 0.66 + 1) * width / 2)
            size = min(height, max(1, int(height / distance * (0.8 if glyph in "EFRW" else 0.35))))
            for column in range(max(0, center - max(1, size // 5)), min(width, center + max(1, size // 5) + 1)):
                if distance >= depths[column] + 0.1:
                    continue
                for row in range(max(0, sky - size // 2), min(height, sky + size // 2 + 1)):
                    image[row][column] = glyph
        image[sky][width // 2] = "✛" if game.flash == 0 else "✦"
        for row in range(height):
            safe_write(screen, row + 3, left, "".join(image[row]), color(5) if game.hurt_cooldown or (game.flash and row == sky) else color(1))
        stage = f"{game.level_index + 1}/{game.level_count} {LEVEL_NAMES[game.level_index]}" if not game.custom_maze else "CUSTOM ARENA"
        safe_write(screen, 2, left, f"STAGE {stage}  ·  SCORE {game.score}", color(4))
        safe_write(screen, height + 4, left,
                   f"HP {game.health:3} [{'█' * (game.health // 10):10}]  AMMO {game.ammo:2}  FOES {game.total - game.kills:2}"
                   + ("  VICTORY · R restart" if game.won else "  GAME OVER · R restart" if game.health <= 0
                      else "  FIND GATE >" if game.kills == game.total else ""),
                   color(3) if game.health > 30 else color(5))
        safe_write(screen, height + 5, left, game.message if game.message_ticks or game.won else
                   "W/S move · A/D strafe · ←/→ turn · SPACE fire · M map · P pause · R restart · Q quit", color(4))
        if show_map and columns >= 72 and rows >= 25:
            for y, line in enumerate(game.maze):
                if y + 3 >= rows - 1:
                    break
                cells = list(line.replace("E", "."))
                for enemy in game.enemies:
                    if enemy.health > 0 and int(enemy.y) == y:
                        cells[int(enemy.x)] = enemy.kind
                for (x, py), kind in game.pickups.items():
                    if py == y:
                        cells[x] = "+" if kind == "H" else "="
                if game.exit and game.exit[1] == y:
                    cells[game.exit[0]] = ">"
                if int(game.y) == y:
                    cells[int(game.x)] = "@"
                safe_write(screen, y + 3, left + 2, "".join(cells), color(2))

    frame(screen, 70, 22, render, game.step, keys, 20)


def run(name):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise GameError("Games need an interactive terminal. Open Terminal and run bobocodexultra " + name + ".")
    if name not in {"snake", "pong", "doom"}:
        raise GameError("Unknown game.")
    if not sys.stdout.encoding or "UTF" not in sys.stdout.encoding.upper():
        raise GameError("Games need a UTF-8 terminal.")
    try:
        curses.wrapper({"snake": play_snake, "pong": play_pong, "doom": play_doom}[name])
    except curses.error as exc:
        raise GameError("Terminal graphics are unavailable; use a standard interactive Terminal window.") from exc
