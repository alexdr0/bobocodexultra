"""Procedural, asset-free half-block graphics for BCU's terminal raycaster.

Each terminal character contains two independently colored vertical pixels. The
renderer uses a fixed 15-color palette so color-pair allocation stays bounded,
and falls back to monochrome shading on terminals without usable color support.
"""

from __future__ import annotations

import curses
import math


BLACK, NIGHT, TEAL, SLATE, STEEL, IRON, BRONZE, SAND, RUST, AMBER, RED, GREEN, CYAN, WHITE, VIOLET = range(15)
XTERM_COLORS = (0, 17, 24, 59, 60, 52, 94, 180, 130, 202, 196, 34, 45, 231, 129)
BASIC_COLORS = (0, 4, 6, 4, 7, 0, 3, 7, 3, 3, 1, 2, 6, 7, 5)
INK = {"d": IRON, "m": STEEL, "l": WHITE, "r": RED, "o": AMBER,
       "g": GREEN, "c": CYAN, "v": VIOLET, "w": SAND, "k": BLACK}
WALL_THEMES = ((IRON, BRONZE, SAND), (NIGHT, TEAL, CYAN),
               (IRON, RUST, AMBER), (SLATE, STEEL, WHITE),
               (IRON, RED, AMBER), (SLATE, VIOLET, WHITE))


def sprite(rows):
    lines = rows.strip("\n").splitlines()
    width = max(map(len, lines))
    return tuple(line.ljust(width) for line in lines)


# Hand-drawn silhouettes. Spaces are transparent; letters map to palette colors.
SPRITES = {
    "E": sprite("""
     dd     
    drrd    
   drllrd   
   drrrrd   
  ddmrrmdd  
  dmmddmmd  
 dddmmmmddd 
 dmmrmmrmmd 
 dmmmmmmmmd 
 ddmmmmmmdd 
  dmddddmd  
  dd    dd  
 dmm    mmd 
 ddd    ddd 
"""),
    "F": sprite("""
    dd dd    
   dddddd   
   dgllgd   
   dggggd   
  ddggggdd  
 dggddddggd 
 dgdggggdgd 
  dggggggd  
  ddggggdd  
   dggggd   
  dgddddgd  
  dd    dd  
 dg      gd 
 dd      dd 
"""),
    "R": sprite("""
   dddddd   
  dmmmmmm d 
  dmccccmd  
  dmmmmmm d 
  ddmddmdd  
  dmmmmmm d 
 ddmmmmmmdd 
 dmmdmm dmmd
 dmmdmm dmmd
 ddmmmmmmdd 
  dmddddmd  
  dd    dd  
 dmm    mmd 
 ddd    ddd 
"""),
    "B": sprite("""
    dddddddd    
  dddvvvvdddd  
  dvvllllvv d  
  dvvrrrrvv d  
 dddvvvvvvddd  
 dmmmddddmmmd  
 ddmmvvvvmmdd  
 dmmmvvvvmmmd  
 dmmmvvvvmmmd  
 ddddmmmmdddd  
  dddmmmmddd   
  ddmddddmdd   
 dmmm    mmmd  
 dddd    dddd  
"""),
    "H": sprite("""
  ddddddd  
  dllllld  
  dllrll d 
  dlrrrld  
  dllrll d 
  dllllld  
  ddddddd  
"""),
    "A": sprite("""
  ddddddd  
  doooood  
  doddood  
  doooood  
  doddood  
  doooood  
  ddddddd  
"""),
    "X": sprite("""
 dcccccccd 
 dcdddd d c
 dcllllllcd
 dcld  dlcd
 dcld  dlcd
 dcllllllcd
 dcddddddcd
 dcccccccd 
"""),
    "P": sprite("""
  rrr  
 rlllr 
 rllllr
  rrr  
"""),
}

WEAPON = sprite("""
          lll          
         ldddl         
        lmmmmm l       
        dmmmmm d       
       ddmmmm mdd      
      dddmmmmmmddd     
     dmmdmmmmmmdmmd    
    dmmmdmmmmmdmmmd   
   dmmmmddmmddmmmmd   
  ddmmmmmmmmmmmmmmdd  
""")


