import pygame

from .. import config as C


def panel(surf, rect, color=C.C_PANEL, radius=18, border=C.C_PANEL_EDGE, shadow=True, width=2):
    rect = pygame.Rect(rect)
    if shadow:
        sh = pygame.Surface((rect.w + 16, rect.h + 18), pygame.SRCALPHA)
        pygame.draw.rect(sh, (60, 40, 20, 18), (0, 4, rect.w + 16, rect.h + 14), border_radius=radius + 6)
        pygame.draw.rect(sh, (60, 40, 20, 30), (6, 8, rect.w + 4, rect.h + 4), border_radius=radius + 2)
        surf.blit(sh, (rect.x - 8, rect.y - 4))
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)
    return rect


def card(surf, rect, color=(255, 255, 255), border=C.C_PANEL_EDGE, radius=14, width=2, lift=True):
    rect = pygame.Rect(rect)
    if lift:
        pygame.draw.rect(surf, lerp_color(border or C.C_PANEL_EDGE, C.C_BG, .35), rect.move(0, 3),
                         border_radius=radius)
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)
    return rect


def text(surf, s, font, color=C.C_TEXT, pos=(0, 0), anchor="topleft"):
    img = font.render(str(s), True, color)
    r = img.get_rect()
    setattr(r, anchor, pos)
    surf.blit(img, r)
    return r


def fit(s, font, width):
    s = str(s)
    if font.size(s)[0] <= width:
        return s
    while len(s) > 1 and font.size(s + "...")[0] > width:
        s = s[:-1]
    return s.rstrip() + "..."


def wrap(s, font, width):
    lines = []
    for para in str(s).split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        lines.append(line)
    return lines


