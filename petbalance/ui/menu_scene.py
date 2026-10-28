import math
import random
from datetime import datetime

import pygame

from .. import config as C
from ..game_state import GameState
from ..planner import fmt_clock, fmt_duration, WEEKDAYS
from . import widgets as W
from .classes import ClassesOverlay, coin_pill
from .overlays import SettingsOverlay, ConfirmOverlay
from .scene import Scene


class Floater:
    def __init__(self, first=False):
        self.icon = random.choice(["heart", "pet", "studycoin", "heart", "pet"])
        self.x = random.uniform(20, C.SCREEN_W - 20)
        self.y = random.uniform(0, C.SCREEN_H) if first else C.SCREEN_H + 30
        self.size = random.choice([18, 22, 26])
        self.speed = random.uniform(14, 30)
        self.phase = random.uniform(0, 6.28)
        self.alpha = random.randint(40, 90)

    def update(self, dt, t):
        self.y -= self.speed * dt
        return self.y > -40

    def draw(self, surf, assets, t):
        ic = assets.icon(self.icon, self.size).copy()
        ic.set_alpha(self.alpha)
        surf.blit(ic, (self.x + math.sin(t * .8 + self.phase) * 14, self.y))


class MenuScene(Scene):
    toast_x = C.SCREEN_W // 2

    def __init__(self, app):
        super().__init__(app)
        self.t = 0
        self.floaters = [Floater(first=True) for _ in range(14)]
        x, y, h, gap = 150, 316, 56, 68
        has_save = GameState.has_save()
        self.buttons = [
            W.Button((x, y, 320, h), "Start Game", on_click=self.start, style="primary", font_size=22),
            W.Button((x, y + gap, 320, h), "Continue", on_click=self.app.continue_game,
                     enabled=has_save, font_size=22),
            W.Button((x, y + gap * 2, 320, h), "Class Schedule", icon="class", icon_size=32,
                     on_click=lambda: self.open(ClassesOverlay(self)), font_size=21),
            W.Button((x, y + gap * 3, 155, h), "Settings", on_click=lambda: self.open(SettingsOverlay(self)),
                     font_size=19),
            W.Button((x + 165, y + gap * 3, 155, h), "Exit", on_click=self.app.quit, style="ghost", font_size=19),
        ]

    def start(self):
        if GameState.has_save():
            self.open(ConfirmOverlay(self, "Start a new game?",
                                     "This replaces your saved pet progress. Your classes and "
                                     f"{C.COIN_NAME} are kept. Use Continue to keep playing your current game.",
                                     self.app.new_game, yes="New game"))
        else:
            self.app.new_game()

    def handle(self, event):
        if self.handle_overlays(event):
            return
        for b in self.buttons:
            if b.handle(event, self.assets):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            (self.app.continue_game if GameState.has_save() else self.start)()

    def update(self, dt):
        self.t += dt
        self.floaters = [f for f in self.floaters if f.update(dt, self.t)]
        while len(self.floaters) < 14:
            self.floaters.append(Floater())
        self.update_overlays(dt)
        self.toasts.update(dt)
        n_open = len(self.planner.open_sessions(datetime.now()))
        self.buttons[2].badge = n_open
        self.buttons[2].badge_color = C.C_GOOD
        self.buttons[2].pulse = (0.5 + 0.5 * math.sin(self.t * 4)) if n_open else 0

    def draw(self, surf):
        A = self.assets
        surf.fill(C.C_ROOM_WALL)
        for x in range(20, C.SCREEN_W, 60):
            pygame.draw.line(surf, (241, 218, 196), (x, 0), (x, 520), 18)
        pygame.draw.rect(surf, C.C_ROOM_FLOOR, (0, 520, C.SCREEN_W, 200))
        pygame.draw.rect(surf, (200, 160, 124), (0, 510, C.SCREEN_W, 12))
        for f in self.floaters:
            f.draw(surf, A, self.t)
        rug = pygame.Rect(0, 0, 640, 120)
        rug.center = (880, 610)
        pygame.draw.ellipse(surf, (236, 164, 140), rug)
        pygame.draw.ellipse(surf, (246, 196, 176), rug.inflate(-44, -28))

        img = A.pet_image("happy", 420, 460)
        bob = math.sin(self.t * 2) * 5
        shadow = pygame.Surface((300, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (80, 50, 30, 45), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(center=(880, 632)))
        surf.blit(img, img.get_rect(midbottom=(880, 640 + bob)))

        title_f = A.font(84, bold=True)
        W.text(surf, "PetBalance", title_f, (236, 196, 170), (149, 106))
        W.text(surf, "PetBalance", title_f, C.C_ACCENT_DARK, (146, 100))
        W.text(surf, "Care for your pet · Manage your budget · Go to class", A.font(20), C.C_TEXT, (152, 202))
        self.draw_class_strip(surf)
        for b in self.buttons:
            b.draw(surf, A)
        W.text(surf, "Enter: continue   ·   Mochi and your classes run on your computer's real clock", A.font(14), C.C_TEXT_DIM,
               (152, 690))
        self.toasts.draw(surf, A, top=20)
        self.draw_overlays(surf)

    def draw_class_strip(self, surf):
        A, p = self.assets, self.planner
        now = datetime.now()
        r = coin_pill(surf, A, p.coins, (152, 248), "topleft", size=17)
        nxt = p.next_session(now)
        if not p.classes:
            s, col = "Add your classes to earn Study Coins", C.C_TEXT_DIM
        elif not nxt:
            s, col = "No classes coming up", C.C_TEXT_DIM
        else:
            c, d, st = nxt
            if st == "open":
                s, col = f"{c.name} is on now – check in!", C.C_GOOD
            elif d == now.date():
                s, col = f"Next: {c.name} in {fmt_duration((c.start_dt(d) - now).total_seconds() / 60)}", C.C_TEXT
            else:
                day = "tomorrow" if (d - now.date()).days == 1 else WEEKDAYS[d.weekday()]
                s, col = f"Next: {c.name} {day} {fmt_clock(c.start)}", C.C_TEXT
        f = A.font(16, bold=True)
        W.icon_chip(surf, A, "class", W.fit(s, f, 360), f, col, (255, 255, 255), (r.right + 10, r.centery),
                    "midleft", isz=24, pad=(10, 3), border=C.C_PANEL_EDGE)