def wall_pixel(u, v, distance, side, level):
    """Procedural riveted plating; side and distance change the light level."""
    dark, middle, bright = WALL_THEMES[level % len(WALL_THEMES)]
    brick_row = int(v * 9)
    seam_x = ((u * 6 + (brick_row % 2) * 0.5) % 1) < 0.09
    seam_y = (v * 9 % 1) < 0.11
    rivet = (u * 6 % 1 < 0.12) and (v * 9 % 1 < 0.22)
    if seam_x or seam_y:
        return dark
    if rivet and distance < 7:
        return bright
    if side or distance > 9:
        return dark if distance > 14 or (int(u * 24) + brick_row) % 3 == 0 else middle
    if distance < 4 and (int(u * 12) + brick_row) % 5 == 0:
        return bright
    return middle


def floor_pixel(x, y, distance, level):
    """Perspective floor grid with stage-colored hazard inlays."""
    fraction_x, fraction_y = x % 1, y % 1
    if distance > 14:
        return NIGHT
    edge = min(fraction_x, fraction_y, 1 - fraction_x, 1 - fraction_y)
    if edge < 0.045:
        return IRON
    if (int(x) + int(y) + level) % 7 == 0 and abs(fraction_x - fraction_y) < 0.065:
        return WALL_THEMES[level % 6][2] if distance < 5 else WALL_THEMES[level % 6][1]
    if distance > 7:
        return SLATE
    return STEEL if (int(x) + int(y)) % 2 == 0 else SLATE