def text_block(surf, s, font, color, x, y, width, line_gap=4, max_lines=None):
    lines = wrap(s, font, width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(lines[-1] + " ...", font, width)
    for ln in lines:
        text(surf, ln, font, color, (x, y))
        y += font.get_height() + line_gap
    return y


def bar(surf, rect, value, color, bg=(236, 226, 214), radius=8, ghost=None, ghost_color=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    v = max(0, min(100, value))
    if v > 0:
        fill = rect.copy()
        fill.w = max(min(rect.w, radius * 2), int(rect.w * v / 100))
        pygame.draw.rect(surf, color, fill, border_radius=radius)
        if fill.h >= 8 and fill.w > radius * 2:
            gl = pygame.Rect(fill.x + radius // 2, fill.y + 2, fill.w - radius, max(2, fill.h // 3))
            pygame.draw.rect(surf, lerp_color(color, (255, 255, 255), .38), gl, border_radius=gl.h // 2)
    if ghost is not None:
        g = max(0, min(100, ghost))
        x = rect.x + int(rect.w * g / 100)
        pygame.draw.line(surf, ghost_color or C.C_TEXT, (x, rect.y - 3), (x, rect.bottom + 2), 3)


def chip(surf, s, font, fg, bg, pos, anchor="topleft", pad=(10, 4)):
    img = font.render(s, True, fg)
    r = pygame.Rect(0, 0, img.get_width() + pad[0] * 2, img.get_height() + pad[1] * 2)
    setattr(r, anchor, pos)
    pygame.draw.rect(surf, bg, r, border_radius=r.h // 2)
    surf.blit(img, img.get_rect(center=r.center))
    return r


def icon_chip(surf, assets, icon, s, font, fg, bg, pos, anchor="topleft", isz=None, pad=(10, 4), border=None):
    img = font.render(s, True, fg)
    isz = isz or img.get_height()
    r = pygame.Rect(0, 0, img.get_width() + isz + 6 + pad[0] * 2, max(img.get_height(), isz) + pad[1] * 2)
    setattr(r, anchor, pos)
    pygame.draw.rect(surf, bg, r, border_radius=r.h // 2)
    if border:
        pygame.draw.rect(surf, border, r, 2, border_radius=r.h // 2)
    ic = assets.icon(icon, isz)
    surf.blit(ic, ic.get_rect(midleft=(r.x + pad[0], r.centery)))
    surf.blit(img, img.get_rect(midleft=(r.x + pad[0] + isz + 6, r.centery)))
    return r


def level_color(level):
    return {"info": C.C_INFO, "good": C.C_GOOD, "warn": C.C_WARN, "bad": C.C_BAD}.get(level, C.C_INFO)


def dim(surf, alpha=110):
    sh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    sh.fill((40, 28, 20, int(alpha)))
    surf.blit(sh, (0, 0))


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def approach(cur, target, dt, speed=6.0):
    k = min(1.0, dt * speed)
    return cur + (target - cur) * k


def tooltip(surf, assets, s, anchor_rect):
    f = assets.font(14, bold=True)
    w, h = f.size(s)[0] + 20, 30
    r = pygame.Rect(0, 0, w, h)
    r.midbottom = (anchor_rect.centerx, anchor_rect.y - 8)
    r.clamp_ip(surf.get_rect().inflate(-8, -8))
    pygame.draw.rect(surf, (70, 54, 46), r, border_radius=8)
    pygame.draw.polygon(surf, (70, 54, 46), [(r.centerx - 6, r.bottom), (r.centerx + 6, r.bottom),
                                             (r.centerx, r.bottom + 6)])
    text(surf, s, f, (255, 255, 255), r.center, "center")


class Button:
    STYLES = {
        "primary": (C.C_ACCENT, (240, 150, 112), (255, 255, 255)),
        "secondary": ((255, 255, 255), (255, 247, 238), C.C_TEXT),
        "good": (C.C_GOOD, (118, 190, 134), (255, 255, 255)),
        "ghost": ((250, 243, 232), (243, 232, 218), C.C_TEXT),
        "selected": ((255, 226, 206), (252, 214, 190), C.C_ACCENT_DARK),
        "danger": ((255, 255, 255), (253, 236, 234), C.C_BAD),
        "coin": ((122, 104, 200), (138, 120, 214), (255, 255, 255)),
        "dock": ((255, 255, 255), (255, 246, 236), C.C_TEXT),
    }

    def __init__(self, rect, label="", on_click=None, icon=None, style="secondary",
                 font_size=18, enabled=True, tooltip=None, icon_size=None, hotkey=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.icon = icon
        self.style = style
        self.font_size = font_size
        self.enabled = enabled
        self.tooltip = tooltip
        self.icon_size = icon_size
        self.hotkey = hotkey
        self.show_hotkey = False
        self.badge = 0
        self.badge_color = C.C_BAD
        self.hover = False
        self._pressed = False
        self.visible = True
        self.pulse = 0.0

    def handle(self, event, assets=None):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self._pressed
            self._pressed = False
            if was and self.rect.collidepoint(event.pos):
                if self.enabled and self.on_click:
                    if assets:
                        assets.play("click")
                    self.on_click()
                return True
        return False

    def draw(self, surf, assets):
        if not self.visible:
            return
        base, hov, fg = self.STYLES.get(self.style, self.STYLES["secondary"])
        live = self.hover and self.enabled
        col = hov if live else base
        if not self.enabled and self.style not in ("secondary", "ghost", "dock"):
            col = lerp_color(base, (236, 228, 220), .6)
        lift = -2 if (live and not self._pressed) else (2 if self._pressed else 0)
        r = self.rect.move(0, lift)
        rad = min(14, r.h // 2)
        if self.pulse > 0:
            glow = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C.C_WARN, int(90 * self.pulse)), glow.get_rect(), border_radius=rad + 8)
            surf.blit(glow, (r.x - 8, r.y - 8))
        if self.style != "ghost":
            depth = 4 if not self._pressed else 1
            edge = lerp_color(col, (60, 40, 30), .22) if self.style not in ("secondary", "dock", "danger") \
                else lerp_color(C.C_PANEL_EDGE, (60, 40, 30), .08)
            pygame.draw.rect(surf, edge, self.rect.move(0, depth), border_radius=rad)
        pygame.draw.rect(surf, col, r, border_radius=rad)
        if self.style in ("secondary", "ghost", "selected", "danger", "dock"):
            border = {"selected": C.C_ACCENT, "danger": (238, 170, 166)}.get(
                self.style, C.C_ACCENT if (live and self.style == "dock") else C.C_PANEL_EDGE)
            pygame.draw.rect(surf, border, r, 2, border_radius=rad)
        elif r.h >= 30:
            hl = pygame.Rect(r.x + rad // 2, r.y + 3, r.w - rad, max(3, r.h // 4))
            pygame.draw.rect(surf, lerp_color(col, (255, 255, 255), .22), hl, border_radius=hl.h // 2)
        if not self.enabled:
            fg = (180, 168, 156) if self.style in ("secondary", "ghost", "dock", "danger") else (255, 250, 245)
        font = assets.font(self.font_size, bold=True)
        if self.icon and self.label and r.h >= 64:
            isz = self.icon_size or int(r.h * .5)
            ic = assets.icon(self.icon, isz)
            if not self.enabled:
                ic = ic.copy(); ic.set_alpha(110)
            surf.blit(ic, ic.get_rect(midtop=(r.centerx, r.y + 7)))
            text(surf, self.label, assets.font(max(12, self.font_size - 3), bold=True), fg,
                 (r.centerx, r.bottom - 7), "midbottom")
        elif self.icon and self.label:
            isz = self.icon_size or int(r.h * .62)
            ic = assets.icon(self.icon, isz)
            if not self.enabled:
                ic = ic.copy(); ic.set_alpha(130)
            lw = font.size(self.label)[0]
            x = r.centerx - (isz + 6 + lw) // 2
            surf.blit(ic, ic.get_rect(midleft=(x, r.centery)))
            text(surf, self.label, font, fg, (x + isz + 6, r.centery), "midleft")
        elif self.icon:
            isz = self.icon_size or int(min(r.w, r.h) * .66)
            ic = assets.icon(self.icon, isz)
            surf.blit(ic, ic.get_rect(center=r.center))
        else:
            text(surf, self.label, font, fg, r.center, "center")
        if self.show_hotkey and self.hotkey:
            kf = assets.font(11, bold=True)
            kr = pygame.Rect(r.x + 6, r.y + 6, 18, 18)
            pygame.draw.rect(surf, (246, 236, 224), kr, border_radius=5)
            pygame.draw.rect(surf, C.C_PANEL_EDGE, kr, 1, border_radius=5)
            text(surf, self.hotkey, kf, C.C_TEXT_DIM, kr.center, "center")
        if self.badge:
            b = str(self.badge) if not isinstance(self.badge, int) or self.badge < 100 else "99+"
            bf = assets.font(13, bold=True)
            w = max(22, bf.size(b)[0] + 10)
            br = pygame.Rect(0, 0, w, 22)
            br.center = (r.right - 6, r.y + 6)
            pygame.draw.rect(surf, (255, 255, 255), br.inflate(4, 4), border_radius=13)
            pygame.draw.rect(surf, self.badge_color, br, border_radius=11)
            text(surf, b, bf, (255, 255, 255), br.center, "center")


class TextInput:
    def __init__(self, rect, value="", placeholder="", max_len=28):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.placeholder = placeholder
        self.max_len = max_len
        self.focused = False
        self.t = 0.0

    def focus(self, on=True):
        self.focused = on
        self.t = 0
        try:
            if on:
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(self.rect)
        except (AttributeError, pygame.error):
            pass

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            inside = self.rect.collidepoint(event.pos)
            self.focus(inside)
            return inside
        if not self.focused:
            return False
        if event.type == pygame.TEXTINPUT:
            add = "".join(ch for ch in event.text if ch.isprintable())
            self.value = (self.value + add)[:self.max_len]
            self.t = 0
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.value = self.value.rstrip()
                    self.value = self.value[:self.value.rfind(" ") + 1] if " " in self.value else ""
                else:
                    self.value = self.value[:-1]
                self.t = 0
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.focused = False
                return False
            return True
        return False

    def update(self, dt):
        self.t += dt

    def draw(self, surf, assets):
        r = self.rect
        pygame.draw.rect(surf, (255, 255, 255), r, border_radius=12)
        pygame.draw.rect(surf, C.C_ACCENT if self.focused else C.C_PANEL_EDGE, r, 2, border_radius=12)
        f = assets.font(18)
        if self.value:
            shown = self.value
            while f.size(shown)[0] > r.w - 30 and len(shown) > 1:
                shown = shown[1:]
            tr = text(surf, shown, f, C.C_TEXT, (r.x + 14, r.centery), "midleft")
            cx = tr.right + 2
        else:
            text(surf, self.placeholder, f, (190, 176, 164), (r.x + 14, r.centery), "midleft")
            cx = r.x + 14
        if self.focused and int(self.t * 2) % 2 == 0:
            pygame.draw.line(surf, C.C_ACCENT_DARK, (cx, r.y + 10), (cx, r.bottom - 10), 2)


class Toasts:
    ICON = {"info": "i", "warn": "!", "bad": "!"}

    def __init__(self, center_x=420):
        self.items = []
        self.center_x = center_x

    def add(self, s, level="info"):
        self.items.append([s, level, C.TOAST_SECONDS, 0.0])
        self.items = self.items[-4:]

    def update(self, dt):
        for t in self.items:
            t[2] -= dt
            t[3] += dt
        self.items = [t for t in self.items if t[2] > 0]

    def draw(self, surf, assets, top=78):
        font = assets.font(17, bold=True)
        sym_font = assets.font(15, bold=True)
        y = top
        for s, level, left, age in self.items:
            s = fit(s, font, 700)
            w = font.size(s)[0] + 70
            slide = max(0.0, 1 - age / .22)
            r = pygame.Rect(0, int(y - 18 * slide * slide), w, 44)
            r.centerx = self.center_x
            alpha = int(255 * min(1, left / .4, age / .15 if age < .15 else 1))
            col = level_color(level)
            box = pygame.Surface((r.w, r.h + 4), pygame.SRCALPHA)
            pygame.draw.rect(box, (60, 40, 20, alpha // 6), (0, 4, r.w, r.h), border_radius=22)
            pygame.draw.rect(box, (*C.C_PANEL, alpha), (0, 0, r.w, r.h), border_radius=22)
            pygame.draw.rect(box, (*col, alpha), (0, 0, r.w, r.h), 2, border_radius=22)
            pygame.draw.circle(box, (*col, alpha), (24, 22), 12)
            if level == "good":
                pygame.draw.lines(box, (255, 255, 255, alpha), False, [(18, 22), (22, 27), (30, 17)], 3)
            else:
                sym = sym_font.render(self.ICON.get(level, "i"), True, (255, 255, 255))
                sym.set_alpha(alpha)
                box.blit(sym, sym.get_rect(center=(24, 22)))
            img = font.render(s, True, C.C_TEXT)
            img.set_alpha(alpha)
            box.blit(img, img.get_rect(midleft=(46, 22)))
            surf.blit(box, r)
            y += 52
