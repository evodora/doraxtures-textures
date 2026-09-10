#!/usr/bin/env python3
"""Gallery scenes for the doraxtures.site pack pages.

Ten locations (village, desert, beach, snow, volcano, graveyard, space, jungle,
arena, catacombs), each composed the way the game draws its world: sky panel,
parallax skyline strips, 64-px ground tiles and props standing on the ground
line.  Every sprite is resolved through the pack's own redirect rules — the
pack's file when the pack replaces that sprite, the game's default sprite
otherwise — and drawn at the DEFAULT sprite's footprint, exactly as the game
stretches whatever image a rule points at into the object's world size.

Inputs (kept outside this public repo):
  ~/Desktop/Tools/evoworld-vanilla/sprites/<path>   default sprites (game CDN)
  ~/Desktop/Tools/evoworld-vanilla/sizes.json       default sprite sizes
  ~/Desktop/Tools/evoworld-vanilla/pack_rules.json  pack id -> folder + rules
Output: site/gallery/<pack folder>/<scene>.webp (1280x800, the pack page's 16:10 cells)

    python3 tools/gallery_art.py                 # every pack
    python3 tools/gallery_art.py --pack magma-world --scene village
    python3 tools/gallery_art.py --sheet         # also /tmp/gallery_<folder>.jpg contact sheets
"""
import argparse
import json
import os
import random
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACKS_DIR = os.path.join(ROOT, 'packs')
OUT_DIR = os.path.join(ROOT, 'site', 'gallery')
TOOLS = os.path.expanduser('~/Desktop/Tools/evoworld-vanilla')
VANILLA = os.path.join(TOOLS, 'sprites')
SIZES = json.load(open(os.path.join(TOOLS, 'sizes.json')))
PACK_RULES = json.load(open(os.path.join(TOOLS, 'pack_rules.json')))

W, H = 1280, 800
TILE = 64

BG = 'background/'
TL = 'tiles/'
DIRT = [f'{TL}dirt{i}.png' for i in range(1, 10)]
DIRT_GRASS = [f'{TL}dirt_grass{i}.png' for i in (1, 2, 3)]
DIRT_TOP = [f'{TL}dirt_top{i}.png' for i in (1, 2, 3, 4)]
DIRT_SNOW = [f'{TL}dirt_snow{i}.png' for i in (1, 2)]
GY_TOP = [f'{TL}dirt_graveyard_{i}.png' for i in (1, 2, 3, 4)]
GY_BARE = [f'{TL}dirt_top_graveyard_{i}.png' for i in (1, 2, 3, 4)]
GY_FILL = [f'{TL}dirt_fill_graveyard_{i}.png' for i in range(1, 10)]
HOUSES = [f'houses/house_{i}.png' for i in range(1, 14)]
TREES = [f'{BG}tree_1_bright_green.png', f'{BG}tree_2_bright_green.png', f'{BG}tree_3_bright_green.png']
DEAD_TREES = [f'{BG}tree_1__no_vegetation_base.png', f'{BG}tree_3_no_vegetation_base.png']
FLOWERS = [f'{TL}flowers/flower_{c}.png' for c in ('pink', 'purple', 'red', 'white', 'yellow')]
CLOUDS = [f'clouds/cloud{i}.png' for i in (1, 2, 3, 4)]


def paste(canvas, img, x, y):
    """alpha-composite img with its top-left at (x, y), clipped to the canvas."""
    x, y = int(round(x)), int(round(y))
    sx = max(0, -x)
    sy = max(0, -y)
    ex = min(img.width, W - x)
    ey = min(img.height, H - y)
    if ex <= sx or ey <= sy:
        return
    part = img if (sx, sy, ex, ey) == (0, 0, img.width, img.height) else img.crop((sx, sy, ex, ey))
    canvas.alpha_composite(part, (x + sx, y + sy))


