#!/usr/bin/env python3
"""Art for the doraxtures.site landing page.

gallery_art.py seeds every scene from the pack's folder name, so two packs'
villages pick different houses and trees. Here one seed is shared by every
pack and by the game's own textures, so a wipe from any pack to any other
changes the textures and nothing else — the landing page's before/after hero
and its scroll-driven "repaint" scene depend on that.

Outputs (site/landing/), key = 'default' for the game's own textures, else the
pack folder:
  village/<key>.webp        1280x800  hero compare, repaint scene, large cards
  village-sm/<key>.webp      640x400  the same scene for small screens and cards
  taxi/<key>.webp            the pack's EvoTaxi airship, cropped, 360 px wide
  cloud/<key>.webp           the pack's first cloud, cropped, 240 px wide
  thumbs/<folder>-<scene>.webp  480x300 from site/gallery, for marquees

    python3 tools/landing_art.py
"""
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


def main():
    packs = [('default', DEFAULT)] + [(p['folder'], p) for p in ga.PACK_RULES.values()]
    for i, (key, pack) in enumerate(packs):
        scene = ga.Scene(pack, SEED)
        ga.SCENES['village'](scene)
        big = scene.rgb()
        kb = [save(big, 'village', key + '.webp', quality=80),
              save(big.resize((640, 400), Image.LANCZOS), 'village-sm', key + '.webp', quality=78)]

        props = ga.Scene(pack, SEED)
        for vpath, folder, width in (('teleports/taxi.png', 'taxi', 360), ('clouds/cloud1.png', 'cloud', 240)):
            img = props._open(vpath)
            prop = cropped(img, width) if img else None
            if prop is not None:
                kb.append(save(prop, folder, key + '.webp', quality=84))

        if key != 'default':
            names = ['village'] if pack['is_free'] else [THUMB_SCENES[i % len(THUMB_SCENES)], 'arena']
            for n in dict.fromkeys(names):
                src = os.path.join(GALLERY, key, n + '.webp')
                if os.path.exists(src):
                    th = Image.open(src).convert('RGB').resize((480, 300), Image.LANCZOS)
                    kb.append(save(th, 'thumbs', f'{key}-{n}.webp', quality=72))
        print(f'{pack["name"]:<20} {kb} KB')


if __name__ == '__main__':
    main()
