import pygame

from .. import config as C
from . import widgets as W

OPEN_ANIM = 0.18


class Scene:
    toast_x = 420

    def __init__(self, app):
        self.app = app
        self.overlays = []
        self.toasts = W.Toasts(self.toast_x)

    @property
    def assets(self):
        return self.app.assets

    @property
    def planner(self):
        return self.app.planner

    def open(self, overlay):
        self.overlays.append(overlay)
        return overlay

    def close_overlay(self, overlay):
        if overlay in self.overlays:
            self.overlays.remove(overlay)
            overlay.on_close()

    def top_overlay(self):
        return self.overlays[-1] if self.overlays else None

    def has_overlay(self, cls):
        return any(isinstance(o, cls) for o in self.overlays)

    def handle_overlays(self, event):
        if self.overlays:
            self.overlays[-1].handle(event)
            return True
        return False

    def update_overlays(self, dt):
        for o in list(self.overlays):
            o.anim = min(1.0, o.anim + dt / OPEN_ANIM)
            o.update(dt)

    def draw_overlays(self, surf):
        for i, o in enumerate(self.overlays):
            first = i == 0
            if o.anim >= 1:
                o.draw(surf, dim=first)
                continue
            t = 1 - (1 - o.anim) ** 3
            if first:
                W.dim(surf, 110 * t)
            layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            o.draw(layer, dim=False)
            layer.set_alpha(int(255 * t))
            surf.blit(layer, (0, int(22 * (1 - t))))

    def toast(self, msg, level="info"):
        self.toasts.add(msg, level)

    def report(self, ok, msg, sound_ok="success"):
        self.toast(msg, "good" if ok else "bad")
        self.assets.play(sound_ok if ok else "warn")

    def on_class_events(self, events):
        from .classes import ClassAlertOverlay
        missed = []
        for kind, entry, info in events:
            if kind == "reminder":
                where = f" · {entry.room}" if entry.room else ""
                self.toast(f"{entry.name} starts in {info} min{where}", "info")
                self.assets.play("notify")
            elif kind == "start":
                if not any(isinstance(o, ClassAlertOverlay) and o.entry.id == entry.id for o in self.overlays):
                    self.open(ClassAlertOverlay(self, entry))
                self.app.attention(f"Class started: {entry.name}")
                self.assets.play("notify")
            elif kind == "missed":
                missed.append(entry.name)
        if missed:
            if len(missed) == 1:
                self.toast(f"{missed[0]} ended without a check-in. Streak reset.", "warn")
            else:
                self.toast(f"{len(missed)} classes were missed. Streak reset.", "warn")

    def on_coins_earned(self, amount):
        pass

    def check_in(self, entry):
        from datetime import datetime
        ok, msg, coins = self.planner.check_in(entry.id, datetime.now())
        self.report(ok, msg, "success")
        if ok:
            self.on_coins_earned(coins)
            self.app.attention(None)
        return ok

    def handle(self, event):
        self.handle_overlays(event)

    def update(self, dt):
        self.update_overlays(dt)
        self.toasts.update(dt)

    def draw(self, surf):
        self.draw_overlays(surf)


class Overlay:
    closable = True
    icon = None

    def __init__(self, scene, w, h, title=""):
        self.scene = scene
        self.app = scene.app
        self.assets = scene.app.assets
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
        self.title = title
        self.buttons = []
        self.anim = 0.0
        self.close_btn = Button_close(self) if self.closable else None

    def btn(self, *a, **kw):
        b = W.Button(*a, **kw)
        self.buttons.append(b)
        return b

    def close(self):
        self.scene.close_overlay(self)

    def on_close(self):
        pass

    @property
    def body(self):
        return pygame.Rect(self.rect.x + 24, self.rect.y + 76, self.rect.w - 48, self.rect.h - 100)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.closable:
            self.close()
            return
        if self.close_btn and self.close_btn.handle(event, self.assets):
            return
        for b in list(self.buttons):
            if b.handle(event, self.assets):
                return
        self.on_event(event)

    def on_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf, dim=True):
        if dim:
            W.dim(surf)
        W.panel(surf, self.rect, radius=22)
        if self.title:
            x = self.rect.x + 26
            if self.icon:
                tile = pygame.Rect(x, self.rect.y + 16, 42, 42)
                pygame.draw.rect(surf, (255, 236, 222), tile, border_radius=12)
                ic = self.assets.icon(self.icon, 30)
                surf.blit(ic, ic.get_rect(center=tile.center))
                x += 54
            W.text(surf, self.title, self.assets.font(28, bold=True), C.C_TEXT, (x, self.rect.y + 37), "midleft")
            pygame.draw.line(surf, C.C_PANEL_EDGE, (self.rect.x + 20, self.rect.y + 70),
                             (self.rect.right - 20, self.rect.y + 70), 2)
        self.draw_body(surf)
        for b in self.buttons:
            b.draw(surf, self.assets)
        if self.close_btn:
            self.close_btn.draw(surf, self.assets)
        self.draw_after(surf)

    def draw_body(self, surf):
        pass

    def draw_after(self, surf):
        pass


def Button_close(overlay):
    r = pygame.Rect(0, 0, 40, 40)
    r.topright = (overlay.rect.right - 16, overlay.rect.y + 17)
    return W.Button(r, icon="close", on_click=overlay.close, style="ghost", icon_size=26)