class Scene:
    def __init__(self, pack, seed, s=0.55):
        self.pack = pack
        self.rng = random.Random(seed)
        self.s = s
        self.canvas = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        self.cache = {}
        self.gy = H - 3 * int(TILE * s)      # ground line (top of the ground tiles)

    # ------------------------------------------------------------ sprites
    def _open(self, vpath):
        if vpath in self.cache:
            return self.cache[vpath]
        rules = self.pack['rules']
        img = None
        if vpath in rules:
            f = os.path.join(PACKS_DIR, self.pack['folder'], rules[vpath])
            if os.path.exists(f):
                img = Image.open(f).convert('RGBA')
                if img.getchannel('A').getbbox() is None:      # blanked on purpose
                    img = False
        if img is None:
            f = os.path.join(VANILLA, vpath)
            img = Image.open(f).convert('RGBA') if os.path.exists(f) else False
        self.cache[vpath] = img
        return img

    def size(self, vpath, scale=None):
        vw, vh = SIZES[vpath]
        k = self.s if scale is None else scale
        return max(1, int(round(vw * k))), max(1, int(round(vh * k)))

    def sprite(self, vpath, scale=None, w=None, h=None, flip=False):
        img = self._open(vpath)
        if img is False:
            return None
        if w is None or h is None:
            w, h = self.size(vpath, scale)
        out = img.resize((w, h), Image.LANCZOS)
        if flip:
            out = out.transpose(Image.FLIP_LEFT_RIGHT)
        return out

    def blit(self, vpath, x, y, scale=None, anchor='bl', flip=False, w=None, h=None):
        """Draw vpath at its game footprint. anchor: bl / bc / br / tl / c."""
        im = self.sprite(vpath, scale, w, h, flip)
        if im is None:
            return None
        if anchor == 'bl':
            px, py = x, y - im.height
        elif anchor == 'bc':
            px, py = x - im.width // 2, y - im.height
        elif anchor == 'br':
            px, py = x - im.width, y - im.height
        elif anchor == 'c':
            px, py = x - im.width // 2, y - im.height // 2
        else:
            px, py = x, y
        paste(self.canvas, im, px, py)
        return (px, py, px + im.width, py + im.height)

    # ------------------------------------------------------------ layers
    def sky(self, vpath, y_bottom=None):
        img = self._open(vpath)
        if img is False:
            return
        y_bottom = self.gy + 40 if y_bottom is None else y_bottom
        sc = W / img.width
        im = img.resize((W, int(img.height * sc)), Image.LANCZOS)
        paste(self.canvas, im, 0, y_bottom - im.height)
        if y_bottom - im.height > 0:                       # extend the top colour upward
            top = im.crop((0, 0, W, 1)).resize((W, y_bottom - im.height))
            paste(self.canvas, top, 0, 0)

    def panel_wall(self, vpaths, scale=None, y_bottom=None, x_shift=0, rows=None):
        """Tile tall 640x1024 panels (graveyard / jungle / space) over the canvas."""
        y_bottom = H if y_bottom is None else y_bottom
        pw, ph = self.size(vpaths[0], scale)
        rows = rows or (y_bottom // ph + 1)
        for r in range(rows):
            y = y_bottom - (r + 1) * ph
            x = -((x_shift + r * pw // 3) % pw)
            i = 0
            while x < W:
                self.blit(vpaths[(i + r) % len(vpaths)], x, y, anchor='tl', w=pw, h=ph)
                x += pw
                i += 1

    def strips(self, biome, layers=((3, 1.32, -260, 16), (2, 1.12, -560, 8), (1, 1.0, -40, 0))):
        """Parallax skyline: (variant, canvas scale, x offset, y sink) back to front.
        Copies alternate mirrored so every seam is continuous whatever the strip's edges."""
        vp = f'{BG}background_{biome}_%d.png'
        bottom = f'{BG}background_{biome}_bottom.png'
        if self._open(bottom):
            bt = self.sprite(bottom, w=128, h=128)
            for x in range(0, W, 128):
                paste(self.canvas, bt, x, self.gy - 6)
        for variant, k, xo, sink in layers:
            path = vp % variant
            img = self._open(path)
            if img is False:
                continue
            vw, vh = SIZES[path]
            w, h = int(vw * k), int(vh * k)
            im = img.resize((w, h), Image.LANCZOS)
            imf = im.transpose(Image.FLIP_LEFT_RIGHT)
            x = xo % w - w
            i = 0
            while x < W:
                paste(self.canvas, im if i % 2 == 0 else imf, x, self.gy + sink - h)
                x += w
                i += 1

    def ground(self, top, fill, rows=3, x0=0, x1=W, y=None, scale=None):
        y = self.gy if y is None else y
        t = int(TILE * (self.s if scale is None else scale))
        x = x0
        while x < x1:
            for r in range(rows):
                path = self.rng.choice(top if r == 0 else fill)
                self.blit(path, x, y + r * t, anchor='tl', w=t, h=t)
            x += t

    def platform(self, top, fill, x, y, tiles, rows=2, scale=None):
        t = int(TILE * (self.s if scale is None else scale))
        for i in range(tiles):
            for r in range(rows):
                self.blit(self.rng.choice(top if r == 0 else fill), x + i * t, y + r * t, anchor='tl', w=t, h=t)
        return x, y, x + tiles * t, y + rows * t

    def clouds(self, n, y_range=(40, 260), k=0.72):
        xs = sorted(self.rng.sample(range(-60, W - 120, 40), n))
        for x in xs:
            self.blit(self.rng.choice(CLOUDS), x, self.rng.randint(*y_range), scale=self.s * k, anchor='tl')

    def moon(self, vpath, x, y, px=170):
        self.blit(vpath, x, y, anchor='c', w=px, h=px)

    def taxi(self, x, y, k=0.62):
        self.blit('teleports/taxi.png', x, y, scale=self.s * k, anchor='tl')

    def ground_row(self, items, xs, y=None, sink=6):
        """Props standing on the ground: items = (vpath, scale multiplier or None)."""
        y = (self.gy if y is None else y) + sink
        for (vpath, k), x in zip(items, xs):
            self.blit(vpath, x, y, scale=None if k is None else self.s * k, anchor='bc')

    def spread(self, n, x0=60, x1=W - 60, jitter=40):
        step = (x1 - x0) / max(1, n - 1) if n > 1 else 0
        return [int(x0 + i * step + self.rng.randint(-jitter, jitter)) for i in range(n)]

    def rgb(self):
        return self.canvas.convert('RGB')


# ---------------------------------------------------------------- scenes
def village(c):
    c.sky(f'{BG}background_lightblue.png')
    c.strips('normal')
    c.clouds(3)
    c.taxi(W - 330, 30)
    c.ground(DIRT_GRASS, DIRT)
    trees = c.rng.sample(TREES, 2)
    c.ground_row([(trees[0], 1.0), (trees[1], 0.9)], [int(W * 0.30), int(W * 0.68)], sink=4)
    houses = c.rng.sample(HOUSES, 3)
    c.ground_row([(h, 1.0) for h in houses], [int(W * 0.14), int(W * 0.50), int(W * 0.86)])
    c.ground_row([('bushes/bush_1_bright_green.png', 1.0), ('bushes/strawberry_bush.png', 1.0),
                  ('food/pumpkin.png', 1.0), ('food/pig/1.png', 1.0)],
                 [int(W * 0.32), int(W * 0.60), int(W * 0.70), int(W * 0.40)], sink=4)
    for x in c.spread(6, 40, W - 40, 30):
        c.blit(c.rng.choice(FLOWERS), x, c.gy + 4, anchor='bc')
    c.blit('teleports/wooden_doors.png', int(W * 0.975), c.gy + 6, anchor='br')


def desert(c):
    c.sky(f'{BG}background_lightblue.png')
    c.strips('desert', layers=((3, 0.82, -300, 16), (2, 0.72, -620, 10), (1, 0.66, -80, 2)))
    c.clouds(3, (30, 170))
    c.taxi(W - 300, 40, k=0.5)
    c.ground([f'{TL}sand.png'], [f'{TL}sand.png', f'{TL}greystone_sand.png', f'{TL}sand.png'])
    c.ground_row([(f'{BG}rock_1_blue.png', 0.9)], [int(W * 0.78)], sink=4)
    c.ground_row([(f'{BG}dino_bones.png', 0.85)], [int(W * 0.36)], sink=2)
    h = c.rng.sample(HOUSES, 2)
    c.ground_row([(h[0], 1.0), (h[1], 1.0)], [int(W * 0.12), int(W * 0.58)])
    # a ruined colonnade: two stacked pillars and a brick post
    for x in (int(W * 0.88), int(W * 0.96)):
        y = c.gy + 6
        c.blit(f'{BG}pillar_bottom.png', x, y, anchor='bc')
        pb = c.size(f'{BG}pillar_bottom.png')[1]
        pc = c.size(f'{BG}pillar_center.png')[1]
        c.blit(f'{BG}pillar_center.png', x, y - pb, anchor='bc')
        c.blit(f'{BG}pillar_top.png', x, y - pb - pc, anchor='bc')
    c.ground_row([(f'{BG}brick_post_1.png', 1.0), (f'{BG}standing_stone.png', 0.9),
                  ('food/starFruit.png', 1.0), ('food/seed.png', 1.0), ('food/stone.png', 1.0)],
                 [int(W * 0.30), int(W * 0.70), int(W * 0.45), int(W * 0.50), int(W * 0.24)], sink=4)
    c.blit('teleports/wooden_doors_desert.png', int(W * 0.02), c.gy + 6, anchor='bl')


def beach(c):
    c.sky(f'{BG}background_lightblue.png')
    c.strips('sea', layers=((3, 1.2, -200, 12), (2, 1.05, -540, 6), (1, 1.0, -60, 0)))
    c.clouds(3, (30, 200))
    c.taxi(40, 20)
    c.ground([f'{TL}sand.png'], [f'{TL}sand.png'])
    c.ground_row([(f'{BG}jungleTree1.png', 0.9), (f'{BG}jungleTree1.png', 0.7)],
                 [int(W * 0.10), int(W * 0.90)], sink=4)
    c.blit(f'{BG}jungleTree1.png', int(W * 0.10), c.gy + 4, scale=c.s * 0.9, anchor='bc', flip=True)
    h = c.rng.sample(HOUSES, 2)
    c.ground_row([(h[0], 1.0), (h[1], 1.0)], [int(W * 0.36), int(W * 0.70)])
    c.ground_row([(f'{BG}rock_3_grey.png', 0.75), ('food/deadFish.png', 1.0), ('food/starFruit.png', 1.0),
                  ('bushes/bush_1_bright_green.png', 1.0), ('food/egg.png', 1.2)],
                 [int(W * 0.55), int(W * 0.24), int(W * 0.84), int(W * 0.50), int(W * 0.62)], sink=4)
    for x in c.spread(4, 80, W - 80, 30):
        c.blit(c.rng.choice(FLOWERS), x, c.gy + 4, anchor='bc')
    c.blit('teleports/wooden_doors.png', int(W * 0.99), c.gy + 6, anchor='br')


def snow(c):
    c.sky(f'{BG}background_lightblue.png')
    c.strips('snow')
    c.clouds(4, (30, 220), k=0.8)
    c.taxi(60, 30, k=0.5)
    c.ground(DIRT_SNOW, DIRT)
    c.ground_row([(f'{BG}tree_3_no_vegetation_base.png', 0.8), (f'{BG}tree_1__no_vegetation_base.png', 0.7)],
                 [int(W * 0.08), int(W * 0.60)], sink=4)
    h = c.rng.sample(HOUSES, 2)
    c.ground_row([(h[0], 1.0), (h[1], 1.0)], [int(W * 0.30), int(W * 0.82)])
    # stacked ice blocks
    t = int(TILE * c.s)
    x0 = int(W * 0.50)
    for (col, rows) in ((0, 2), (1, 3), (2, 1)):
        for r in range(rows):
            c.blit(f'{TL}iceBlock.png', x0 + col * t, c.gy - (r + 1) * t, anchor='tl', w=t, h=t)
    c.ground_row([(f'{BG}rock_3_grey.png', 0.7), ('food/meat.png', 1.0), ('food/bread.png', 1.0),
                  ('bushes/strawberry_bush.png', 1.0)],
                 [int(W * 0.68), int(W * 0.42), int(W * 0.20), int(W * 0.94)], sink=4)
    c.blit('teleports/wooden_doors_ice.png', int(W * 0.01), c.gy + 6, anchor='bl')


def volcano(c):
    c.sky(f'{BG}background_lightblue.png')
    c.strips('volcano', layers=((3, 1.05, -240, 14), (2, 0.92, -600, 8), (1, 0.85, -60, 2)))
    c.clouds(3, (20, 160), k=0.6)
    c.ground([f'{TL}greystone.png'], [f'{TL}greystone.png'])
    t = int(TILE * c.s)
    for x in range(int(W * 0.40), int(W * 0.40) + 5 * t, t):   # a lava pool sunk into the ground
        for r in (0, 1):
            c.blit(f'{TL}lava.png', x, c.gy + r * t, anchor='tl', w=t, h=t)
    c.ground_row([(f'{BG}volcano_1.png', 0.85), (f'{BG}volcano_2.png', 0.9)],
                 [int(W * 0.24), int(W * 0.84)], sink=4)
    c.ground_row([(f'{BG}tree_3_no_vegetation_base.png', 0.7), (f'{BG}rock_1_blue.png', 0.7),
                  (f'{BG}standing_stone.png', 0.9), ('food/stone.png', 1.0), ('food/meat.png', 1.0)],
                 [int(W * 0.62), int(W * 0.08), int(W * 0.72), int(W * 0.30), int(W * 0.95)], sink=4)
    c.blit('teleports/wooden_doors_lava.png', int(W * 0.52), c.gy + 6, anchor='bl')


def graveyard(c):
    c.sky(f'{BG}background_lightblue.png')
    pw, ph = c.size(f'{BG}background_graveyard_1.png')
    panels = [f'{BG}background_graveyard_{i}.png' for i in (1, 2, 3)]
    x = -pw // 2
    i = 0
    while x < W:
        c.blit(panels[i % 3], x, c.gy + 8, anchor='bl', w=pw, h=ph)
        c.blit(f'{BG}background_graveyard_top.png', x, c.gy + 8 - ph, anchor='bl', w=pw, h=ph)
        x += pw
        i += 1
    c.moon(f'{BG}moon_half.png', int(W * 0.86), 110, 150)
    c.ground(GY_TOP + GY_BARE, GY_FILL)
    c.ground_row([(f'{BG}tree_1__no_vegetation_base.png', 0.75), (f'{BG}strangeTree.png', 0.8)],
                 [int(W * 0.14), int(W * 0.80)], sink=4)
    c.ground_row([(f'{BG}dino_bones.png', 0.7)], [int(W * 0.50)], sink=2)
    c.ground_row([(f'{BG}grave.png', 1.0), (f'{BG}grave.png', 0.9), (f'{BG}coffin_dark.png', 1.0),
                  (f'{BG}open_coffin.png', 1.0), (f'{BG}bones.png', 1.0), (f'{BG}standing_stone.png', 1.0),
                  (f'{BG}statue_1_with_vegetation.png', 1.0), ('food/pumpkin.png', 1.0), ('food/pumpkin.png', 0.9)],
                 [int(W * 0.30), int(W * 0.62), int(W * 0.44), int(W * 0.92), int(W * 0.72),
                  int(W * 0.06), int(W * 0.54), int(W * 0.38), int(W * 0.84)], sink=4)
    for x in (int(W * 0.20), int(W * 0.25)):
        c.blit(f'{TL}fence.png', x, c.gy + 4, anchor='bc')
    c.blit('teleports/wooden_doors_graveyard.png', int(W * 0.985), c.gy + 6, anchor='br')


def space(c):
    c.sky(f'{BG}background_lightblue_to_purple.jpg', y_bottom=H)
    c.panel_wall([f'{BG}background_space_{i}.png' for i in (1, 2, 3, 4)], y_bottom=H, x_shift=90)
    c.moon(f'{BG}moon_full.png', int(W * 0.80), 130, 210)
    c.blit(f'{BG}space_rock_1.png', int(W * 0.05), 250, scale=c.s * 0.9, anchor='tl')
    c.blit(f'{BG}space_rock_2.png', int(W * 0.62), 560, scale=c.s * 0.9, anchor='tl')
    c.blit(f'{BG}space_rock_3.png', int(W * 0.86), 420, scale=c.s * 0.9, anchor='tl')
    t = int(TILE * c.s)
    plats = [(int(W * 0.08), 640, 9), (int(W * 0.46), 500, 7), (int(W * 0.72), 300, 6), (int(W * 0.28), 340, 4)]
    for x, y, n in plats:
        c.platform(DIRT_GRASS, DIRT, x, y, n)
    px = [(plats[0][0] + 2 * t, plats[0][1]), (plats[0][0] + 6 * t, plats[0][1]),
          (plats[1][0] + 3 * t, plats[1][1]), (plats[2][0] + t, plats[2][1]), (plats[3][0] + 2 * t, plats[3][1])]
    props = [f'{TL}cosmic_plant.png', 'food/alienFruit/1.png', f'{TL}cosmic_plant.png', 'food/egg_cosmic.png',
             'food/alienFruit/2.png']
    for (x, y), p in zip(px, props):
        c.blit(p, x, y + 4, anchor='bc')
    c.blit('food/alienFruit/3.png', plats[1][0] + 5 * t, plats[1][1] + 4, anchor='bc')
    c.blit('food/egg_cosmic.png', plats[2][0] + 4 * t, plats[2][1] + 4, anchor='bc')


def jungle(c):
    c.sky(f'{BG}background_lightblue.png')
    c.panel_wall([f'{BG}background_jungle_{i}.png' for i in (1, 2, 3)], y_bottom=c.gy + 10, x_shift=40, rows=1)
    c.ground([f'{TL}jungleTop.png'], [f'{TL}jungleBottom.png'])
    c.ground_row([(f'{BG}jungleTree2.png', 0.9), (f'{BG}jungleTree1.png', 0.9), (f'{BG}strangeTree.png', 0.85)],
                 [int(W * 0.14), int(W * 0.88), int(W * 0.50)], sink=4)
    c.ground_row([(f'{BG}thorn_branch_3.png', 1.0), (f'{BG}thorn_branch_2.png', 1.0), ('food/pig/2.png', 1.0),
                  ('food/frog/1.png', 2.0), ('food/frog/5.png', 2.0), (f'{TL}stalk_light_green.png', 1.2),
                  (f'{TL}stalk_light_green.png', 1.0), ('food/starFruit.png', 1.0), ('bushes/bush_1_bright_green.png', 1.0)],
                 [int(W * 0.30), int(W * 0.70), int(W * 0.40), int(W * 0.60), int(W * 0.78), int(W * 0.06),
                  int(W * 0.24), int(W * 0.66), int(W * 0.94)], sink=4)
    c.blit('teleports/wooden_doors_jungle.png', int(W * 0.20), c.gy + 6, anchor='bl')


def arena(c):
    c.s = 0.5
    c.gy = H - 3 * int(TILE * c.s)
    c.sky(f'{BG}background_lightblue.png')
    c.strips('normal')
    c.clouds(2, (30, 160))
    c.ground(DIRT_GRASS, DIRT)
    c.ground_row([(c.rng.choice(TREES), 0.95)], [int(W * 0.09)], sink=4)
    c.ground_row([(f'{BG}arena.png', 1.0)], [int(W * 0.60)], sink=6)
    c.ground_row([('teleports/arena_doors_1.png', 1.0), ('teleports/arena_doors_2.png', 1.0)],
                 [int(W * 0.26), int(W * 0.93)], sink=6)
    c.ground_row([(f'{BG}arena_statue_1.png', 1.0), (f'{BG}arena_statue_1.png', 1.0),
                  (f'{BG}brick_post_1.png', 1.0), ('bushes/bush_1_bright_green.png', 1.0)],
                 [int(W * 0.34), int(W * 0.86), int(W * 0.18), int(W * 0.45)], sink=4)
    for x in c.spread(5, 60, int(W * 0.5), 30):
        c.blit(c.rng.choice(FLOWERS), x, c.gy + 4, anchor='bc')


def catacombs(c):
    c.s = 0.75
    c.gy = H - 2 * int(TILE * c.s)
    cw, ch = c.size(f'{BG}castle_bg.png')
    y = c.gy
    while y > -ch:
        for x in range(-cw // 3, W, cw):
            c.blit(f'{BG}castle_bg.png', x, y - ch, anchor='tl', w=cw, h=ch)
        y -= ch
    c.ground([f'{TL}brick_grey.png'], [f'{TL}brick_grey.png'])
    doors = ['teleports/wooden_doors_city.png', 'teleports/wooden_doors_desert.png', 'teleports/wooden_doors_graveyard.png',
             'teleports/wooden_doors_ice.png', 'teleports/wooden_doors_jungle.png']
    xs = [int(W * f) for f in (0.11, 0.305, 0.50, 0.695, 0.89)]
    for d, x in zip(doors, xs):
        c.blit(d, x, c.gy + 2, anchor='bc')
    pb = c.size(f'{BG}pillar_bottom.png')[1]
    pc = c.size(f'{BG}pillar_center.png')[1]
    for x in (int(W * 0.2075), int(W * 0.4025), int(W * 0.5975), int(W * 0.7925)):
        y = c.gy + 2
        if c._open(f'{BG}pillar_bottom.png'):
            c.blit(f'{BG}pillar_bottom.png', x, y, anchor='bc')
            yy = y - pb
            while yy > pb:
                c.blit(f'{BG}pillar_center.png', x, yy, anchor='bc')
                yy -= pc
            c.blit(f'{BG}pillar_top.png', x, yy, anchor='bc')
        else:
            c.blit(f'{BG}brick_post_1.png', x, y, anchor='bc')
    c.ground_row([(f'{BG}arena_statue_1.png', 1.0), (f'{BG}arena_statue_1.png', 1.0)],
                 [int(W * 0.02), int(W * 0.98)], sink=2)
    c.ground_row([(f'{BG}coffin_dark.png', 0.9), (f'{BG}bones.png', 0.8), ('food/pumpkin.png', 1.0),
                  (f'{BG}open_coffin.png', 0.8), (f'{BG}standing_stone.png', 0.8), ('food/meat.png', 1.0)],
                 [int(W * 0.255), int(W * 0.45), int(W * 0.55), int(W * 0.745), int(W * 0.155), int(W * 0.845)], sink=2)


SCENES = {
    'village': village, 'desert': desert, 'beach': beach, 'snow': snow, 'volcano': volcano,
    'graveyard': graveyard, 'space': space, 'jungle': jungle, 'arena': arena, 'catacombs': catacombs,
}
PAID_ORDER = ['village', 'desert', 'beach', 'snow', 'volcano', 'graveyard', 'space', 'jungle', 'arena', 'catacombs']
FREE_ORDER = ['village', 'desert', 'snow', 'graveyard', 'space']


def render(pack, scene_name):
    seed = sum(map(ord, pack['folder'] + scene_name))
    c = Scene(pack, seed)
    SCENES[scene_name](c)
    return c.rgb()


def contact_sheet(folder, names):
    tiles = []
    for n in names:
        f = os.path.join(OUT_DIR, folder, n + '.webp')
        if os.path.exists(f):
            tiles.append(Image.open(f).convert('RGB').resize((640, 400), Image.LANCZOS))
    if not tiles:
        return
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 640, rows * 400), (20, 20, 20))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 640, (i // cols) * 400))
    out = f'/tmp/gallery_{folder}.jpg'
    sheet.save(out, quality=82)
    print('sheet', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', help='pack folder name (default: all)')
    ap.add_argument('--scene', help='scene name (default: the pack\'s full set)')
    ap.add_argument('--sheet', action='store_true')
    a = ap.parse_args()
    for pid, pack in PACK_RULES.items():
        if a.pack and pack['folder'] != a.pack:
            continue
        names = FREE_ORDER if pack['is_free'] else PAID_ORDER
        if a.scene:
            names = [a.scene]
        dst = os.path.join(OUT_DIR, pack['folder'])
        os.makedirs(dst, exist_ok=True)
        for n in names:
            im = render(pack, n)
            f = os.path.join(dst, n + '.webp')
            im.save(f, 'WEBP', quality=84, method=6)
            print(f'{pack["name"]:<20} {n:<10} {os.path.getsize(f) // 1024} KB')
        if a.sheet:
            contact_sheet(pack['folder'], names)


if __name__ == '__main__':
    main()
