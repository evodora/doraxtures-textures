#!/usr/bin/env python3
"""Art for the doraxtures.site landing page.

gallery_art.py seeds every scene from the pack's folder name, so two packs'
villages pick different houses and trees. Here one seed is shared by every
pack and by the game's own textures, so a wipe from any pack to any other
changes the textures and nothing else — the landing page's before/after hero,
its "exploded layers" scene and its repaint loops depend on that.

Outputs (site/landing/), key = 'default' for the game's own textures, else the
pack folder:
  village/<key>.webp        1280x800  hero compare, large cards
  village-sm/<key>.webp      640x400  the same scene for small screens and cards
  taxi/<key>.webp            the pack's EvoTaxi airship, cropped, 360 px wide
  cloud/<key>.webp           the pack's first cloud, cropped, 240 px wide
  thumbs/<folder>-<scene>.webp  480x300 from site/gallery, for marquees
  layers/<key>/<n>-<name>.webp  960x600 transparent layers of the village
                                (LAYER_KEYS only), stacked they rebuild village/<key>

    python3 tools/landing_art.py                      # everything (~3 min)
    python3 tools/landing_art.py --only layers        # scenes | props | thumbs | layers
"""
import argparse
import importlib.util
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('gallery_art', os.path.join(HERE, 'gallery_art.py'))
ga = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ga)

OUT = os.path.join(ROOT, 'site', 'landing')
GALLERY = os.path.join(ROOT, 'site', 'gallery')
SEED = 7331
DEFAULT = {'name': 'Default', 'folder': 'default', 'is_free': 1, 'rules': {}}
THUMB_SCENES = ['arena', 'beach', 'snow', 'volcano', 'graveyard', 'catacombs', 'space', 'jungle', 'desert']
LAYER_KEYS = ['default', 'magma-world']
STEPS = ['scenes', 'props', 'thumbs', 'layers']


def save(im, *parts, quality=80):
    f = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    im.save(f, 'WEBP', quality=quality, method=6)
    return os.path.getsize(f) // 1024


def cropped(img, width):
    box = img.getchannel('A').getbbox()
    if not box:
        return None
    img = img.crop(box)
    return img.resize((width, max(1, round(img.height * width / img.width))), Image.LANCZOS)


def village_layers(pack):
    """The village() recipe of gallery_art.py, drawn onto a fresh transparent
    canvas per layer. The calls (and so the rng draws) run in exactly the same
    order as village(), so the stacked layers equal the full scene."""
    c = ga.Scene(pack, SEED)
    W, H = ga.W, ga.H
    layers = []

    def layer(name, draw):
        c.canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw()
        layers.append((name, c.canvas))

    layer('sky', lambda: c.sky(f'{ga.BG}background_lightblue.png'))
    layer('skyline', lambda: c.strips('normal'))

    def air():
        c.clouds(3)
        c.taxi(W - 330, 30)
    layer('air', air)
    layer('ground', lambda: c.ground(ga.DIRT_GRASS, ga.DIRT))

    def trees():
        t = c.rng.sample(ga.TREES, 2)
        c.ground_row([(t[0], 1.0), (t[1], 0.9)], [int(W * 0.30), int(W * 0.68)], sink=4)
    layer('trees', trees)

    def houses():
        hs = c.rng.sample(ga.HOUSES, 3)
        c.ground_row([(h, 1.0) for h in hs], [int(W * 0.14), int(W * 0.50), int(W * 0.86)])
        c.ground_row([('bushes/bush_1_bright_green.png', 1.0), ('bushes/strawberry_bush.png', 1.0),
                      ('food/pumpkin.png', 1.0), ('food/pig/1.png', 1.0)],
                     [int(W * 0.32), int(W * 0.60), int(W * 0.70), int(W * 0.40)], sink=4)
        for x in c.spread(6, 40, W - 40, 30):
            c.blit(c.rng.choice(ga.FLOWERS), x, c.gy + 4, anchor='bc')
        c.blit('teleports/wooden_doors.png', int(W * 0.975), c.gy + 6, anchor='br')
    layer('houses', houses)
    return layers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='comma-separated steps: ' + ', '.join(STEPS))
    steps = set((ap.parse_args().only or ','.join(STEPS)).split(','))

    packs = [('default', DEFAULT)] + [(p['folder'], p) for p in ga.PACK_RULES.values()]
    for i, (key, pack) in enumerate(packs):
        kb = []
        if 'scenes' in steps:
            scene = ga.Scene(pack, SEED)
            ga.SCENES['village'](scene)
            big = scene.rgb()
            kb += [save(big, 'village', key + '.webp', quality=80),
                   save(big.resize((640, 400), Image.LANCZOS), 'village-sm', key + '.webp', quality=78)]

        if 'props' in steps:
            props = ga.Scene(pack, SEED)
            for vpath, folder, width in (('teleports/taxi.png', 'taxi', 360), ('clouds/cloud1.png', 'cloud', 240)):
                img = props._open(vpath)
                prop = cropped(img, width) if img else None
                if prop is not None:
                    kb.append(save(prop, folder, key + '.webp', quality=84))

        if 'thumbs' in steps and key != 'default':
            names = ['village'] if pack['is_free'] else [THUMB_SCENES[i % len(THUMB_SCENES)], 'arena']
            for n in dict.fromkeys(names):
                src = os.path.join(GALLERY, key, n + '.webp')
                if os.path.exists(src):
                    th = Image.open(src).convert('RGB').resize((480, 300), Image.LANCZOS)
                    kb.append(save(th, 'thumbs', f'{key}-{n}.webp', quality=72))

        if 'layers' in steps and key in LAYER_KEYS:
            stack = Image.new('RGBA', (ga.W, ga.H), (0, 0, 0, 255))
            for n, (name, im) in enumerate(village_layers(pack)):
                stack.alpha_composite(im)
                kb.append(save(im.resize((960, 600), Image.LANCZOS), 'layers', key, f'{n}-{name}.webp', quality=82))
            ref = ga.Scene(pack, SEED)
            ga.SCENES['village'](ref)
            diff = sum(abs(a - b) for a, b in zip(stack.convert('RGB').tobytes()[::97], ref.rgb().tobytes()[::97]))
            print(f'  layers/{key}: stacked vs full scene, sampled abs diff = {diff}')

        if kb:
            print(f'{pack["name"]:<20} {kb} KB')


if __name__ == '__main__':
    main()