class TerminalPixels:
    """Bounded color-pair cache; monochrome still works without curses colors."""

    def __init__(self):
        self.pairs = {}
        self.next_pair = 7  # pairs 1-6 belong to the other arcade games
        self.has_color = bool(curses.has_colors())
        self.colors = XTERM_COLORS if self.has_color and curses.COLORS >= 256 else BASIC_COLORS
        self.limit = min(getattr(curses, "COLOR_PAIRS", 0), 256)

    def cell(self, upper, lower):
        if not self.has_color:
            brightness = (upper not in (BLACK, NIGHT, IRON)) + (lower not in (BLACK, NIGHT, IRON))
            return ("█" if brightness == 2 else "▓" if brightness else "░"), 0
        key = (self.colors[upper], self.colors[lower])
        if key not in self.pairs:
            if self.next_pair >= self.limit:
                foreground = next((style for (front, _), style in self.pairs.items()
                                   if front == key[0]), curses.color_pair(1))
                return "█", foreground
            try:
                curses.init_pair(self.next_pair, *key)
            except curses.error:
                foreground = next((style for (front, _), style in self.pairs.items()
                                   if front == key[0]), curses.color_pair(1))
                return "█", foreground
            self.pairs[key] = curses.color_pair(self.next_pair)
            self.next_pair += 1
        return "▀", self.pairs[key]

    def draw(self, screen, pixels, left, top):
        """Batch adjacent cells with the same pair to reduce terminal writes."""
        for row in range(len(pixels) // 2):
            run, style, start = "", None, 0
            for col, (upper, lower) in enumerate(zip(pixels[row * 2], pixels[row * 2 + 1])):
                char, attribute = self.cell(upper, lower)
                if style is not None and style != attribute:
                    try:
                        screen.addstr(top + row, left + start, run, style)
                    except curses.error:
                        pass
                    run, start = "", col
                run += char
                style = attribute
            if run:
                try:
                    screen.addstr(top + row, left + start, run, style)
                except curses.error:
                    pass


class DoomRenderer:
    """Raycast walls, textured floor, depth-sorted sprites, and a first-person gun."""

    def __init__(self):
        self.terminal = None

    @staticmethod
    def overlay(pixels, art, center_x, top, width, height, depths=None, distance=0):
        rows, columns = len(pixels), len(pixels[0])
        start_x = center_x - width // 2
        for y in range(max(0, top), min(rows, top + height)):
            source_y = min(len(art) - 1, (y - top) * len(art) // height)
            for x in range(max(0, start_x), min(columns, start_x + width)):
                if depths is not None and distance >= depths[x] + 0.08:
                    continue
                source_x = min(len(art[0]) - 1, (x - start_x) * len(art[0]) // width)
                ink = art[source_y][source_x]
                if ink != " ":
                    pixels[y][x] = INK[ink]

    def pixels(self, game, width, height):
        if width < 1 or height < 1:
            raise ValueError("Doom viewport must have positive dimensions")
        pixel_height = height * 2
        horizon = pixel_height // 2
        canvas = [[NIGHT] * width for _ in range(pixel_height)]
        depths = [24.0] * width
        for column in range(width):
            offset = math.atan((2 * (column + 0.5) / width - 1) * 0.66)
            angle = game.angle + offset
            raw_distance, side, u = game.ray_detail(angle)
            distance = max(0.12, raw_distance * math.cos(offset))
            depths[column] = distance
            wall_height = min(pixel_height * 3, max(1, int(pixel_height / distance)))
            wall_top = horizon - wall_height // 2
            ray_x, ray_y = math.cos(angle), math.sin(angle)
            for row in range(pixel_height):
                if wall_top <= row < wall_top + wall_height:
                    canvas[row][column] = wall_pixel(u, (row - wall_top) / wall_height,
                                                     distance, side, game.level_index)
                elif row < horizon:
                    canvas[row][column] = NIGHT if row < horizon // 2 else TEAL if row > horizon - 3 else SLATE
                    if (column * 67 + row * 41 + game.level_index * 17) % 313 == 0:
                        canvas[row][column] = CYAN
                else:
                    floor_distance = pixel_height / max(1, 2 * row - pixel_height + 1)
                    world_x = game.x + ray_x * floor_distance
                    world_y = game.y + ray_y * floor_distance
                    canvas[row][column] = floor_pixel(world_x, world_y, floor_distance, game.level_index)

        sprites = [(enemy.x, enemy.y, enemy.kind, 1.0 if enemy.kind != "B" else 1.35)
                   for enemy in game.enemies if enemy.health > 0]
        sprites.extend((x + 0.5, y + 0.5, kind, 0.5) for (x, y), kind in game.pickups.items())
        sprites.extend((shot.x, shot.y, "P", 0.3) for shot in game.projectiles)
        if game.exit is not None and game.kills == game.total:
            sprites.append((game.exit[0] + 0.5, game.exit[1] + 0.5, "X", 1.0))
        for x, y, kind, scale in sorted(sprites,
                                        key=lambda item: math.hypot(item[0] - game.x, item[1] - game.y),
                                        reverse=True):
            distance = math.hypot(x - game.x, y - game.y)
            bearing = math.atan2(math.sin(math.atan2(y - game.y, x - game.x) - game.angle),
                                 math.cos(math.atan2(y - game.y, x - game.x) - game.angle))
            if distance < 0.28 or abs(bearing) >= 0.68 or not game.line_clear(game.x, game.y, x, y):
                continue
            projected = max(0.12, distance * math.cos(bearing))
            sprite_height = min(pixel_height * 3, max(2, int(pixel_height * scale / projected)))
            art = SPRITES[kind]
            sprite_width = max(1, int(sprite_height * len(art[0]) / len(art) * 0.8))
            center = int((math.tan(bearing) / 0.66 + 1) * width / 2)
            top = horizon - sprite_height // 2
            self.overlay(canvas, art, center, top, sprite_width, sprite_height, depths, projected)

        # Reticle and weapon remain screen-space overlays, not world sprites.
        center = width // 2
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            x, y = center + dx, horizon + dy
            if 0 <= x < width and 0 <= y < pixel_height:
                canvas[y][x] = RED if game.hurt_cooldown else WHITE
        canvas[horizon][center] = AMBER if game.flash else RED
        weapon_height = min(10, pixel_height // 3)
        if weapon_height > 1:
            weapon_width = min(width // 2, max(5, int(weapon_height * len(WEAPON[0]) / len(WEAPON))))
            self.overlay(canvas, WEAPON, center, pixel_height - weapon_height,
                         weapon_width, weapon_height)
        if game.flash:
            for y in range(max(0, pixel_height - weapon_height - 3), pixel_height - weapon_height):
                for x in range(max(0, center - 2), min(width, center + 3)):
                    if abs(x - center) + abs(y - (pixel_height - weapon_height - 2)) <= 3:
                        canvas[y][x] = WHITE if game.flash > 1 else AMBER
        return canvas

    def draw(self, screen, game, left, top, width, height):
        if self.terminal is None:
            self.terminal = TerminalPixels()
        pixels = self.pixels(game, width, height)
        self.terminal.draw(screen, pixels, left, top)
