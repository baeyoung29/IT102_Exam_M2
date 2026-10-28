import math
import os

import pygame

from . import config as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets")

ICON_NAMES = [
    "feed", "shop", "inventory", "schedule", "bell", "settings", "pet", "play",
    "coin", "heart", "hunger", "happy", "weight", "clock", "close",
    "kibble", "wetfood", "fish", "premium", "treats", "vitamins", "toy",
    "studycoin", "class", "streak", "check", "plus", "goldfish", "catbed", "plant", "lights",
]
SOUND_NAMES = ["click", "buy", "feed", "notify", "warn", "success", "purr"]
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _find(folder, name, exts):
    for ext in exts:
        for candidate in (name, name.upper(), name.capitalize()):
            p = os.path.join(ASSET_DIR, folder, candidate + ext)
            if os.path.exists(p):
                return p
    return None


def _s(size):
    return pygame.Surface((size, size), pygame.SRCALPHA)


def _icon_coin(sz):
    s = _s(sz); c = sz // 2
    pygame.draw.circle(s, (230, 170, 50), (c, c), int(sz * .45))
    pygame.draw.circle(s, (250, 205, 90), (c, c), int(sz * .36))
    pygame.draw.circle(s, (230, 170, 50), (c, c), int(sz * .36), max(1, sz // 24))
    w = max(2, sz // 12)
    pygame.draw.line(s, (180, 120, 30), (c - sz * .1, c - sz * .2), (c - sz * .1, c + sz * .22), w)
    pygame.draw.arc(s, (180, 120, 30), (c - sz * .12, c - sz * .22, sz * .28, sz * .24),
                    -math.pi / 2, math.pi / 2, w)
    pygame.draw.line(s, (180, 120, 30), (c - sz * .2, c - sz * .12), (c + sz * .18, c - sz * .12), max(1, w // 2))
    pygame.draw.line(s, (180, 120, 30), (c - sz * .2, c - sz * .04), (c + sz * .18, c - sz * .04), max(1, w // 2))
    return s


def _heart_points(cx, cy, r, n=40):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * r / 17, cy + y * r / 17))
    return pts


def _icon_heart(sz, color=(230, 96, 110)):
    s = _s(sz)
    pygame.draw.polygon(s, color, _heart_points(sz / 2, sz / 2 + sz * .02, sz * .42))
    pygame.draw.circle(s, (255, 255, 255, 120), (int(sz * .36), int(sz * .36)), max(1, sz // 12))
    return s


def _icon_bowl(sz, food=(214, 160, 92)):
    s = _s(sz)
    pygame.draw.ellipse(s, food, (sz * .18, sz * .3, sz * .64, sz * .3))
    for i in range(5):
        pygame.draw.circle(s, tuple(max(0, v - 30) for v in food),
                           (int(sz * (.3 + i * .1)), int(sz * (.4 + (i % 2) * .05))), max(1, sz // 16))
    pygame.draw.polygon(s, (232, 120, 96), [(sz * .1, sz * .45), (sz * .9, sz * .45),
                                             (sz * .76, sz * .8), (sz * .24, sz * .8)])
    pygame.draw.rect(s, (200, 96, 74), (sz * .1, sz * .43, sz * .8, sz * .07), border_radius=sz // 16)
    return s


def _icon_bag(sz):
    s = _s(sz)
    pygame.draw.rect(s, (110, 160, 210), (sz * .18, sz * .32, sz * .64, sz * .52), border_radius=sz // 10)
    pygame.draw.arc(s, (70, 110, 160), (sz * .32, sz * .12, sz * .36, sz * .42), 0, math.pi, max(2, sz // 14))
    pygame.draw.polygon(s, (255, 255, 255), _heart_points(sz / 2, sz * .58, sz * .13))
    return s


def _icon_box(sz):
    s = _s(sz)
    pygame.draw.rect(s, (205, 160, 110), (sz * .14, sz * .34, sz * .72, sz * .52), border_radius=sz // 14)
    pygame.draw.rect(s, (180, 132, 86), (sz * .1, sz * .24, sz * .8, sz * .16), border_radius=sz // 14)
    pygame.draw.rect(s, (240, 220, 190), (sz * .42, sz * .24, sz * .16, sz * .62))
    return s


def _icon_calendar(sz):
    s = _s(sz)
    pygame.draw.rect(s, (255, 255, 255), (sz * .14, sz * .2, sz * .72, sz * .66), border_radius=sz // 10)
    pygame.draw.rect(s, (232, 120, 96), (sz * .14, sz * .2, sz * .72, sz * .2),
                     border_top_left_radius=sz // 10, border_top_right_radius=sz // 10)
    pygame.draw.rect(s, (180, 160, 140), (sz * .14, sz * .2, sz * .72, sz * .66), max(1, sz // 24), border_radius=sz // 10)
    for r in range(2):
        for c in range(3):
            pygame.draw.rect(s, (200, 180, 160), (sz * (.24 + c * .18), sz * (.5 + r * .16), sz * .1, sz * .08))
    for x in (.32, .68):
        pygame.draw.line(s, (120, 100, 90), (sz * x, sz * .12), (sz * x, sz * .28), max(2, sz // 14))
    return s


def _icon_bell(sz):
    s = _s(sz)
    col = (240, 190, 70)
    pygame.draw.polygon(s, col, [(sz * .22, sz * .7), (sz * .3, sz * .38), (sz * .5, sz * .2),
                                 (sz * .7, sz * .38), (sz * .78, sz * .7)])
    pygame.draw.circle(s, col, (int(sz * .5), int(sz * .38)), int(sz * .2))
    pygame.draw.rect(s, (220, 160, 50), (sz * .16, sz * .66, sz * .68, sz * .08), border_radius=sz // 16)
    pygame.draw.circle(s, (200, 140, 40), (int(sz * .5), int(sz * .8)), max(2, sz // 12))
    return s


def _icon_gear(sz):
    s = _s(sz); c = sz / 2
    pts = []
    for i in range(16):
        r = sz * (.44 if i % 2 == 0 else .34)
        a = i * math.pi / 8
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    pygame.draw.polygon(s, (150, 140, 135), pts)
    pygame.draw.circle(s, (150, 140, 135), (int(c), int(c)), int(sz * .34))
    pygame.draw.circle(s, (0, 0, 0, 0), (int(c), int(c)), int(sz * .14))
    return s


def _icon_paw(sz, col=(200, 140, 110)):
    s = _s(sz)
    pygame.draw.ellipse(s, col, (sz * .28, sz * .45, sz * .44, sz * .38))
    for x, y in ((.22, .36), (.4, .22), (.6, .22), (.78, .36)):
        pygame.draw.ellipse(s, col, (sz * (x - .09), sz * (y - .1), sz * .18, sz * .22))
    return s


def _icon_ball(sz):
    s = _s(sz); c = int(sz / 2)
    pygame.draw.circle(s, (240, 110, 110), (c, c), int(sz * .38))
    pygame.draw.arc(s, (255, 255, 255), (sz * .12, sz * .3, sz * .76, sz * .4), 0, math.pi, max(2, sz // 14))
    pygame.draw.arc(s, (255, 255, 255), (sz * .12, sz * .3, sz * .76, sz * .4), math.pi, 2 * math.pi, max(2, sz // 14))
    return s


def _icon_drumstick(sz):
    s = _s(sz)
    pygame.draw.ellipse(s, (210, 130, 70), (sz * .12, sz * .14, sz * .5, sz * .44))
    pygame.draw.line(s, (245, 235, 220), (sz * .5, sz * .5), (sz * .78, sz * .78), max(3, sz // 8))
    pygame.draw.circle(s, (245, 235, 220), (int(sz * .8), int(sz * .74)), max(2, sz // 12))
    pygame.draw.circle(s, (245, 235, 220), (int(sz * .74), int(sz * .82)), max(2, sz // 12))
    return s


def _icon_smile(sz):
    s = _s(sz); c = int(sz / 2)
    pygame.draw.circle(s, (245, 200, 70), (c, c), int(sz * .42))
    pygame.draw.circle(s, (90, 60, 40), (int(sz * .36), int(sz * .4)), max(2, sz // 14))
    pygame.draw.circle(s, (90, 60, 40), (int(sz * .64), int(sz * .4)), max(2, sz // 14))
    pygame.draw.arc(s, (90, 60, 40), (sz * .28, sz * .36, sz * .44, sz * .34), math.pi * 1.1, math.pi * 1.9, max(2, sz // 16))
    return s


def _icon_scale(sz):
    s = _s(sz)
    pygame.draw.rect(s, (120, 168, 200), (sz * .14, sz * .2, sz * .72, sz * .64), border_radius=sz // 6)
    pygame.draw.circle(s, (240, 245, 250), (int(sz * .5), int(sz * .44)), int(sz * .2))
    pygame.draw.line(s, (220, 90, 90), (sz * .5, sz * .44), (sz * .6, sz * .32), max(2, sz // 18))
    return s


def _icon_clock(sz):
    s = _s(sz); c = int(sz / 2)
    pygame.draw.circle(s, (255, 255, 255), (c, c), int(sz * .42))
    pygame.draw.circle(s, (120, 100, 90), (c, c), int(sz * .42), max(2, sz // 16))
    pygame.draw.line(s, (120, 100, 90), (c, c), (c, sz * .24), max(2, sz // 16))
    pygame.draw.line(s, (120, 100, 90), (c, c), (sz * .68, c), max(2, sz // 16))
    return s


def _icon_close(sz):
    s = _s(sz); w = max(2, sz // 8)
    pygame.draw.line(s, (140, 120, 104), (sz * .25, sz * .25), (sz * .75, sz * .75), w)
    pygame.draw.line(s, (140, 120, 104), (sz * .75, sz * .25), (sz * .25, sz * .75), w)
    return s


def _icon_fish(sz):
    s = _s(sz)
    pygame.draw.ellipse(s, (110, 160, 200), (sz * .12, sz * .3, sz * .6, sz * .4))
    pygame.draw.polygon(s, (90, 140, 185), [(sz * .66, sz * .5), (sz * .9, sz * .3), (sz * .9, sz * .7)])
    pygame.draw.circle(s, (40, 40, 60), (int(sz * .26), int(sz * .46)), max(1, sz // 18))
    return s


def _icon_can(sz):
    s = _s(sz)
    pygame.draw.rect(s, (196, 108, 84), (sz * .2, sz * .22, sz * .6, sz * .6), border_radius=sz // 10)
    pygame.draw.ellipse(s, (210, 210, 215), (sz * .2, sz * .14, sz * .6, sz * .18))
    pygame.draw.rect(s, (255, 240, 220), (sz * .2, sz * .42, sz * .6, sz * .18))
    pygame.draw.polygon(s, (110, 160, 200), [(sz * .35, sz * .51), (sz * .55, sz * .45),
                                              (sz * .55, sz * .57)])
    return s


def _icon_pack(sz, col):
    s = _s(sz)
    pygame.draw.rect(s, col, (sz * .2, sz * .14, sz * .6, sz * .72), border_radius=sz // 8)
    pygame.draw.rect(s, tuple(max(0, v - 40) for v in col), (sz * .2, sz * .14, sz * .6, sz * .12),
                     border_top_left_radius=sz // 8, border_top_right_radius=sz // 8)
    pygame.draw.polygon(s, (255, 255, 255), _heart_points(sz / 2, sz * .52, sz * .14))
    return s


def _icon_pill(sz):
    s = _s(sz)
    surf = pygame.Surface((int(sz * .84), int(sz * .38)), pygame.SRCALPHA)
    w, h = surf.get_size()
    pygame.draw.rect(surf, (96, 176, 104), (0, 0, w // 2 + 2, h), border_top_left_radius=h // 2,
                     border_bottom_left_radius=h // 2)
    pygame.draw.rect(surf, (246, 240, 226), (w // 2, 0, w - w // 2, h), border_top_right_radius=h // 2,
                     border_bottom_right_radius=h // 2)
    pygame.draw.rect(surf, (70, 130, 80), (0, 0, w, h), max(1, sz // 24), border_radius=h // 2)
    surf = pygame.transform.rotate(surf, 35)
    s.blit(surf, surf.get_rect(center=(sz // 2, sz // 2)))
    return s


def _icon_mouse_toy(sz):
    s = _s(sz)
    pygame.draw.ellipse(s, (160, 160, 170), (sz * .18, sz * .38, sz * .56, sz * .34))
    pygame.draw.circle(s, (190, 190, 200), (int(sz * .62), int(sz * .38)), int(sz * .09))
    pygame.draw.circle(s, (40, 40, 50), (int(sz * .68), int(sz * .5)), max(1, sz // 20))
    pygame.draw.arc(s, (150, 120, 120), (sz * .02, sz * .3, sz * .3, sz * .4), math.pi / 2, math.pi * 1.4, max(1, sz // 24))
    return s


def _icon_studycoin(sz):
    s = _s(sz); c = sz / 2
    pygame.draw.circle(s, (92, 76, 170), (int(c), int(c + sz * .03)), int(sz * .45))
    pygame.draw.circle(s, (130, 112, 214), (int(c), int(c)), int(sz * .45))
    pygame.draw.circle(s, (160, 144, 232), (int(c), int(c)), int(sz * .35))
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = sz * (.27 if i % 2 == 0 else .12)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    pygame.draw.polygon(s, (255, 226, 120), pts)
    pygame.draw.circle(s, (255, 255, 255, 110), (int(sz * .34), int(sz * .3)), max(1, sz // 14))
    return s


def _icon_cap(sz):
    s = _s(sz); c = sz / 2
    dark, mid = (60, 64, 92), (84, 90, 128)
    pygame.draw.polygon(s, mid, [(sz * .3, sz * .5), (sz * .7, sz * .5), (sz * .68, sz * .72),
                                 (sz * .32, sz * .72)])
    pygame.draw.ellipse(s, dark, (sz * .3, sz * .64, sz * .4, sz * .14))
    pygame.draw.polygon(s, dark, [(c, sz * .2), (sz * .94, sz * .4), (c, sz * .6), (sz * .06, sz * .4)])
    pygame.draw.polygon(s, mid, [(c, sz * .24), (sz * .84, sz * .4), (c, sz * .55), (sz * .16, sz * .4)])
    pygame.draw.line(s, (240, 190, 70), (c, sz * .4), (sz * .82, sz * .46), max(2, sz // 22))
    pygame.draw.line(s, (240, 190, 70), (sz * .82, sz * .46), (sz * .82, sz * .7), max(2, sz // 22))
    pygame.draw.circle(s, (240, 190, 70), (int(sz * .82), int(sz * .74)), max(2, sz // 14))
    return s


def _icon_flame(sz):
    s = _s(sz)
    outer = [(sz * .5, sz * .08), (sz * .74, sz * .36), (sz * .82, sz * .62), (sz * .7, sz * .84),
             (sz * .5, sz * .92), (sz * .3, sz * .84), (sz * .18, sz * .62), (sz * .28, sz * .42),
             (sz * .38, sz * .5), (sz * .4, sz * .3)]
    pygame.draw.polygon(s, (236, 110, 70), outer)
    inner = [(sz * .52, sz * .42), (sz * .66, sz * .62), (sz * .62, sz * .8), (sz * .5, sz * .86),
             (sz * .38, sz * .8), (sz * .36, sz * .64)]
    pygame.draw.polygon(s, (250, 200, 80), inner)
    return s


def _icon_check(sz):
    s = _s(sz); c = int(sz / 2)
    pygame.draw.circle(s, (104, 176, 120), (c, c), int(sz * .44))
    w = max(3, sz // 9)
    pygame.draw.lines(s, (255, 255, 255), False, [(sz * .28, sz * .52), (sz * .44, sz * .68),
                                                  (sz * .72, sz * .36)], w)
    return s


def _icon_plus(sz):
    s = _s(sz); w = max(3, sz // 7)
    pygame.draw.line(s, (255, 255, 255), (sz * .5, sz * .2), (sz * .5, sz * .8), w)
    pygame.draw.line(s, (255, 255, 255), (sz * .2, sz * .5), (sz * .8, sz * .5), w)
    return s


def _icon_goldfish(sz):
    s = _s(sz)
    pygame.draw.ellipse(s, (232, 170, 50), (sz * .12, sz * .3, sz * .6, sz * .4))
    pygame.draw.ellipse(s, (252, 214, 100), (sz * .18, sz * .34, sz * .44, sz * .22))
    pygame.draw.polygon(s, (226, 150, 40), [(sz * .66, sz * .5), (sz * .92, sz * .28), (sz * .92, sz * .72)])
    pygame.draw.circle(s, (60, 40, 30), (int(sz * .26), int(sz * .46)), max(1, sz // 18))
    for x, y in ((.8, .14), (.14, .18), (.88, .86)):
        pygame.draw.circle(s, (255, 236, 150), (int(sz * x), int(sz * y)), max(1, sz // 20))
    return s


def _icon_catbed(sz):
    s = _s(sz)
    pygame.draw.ellipse(s, (120, 92, 170), (sz * .06, sz * .36, sz * .88, sz * .5))
    pygame.draw.ellipse(s, (176, 150, 220), (sz * .16, sz * .4, sz * .68, sz * .3))
    pygame.draw.ellipse(s, (246, 236, 250), (sz * .24, sz * .46, sz * .52, sz * .2))
    return s


def _icon_plant(sz):
    s = _s(sz)
    for ang, col in ((-.9, (84, 150, 100)), (-.3, (104, 176, 120)), (.3, (96, 168, 112)), (.9, (84, 150, 100))):
        cx = sz * (.5 + ang * .2)
        pygame.draw.ellipse(s, col, (cx - sz * .12, sz * (.14 + abs(ang) * .1), sz * .24, sz * .42))
    pygame.draw.polygon(s, (214, 130, 92), [(sz * .28, sz * .56), (sz * .72, sz * .56), (sz * .64, sz * .9),
                                            (sz * .36, sz * .9)])
    pygame.draw.rect(s, (190, 110, 76), (sz * .25, sz * .54, sz * .5, sz * .08), border_radius=sz // 20)
    return s


def _icon_lights(sz):
    s = _s(sz)
    pygame.draw.arc(s, (110, 100, 90), (sz * .02, -sz * .2, sz * .96, sz * .8), math.pi * 1.05, math.pi * 1.95,
                    max(1, sz // 24))
    cols = [(240, 110, 110), (240, 196, 72), (110, 170, 230), (120, 200, 130), (220, 130, 220)]
    for i in range(5):
        t = (i + .5) / 5
        x = sz * (.08 + .84 * t)
        y = sz * (.2 + .38 * math.sin(math.pi * t))
        pygame.draw.circle(s, cols[i], (int(x), int(y + sz * .1)), max(2, sz // 10))
    return s


FALLBACK = {
    "feed": _icon_bowl, "shop": _icon_bag, "inventory": _icon_box, "schedule": _icon_calendar,
    "bell": _icon_bell, "settings": _icon_gear, "pet": _icon_paw, "play": _icon_ball,
    "coin": _icon_coin, "heart": _icon_heart, "hunger": _icon_drumstick, "happy": _icon_smile,
    "weight": _icon_scale, "clock": _icon_clock, "close": _icon_close,
    "kibble": lambda sz: _icon_bowl(sz, (214, 160, 92)),
    "wetfood": _icon_can, "fish": _icon_fish,
    "premium": lambda sz: _icon_pack(sz, (150, 120, 190)),
    "treats": lambda sz: _icon_pack(sz, (236, 130, 160)),
    "vitamins": _icon_pill, "toy": _icon_mouse_toy,
    "studycoin": _icon_studycoin, "class": _icon_cap, "streak": _icon_flame, "check": _icon_check,
    "plus": _icon_plus, "goldfish": _icon_goldfish, "catbed": _icon_catbed, "plant": _icon_plant,
    "lights": _icon_lights,
}


class Assets:
    def __init__(self):
        self.fonts = {}
        self._font_path = None
        self._sysfont_name = None
        self.pets = {}
        self.icons_src = {}
        self._icon_cache = {}
        self.room = None
        self.sounds = {}
        self.volume = 0.6
        self.sound_on = True

    def load(self):
        self._load_fonts()
        self._load_pets()
        self._load_icons()
        bg = _find("backgrounds", "room", IMAGE_EXTS)
        if bg:
            self.room = pygame.image.load(bg).convert()
        self._load_sounds()

    def _load_fonts(self):
        fdir = os.path.join(ASSET_DIR, "fonts")
        if os.path.isdir(fdir):
            for f in sorted(os.listdir(fdir)):
                if f.lower().endswith((".ttf", ".otf")):
                    self._font_path = os.path.join(fdir, f)
                    break
        if not self._font_path:
            for name in ("segoeui", "segoeuisemibold", "arial", "dejavusans", "notosans",
                         "helvetica", "freesans"):
                if pygame.font.match_font(name):
                    self._sysfont_name = name
                    break
        f = self.font(20)
        try:
            m = f.metrics(C.CURRENCY_SYMBOL)
            if not m or m[0] is None:
                C.CURRENCY_SYMBOL = "PHP "
        except Exception:
            C.CURRENCY_SYMBOL = "PHP "

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            if self._font_path:
                f = pygame.font.Font(self._font_path, size)
                f.set_bold(bold)
            elif self._sysfont_name:
                f = pygame.font.SysFont(self._sysfont_name, size, bold=bold)
            else:
                f = pygame.font.Font(None, int(size * 1.3))
                f.set_bold(bold)
            self.fonts[key] = f
        return self.fonts[key]

    def _load_pets(self):
        for mood in ("happy", "hungry", "overweight"):
            p = _find("pets", mood, IMAGE_EXTS)
            if p:
                self.pets[mood] = pygame.image.load(p).convert_alpha()
        if not self.pets:
            self.pets["happy"] = FALLBACK["pet"](256)
        for mood in ("happy", "hungry", "overweight"):
            self.pets.setdefault(mood, self.pets.get("happy") or next(iter(self.pets.values())))

    def _load_icons(self):
        for name in ICON_NAMES:
            p = _find("icons", name, IMAGE_EXTS)
            if p:
                try:
                    self.icons_src[name] = pygame.image.load(p).convert_alpha()
                except pygame.error:
                    pass

    def icon(self, name, size):
        key = (name, size)
        if key not in self._icon_cache:
            src = self.icons_src.get(name)
            if src is not None:
                w, h = src.get_size()
                k = size / max(w, h)
                img = pygame.transform.smoothscale(src, (max(1, int(w * k)), max(1, int(h * k))))
                surf = _s(size)
                surf.blit(img, img.get_rect(center=(size // 2, size // 2)))
            else:
                draw = FALLBACK.get(name)
                surf = draw(size) if draw else _icon_paw(size)
            self._icon_cache[key] = surf
        return self._icon_cache[key]

    def pet_image(self, mood, max_w, max_h):
        key = ("pet", mood, max_w, max_h)
        if key not in self._icon_cache:
            src = self.pets[mood]
            w, h = src.get_size()
            k = min(max_w / w, max_h / h)
            self._icon_cache[key] = pygame.transform.smoothscale(src, (int(w * k), int(h * k)))
        return self._icon_cache[key]

    def _load_sounds(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return
        for name in SOUND_NAMES:
            p = _find("sounds", name, (".wav", ".ogg", ".mp3"))
            if p:
                try:
                    self.sounds[name] = pygame.mixer.Sound(p)
                except pygame.error:
                    pass
        music = _find("sounds", "music", (".ogg", ".mp3", ".wav"))
        if music:
            try:
                pygame.mixer.music.load(music)
                pygame.mixer.music.set_volume(self.volume * 0.5)
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def play(self, name):
        if not self.sound_on:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self.volume)
            snd.play()

    def apply_settings(self, settings):
        self.sound_on = settings.sound
        self.volume = settings.volume
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.volume * 0.5 if self.sound_on else 0)
        except pygame.error:
            pass
