import math
import random
from datetime import datetime

import pygame

from .. import config as C
from ..game_state import money, daily_goal
from ..planner import fmt_clock, fmt_duration, WEEKDAYS
from ..schedule import fmt_time
from . import widgets as W
from .classes import ClassesOverlay, coin_pill
from .overlays import (FeedOverlay, ShopOverlay, InventoryOverlay, ScheduleOverlay,
                       NotificationsOverlay, SummaryOverlay, RecoveryOverlay, TutorialOverlay,
                       PauseOverlay, AwayOverlay, STATUS_STYLE)
from .scene import Scene

ROOM = pygame.Rect(0, 64, 830, 556)
SIDE = pygame.Rect(846, 80, 418, 532)
CLASS_CARD = pygame.Rect(846, 628, 418, 84)
DOCK_Y = 628

SKY = [(0, (28, 32, 70)), (5 * 60, (40, 46, 92)), (6 * 60, (255, 196, 170)), (8 * 60, (176, 216, 244)), (16 * 60, (168, 210, 242)),
       (18 * 60 + 30, (250, 168, 120)), (19 * 60 + 30, (110, 96, 150)), (22 * 60, (40, 46, 92)),
       (24 * 60, (28, 32, 70))]


def sky_color(minute):
    for (m0, c0), (m1, c1) in zip(SKY, SKY[1:]):
        if m0 <= minute <= m1:
            return W.lerp_color(c0, c1, (minute - m0) / (m1 - m0))
    return SKY[-1][1] if minute > SKY[-1][0] else SKY[0][1]


class Particle:
    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.vx = random.uniform(-30, 30)
        self.vy = random.uniform(-90, -60)
        self.life = 1.4

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt


class GameScene(Scene):
    def __init__(self, app, state, new_game=False):
        super().__init__(app)
        self.state = state
        self.particles = []
        self.t = 0.0
        self.last_fed_real = -99.0
        self.pet_rect = pygame.Rect(0, 0, 1, 1)
        self.buttons = []
        p = state.pet
        self.disp = {"hp": p.hp, "hunger": p.hunger, "happiness": p.happiness}
        self.now = datetime.now()
        self.class_btn = None
        self._class_sig = None
        self._autosave = 0.0
        self._build_buttons()
        if new_game and app.settings.show_tutorial:
            self.open(TutorialOverlay(self))
        if state.away_report:
            self.open(AwayOverlay(self, state.away_report))
            state.away_report = None

    def _build_buttons(self):
        b = []
        self.settings_btn = W.Button((1216, 12, 48, 42), icon="settings", style="ghost",
                                     on_click=lambda: self.open(PauseOverlay(self)), icon_size=30,
                                     tooltip="Menu & settings (Esc)")
        b.append(self.settings_btn)
        actions = [("Feed", "feed", self.open_feed, "F"), ("Shop", "shop", self.open_shop, "S"),
                   ("Inventory", "inventory", lambda: self.open(InventoryOverlay(self)), "I"),
                   ("Meals", "schedule", lambda: self.open(ScheduleOverlay(self)), "C"),
                   ("Classes", "class", self.open_classes, "K"),
                   ("Pet", "pet", self.do_pet, "P"), ("Play", "play", self.do_play, "G"),
                   ("Alerts", "bell", lambda: self.open(NotificationsOverlay(self)), "N")]
        names = {"Meals": "Meal schedule", "Classes": "Class schedule", "Alerts": "Notifications"}
        w, gap = 96, 6
        x = ROOM.centerx - (len(actions) * w + (len(actions) - 1) * gap) // 2
        for label, icon, fn, key in actions:
            btn = W.Button((x, DOCK_Y, w, 80), label, icon=icon, on_click=fn, font_size=17, style="dock",
                           tooltip=f"{names.get(label, label)}  ({key})", hotkey=key)
            btn.show_hotkey = True
            if label == "Alerts":
                self.alerts_btn = btn
            if label == "Classes":
                self.classes_btn = btn
            b.append(btn)
            x += w + gap
        self.buttons = b

    def _build_class_button(self):
        self.class_btn = None
        p, now = self.planner, self.now
        r = CLASS_CARD
        open_now = p.open_sessions(now)
        if open_now:
            c = open_now[0]
            self.class_btn = W.Button((r.right - 168, r.y + 20, 152, 44), f"Check in +{p.reward_for(c)}",
                                      on_click=lambda e=c: self.check_in(e), style="good", font_size=16)
        elif not p.classes:
            self.class_btn = W.Button((r.right - 150, r.y + 20, 134, 44), "Add classes",
                                      on_click=self.open_classes, style="primary", font_size=16)
        else:
            self.class_btn = W.Button((r.right - 120, r.y + 20, 104, 44), "Schedule",
                                      on_click=self.open_classes, font_size=16)

    def open_feed(self, preselect=None):
        self.open(FeedOverlay(self, preselect))

    def open_shop(self):
        self.open(ShopOverlay(self))

    def open_classes(self):
        self.open(ClassesOverlay(self))

    def do_pet(self):
        ok, msg = self.state.pet_action()
        self.report(ok, msg, "purr")
        for _ in range(5):
            self.particles.append(Particle(self.pet_rect.centerx + random.randint(-60, 60),
                                           self.pet_rect.y + 40, "heart"))

    def do_play(self):
        ok, msg = self.state.play_action()
        self.report(ok, msg, "success")
        if ok:
            for _ in range(8):
                self.particles.append(Particle(self.pet_rect.centerx + random.randint(-90, 90),
                                               self.pet_rect.y + 60, "star"))

    def on_coins_earned(self, amount):
        for _ in range(min(12, 4 + amount // 3)):
            self.particles.append(Particle(self.pet_rect.centerx + random.randint(-120, 120),
                                           self.pet_rect.y + random.randint(20, 140), "coin"))

    def on_fed(self):
        self.last_fed_real = self.t

    def on_new_day(self):
        self.toast(f"Day {self.state.day} begins! +{money(C.DAILY_ALLOWANCE)} allowance", "good")

    HOTKEYS = {pygame.K_f: "Feed", pygame.K_s: "Shop", pygame.K_i: "Inventory", pygame.K_c: "Meals",
               pygame.K_k: "Classes", pygame.K_p: "Pet", pygame.K_g: "Play", pygame.K_n: "Alerts"}

    def handle(self, event):
        if self.handle_overlays(event):
            return
        if self.class_btn and self.class_btn.handle(event, self.assets):
            return
        for b in self.buttons:
            if b.handle(event, self.assets):
                return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.pet_rect.collidepoint(event.pos):
            self.do_pet()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.open(PauseOverlay(self))
            elif event.key in self.HOTKEYS:
                label = self.HOTKEYS[event.key]
                for b in self.buttons:
                    if b.label == label and b.on_click:
                        b.on_click()

    def update(self, dt):
        self.t += dt
        st = self.state
        st.update(dt, menu_open=bool(self.overlays))
        self.update_overlays(dt)

        for n in st.notifier.drain_toasts():
            if self.app.settings.toasts:
                self.toast(n.text, n.level)
            self.assets.play("warn" if n.level in ("warn", "bad") else "notify")

        if st.pet.fainted and not self.has_overlay(RecoveryOverlay):
            self.overlays = [o for o in self.overlays if not o.closable or isinstance(o, PauseOverlay)]
            self.open(RecoveryOverlay(self))
        if st.away_report:
            self.overlays = [o for o in self.overlays if not isinstance(o, AwayOverlay)]
            self.open(AwayOverlay(self, st.away_report))
            st.away_report = None
            self.app.save()
        if st.summary_pending and st.summary and not self.has_overlay(SummaryOverlay) \
                and not self.has_overlay(AwayOverlay):
            st.summary_pending = False
            self.assets.play("success")
            self.open(SummaryOverlay(self))
        self._autosave += dt
        if self._autosave >= C.AUTOSAVE_SECONDS:
            self._autosave = 0
            self.app.save()

        self.toasts.update(dt)
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        p = st.pet
        for k, v in (("hp", p.hp), ("hunger", p.hunger), ("happiness", p.happiness)):
            self.disp[k] = W.approach(self.disp[k], v, dt)
        self.alerts_btn.badge = st.notifier.unread()
        self.now = datetime.now()
        pl = self.planner
        n_open = len(pl.open_sessions(self.now))
        self.classes_btn.badge = n_open
        self.classes_btn.badge_color = C.C_GOOD
        self.classes_btn.pulse = (0.5 + 0.5 * math.sin(self.t * 4)) if n_open else 0
        sig = (pl.version, n_open, bool(pl.classes),
               tuple(pl.status(c, self.now.date(), self.now) for c in pl.sessions_on(self.now.date())))
        if sig != self._class_sig:
            self._class_sig = sig
            self._build_class_button()
        if self.class_btn:
            self.class_btn.pulse = (0.5 + 0.5 * math.sin(self.t * 4)) if n_open else 0

    def draw(self, surf):
        surf.fill(C.C_BG)
        self.draw_room(surf)
        self.draw_pet(surf)
        self.draw_topbar(surf)
        self.draw_side(surf)
        pygame.draw.rect(surf, (244, 232, 216), (0, 620, C.SCREEN_W, 100))
        pygame.draw.line(surf, (234, 216, 196), (0, 620), (C.SCREEN_W, 620), 2)
        for b in self.buttons:
            b.draw(surf, self.assets)
        self.draw_class_card(surf)
        self.toasts.draw(surf, self.assets)
        if not self.overlays:
            for b in self.buttons + ([self.class_btn] if self.class_btn else []):
                if b.hover and b.tooltip:
                    W.tooltip(surf, self.assets, b.tooltip, b.rect)
        self.draw_overlays(surf)

    def draw_room(self, surf):
        A, st = self.assets, self.state
        floor_y = ROOM.y + 360
        if A.room is not None:
            img = pygame.transform.smoothscale(A.room, ROOM.size) if A.room.get_size() != ROOM.size else A.room
            A.room = img
            surf.blit(img, ROOM)
        else:
            pygame.draw.rect(surf, C.C_ROOM_WALL, (ROOM.x, ROOM.y, ROOM.w, floor_y - ROOM.y))
            for x in range(ROOM.x + 20, ROOM.right, 60):
                pygame.draw.line(surf, (241, 218, 196), (x, ROOM.y), (x, floor_y), 18)
            pygame.draw.rect(surf, C.C_ROOM_FLOOR, (ROOM.x, floor_y, ROOM.w, ROOM.bottom - floor_y))
            for y in range(floor_y + 30, ROOM.bottom, 40):
                pygame.draw.line(surf, (210, 176, 142), (ROOM.x, y), (ROOM.right, y), 2)
            pygame.draw.rect(surf, (200, 160, 124), (ROOM.x, floor_y - 10, ROOM.w, 12))
            win = pygame.Rect(ROOM.x + 70, ROOM.y + 50, 230, 170)
            sky = sky_color(st.minute)
            pygame.draw.rect(surf, sky, win, border_radius=10)
            day_t = max(0.0, min(1.0, (st.minute - C.DAY_START) / (C.DAY_END - C.DAY_START)))
            sx = win.x + 20 + int((win.w - 40) * day_t)
            sy = win.y + 30 + int(60 * (1 - math.sin(math.pi * min(1, day_t * 1.15))))
            night = st.minute >= 19 * 60 + 30 or st.minute < C.DAY_START
            if night:
                for i, (fx, fy) in enumerate(((.2, .2), (.7, .15), (.45, .4), (.85, .5), (.12, .6))):
                    tw = 1 + int(1.5 * (1 + math.sin(self.t * 3 + i)))
                    pygame.draw.circle(surf, (255, 250, 220), (win.x + int(win.w * fx), win.y + int(win.h * fy)), tw)
            pygame.draw.circle(surf, (250, 248, 220) if night else (255, 220, 110), (sx, sy), 18)
            pygame.draw.rect(surf, (255, 255, 255), win, 10, border_radius=10)
            pygame.draw.line(surf, (255, 255, 255), (win.centerx, win.y), (win.centerx, win.bottom), 6)
            pygame.draw.line(surf, (255, 255, 255), (win.x, win.centery), (win.right, win.centery), 6)
            pygame.draw.rect(surf, (236, 150, 130), (win.x - 18, win.y - 14, 40, win.h + 30), border_radius=8)
            pygame.draw.rect(surf, (236, 150, 130), (win.right - 22, win.y - 14, 40, win.h + 30), border_radius=8)
            fr = pygame.Rect(ROOM.x + 520, ROOM.y + 70, 120, 90)
            pygame.draw.rect(surf, (190, 140, 100), fr, border_radius=6)
            pygame.draw.rect(surf, (250, 236, 210), fr.inflate(-16, -16), border_radius=4)
            surf.blit(A.icon("heart", 40), A.icon("heart", 40).get_rect(center=fr.center))
            pygame.draw.rect(surf, (190, 140, 100), (ROOM.x + 660, ROOM.y + 190, 130, 12), border_radius=4)
            surf.blit(A.icon("kibble", 44), (ROOM.x + 670, ROOM.y + 148))
            surf.blit(A.icon("toy", 40), (ROOM.x + 730, ROOM.y + 154))
            if st.minute > 19 * 60 or st.minute < C.DAY_START:
                k = 1 if st.minute < C.DAY_START - 30 else (
                    min(1, (st.minute - 19 * 60) / 180) if st.minute > 19 * 60 else (C.DAY_START - st.minute) / 30)
                tint = pygame.Surface(ROOM.size, pygame.SRCALPHA)
                tint.fill((30, 30, 80, int(70 * k)))
                surf.blit(tint, ROOM)
        self.draw_decor_back(surf, floor_y)
        rug = pygame.Rect(0, 0, 520, 110)
        rug.center = (ROOM.centerx, ROOM.bottom - 70)
        pygame.draw.ellipse(surf, (236, 164, 140), rug)
        pygame.draw.ellipse(surf, (246, 196, 176), rug.inflate(-40, -26))
        pygame.draw.ellipse(surf, (240, 180, 158), rug.inflate(-120, -60), 2)
        fed_recent = self.t - self.last_fed_real < 6
        bowl = A.icon("feed", 74)
        if not fed_recent:
            bowl = bowl.copy()
            pygame.draw.ellipse(bowl, (232, 120, 96), (74 * .18, 74 * .3, 74 * .64, 74 * .16))
        surf.blit(bowl, (ROOM.right - 170, ROOM.bottom - 120))
        if self.state.inv.has("catbed"):
            bed = A.icon("catbed", 170)
            surf.blit(bed, bed.get_rect(midbottom=(ROOM.x + 112, floor_y + 112)))

    def draw_decor_back(self, surf, floor_y):
        A, inv = self.assets, self.state.inv
        if inv.has("lights"):
            cols = [(240, 110, 110), (240, 196, 72), (110, 170, 230), (120, 200, 130), (220, 130, 220)]
            x0, x1, top = ROOM.x + 10, ROOM.right - 10, ROOM.y + 10
            swags = 4
            seg = (x1 - x0) / swags
            pts = []
            for i in range(swags * 12 + 1):
                x = x0 + (x1 - x0) * i / (swags * 12)
                k = ((x - x0) % seg) / seg
                pts.append((x, top + 34 * math.sin(math.pi * k)))
            pygame.draw.lines(surf, (120, 100, 86), False, pts, 2)
            for i in range(swags * 6):
                x = x0 + (i + .5) * (x1 - x0) / (swags * 6)
                k = ((x - x0) % seg) / seg
                y = top + 34 * math.sin(math.pi * k) + 9
                col = cols[i % len(cols)]
                glow = 0.5 + 0.5 * math.sin(self.t * 2.5 + i * 1.7)
                halo = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*col, int(40 + 60 * glow)), (15, 15), 13)
                surf.blit(halo, (x - 15, y - 15))
                pygame.draw.circle(surf, W.lerp_color(col, (255, 255, 255), .3 * glow), (int(x), int(y)), 6)
        if inv.has("plant"):
            pl = A.icon("plant", 150)
            surf.blit(pl, pl.get_rect(midbottom=(ROOM.right - 52, floor_y + 34)))

    def draw_pet(self, surf):
        A, st, p = self.assets, self.state, self.state.pet
        mood = p.mood
        img = A.pet_image(mood, 380, 300)
        bob = math.sin(self.t * 2.2) * (4 if mood == "happy" else 2)
        r = img.get_rect(midbottom=(ROOM.centerx - 20, ROOM.bottom - 50 + bob))
        sh = pygame.Rect(0, 0, int(img.get_width() * .7), 26)
        sh.center = (r.centerx, ROOM.bottom - 52)
        shadow = pygame.Surface(sh.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (80, 50, 30, 50), shadow.get_rect())
        surf.blit(shadow, sh)
        surf.blit(img, r)
        self.pet_rect = r
        say = None
        if p.fainted:
            say = "..."
        elif st.asleep:
            say = "Zzz..." if int(self.t) % 4 else "Zzz... zz..."
        elif p.hunger >= C.HUNGER_CRITICAL:
            say = "So hungry..."
        elif p.hunger >= C.HUNGER_WARNING:
            say = "Feed me!"
        elif p.weight_status in ("Overweight", "Obese"):
            say = "Too full..."
        elif p.happiness < 25:
            say = "Play with me?"
        elif p.hp < 35:
            say = "I don't feel well"
        elif self.planner.open_sessions(self.now):
            say = "Go to class!"
        if say:
            f = A.font(18, bold=True)
            w = f.size(say)[0] + 30
            b = pygame.Rect(0, 0, w, 42)
            b.midbottom = (r.right - 40, r.y + 10)
            b.clamp_ip(ROOM.inflate(-20, -20))
            pygame.draw.rect(surf, (226, 206, 184), b.move(0, 3), border_radius=20)
            pygame.draw.rect(surf, (255, 255, 255), b, border_radius=20)
            pygame.draw.polygon(surf, (255, 255, 255), [(b.x + 24, b.bottom - 2), (b.x + 44, b.bottom - 2),
                                                        (b.x + 22, b.bottom + 14)])
            pygame.draw.rect(surf, C.C_PANEL_EDGE, b, 2, border_radius=20)
            W.text(surf, say, f, C.C_TEXT, b.center, "center")
        W.chip(surf, p.name, A.font(16, bold=True), (255, 255, 255), C.C_ACCENT,
               (r.centerx, ROOM.bottom - 18), "midbottom")
        for pt in self.particles:
            name = {"heart": "heart", "coin": "studycoin"}.get(pt.kind, "happy")
            ic = A.icon(name, 26).copy()
            ic.set_alpha(int(255 * max(0, min(1, pt.life))))
            surf.blit(ic, (pt.x, pt.y))

    def draw_topbar(self, surf):
        A, st = self.assets, self.state
        pygame.draw.rect(surf, C.C_PANEL, (0, 0, C.SCREEN_W, 64))
        pygame.draw.line(surf, C.C_PANEL_EDGE, (0, 64), (C.SCREEN_W, 64), 2)
        r = W.text(surf, f"Day {st.day}", A.font(24, bold=True), C.C_TEXT, (20, 32), "midleft")
        r = W.chip(surf, daily_goal(st.day)[0], A.font(13, bold=True), (255, 255, 255), C.C_INFO,
                   (r.right + 10, 32), "midleft")
        clock = pygame.Rect(r.right + 14, 12, 150, 40)
        pygame.draw.rect(surf, (250, 240, 228), clock, border_radius=20)
        surf.blit(A.icon("clock", 28), (clock.x + 8, clock.y + 6))
        W.text(surf, fmt_time(st.minute), A.font(21, bold=True), C.C_TEXT, (clock.x + 42, clock.centery), "midleft")
        tx = clock.right + 14
        width = 688 - tx
        nxt = st.schedule.next_meal(st.minute) if not st.day_over else None
        if st.asleep and not nxt:
            wake = (C.DAY_START - st.minute) % (24 * 60)
            s, col = f"{st.pet.name} is sleeping · wakes in {fmt_duration(wake)}", (96, 92, 150)
        elif nxt:
            delta = nxt.time - st.minute
            if nxt.status == "overdue":
                s, col = f"{nxt.name} is overdue!", C.C_BAD
            elif nxt.status == "due":
                s = f"{nxt.name} in {int(delta) + 1} min (feed now)" if delta > 0 else f"{nxt.name} is due now!"
                col = C.C_WARN
            else:
                h, m = divmod(int(delta), 60)
                s = f"{nxt.name} in {h}h {m:02d}m" if h else f"{nxt.name} in {m} min"
                col = C.C_TEXT_DIM
        else:
            s, col = "No more meals today · summary at 10 PM", C.C_TEXT_DIM
        f1 = A.font(14, bold=True)
        W.text(surf, W.fit(s, f1, width), f1, col, (tx, 22), "midleft")
        cs, ccol = self.class_status_line()
        f2 = A.font(13)
        W.text(surf, W.fit(cs, f2, width), f2, ccol, (tx, 43), "midleft")
        now = st.clock
        seg = pygame.Rect(700, 12, 226, 40)
        pygame.draw.rect(surf, (250, 240, 228), seg, border_radius=20)
        W.text(surf, now.strftime("%a, %b ") + str(now.day), A.font(15, bold=True), C.C_TEXT,
               (seg.x + 14, seg.centery), "midleft")
        if st.asleep:
            W.chip(surf, "Asleep", A.font(13, bold=True), (255, 255, 255), (96, 92, 150),
                   (seg.right - 8, seg.centery), "midright", pad=(8, 3))
        else:
            W.chip(surf, "Awake", A.font(13, bold=True), (255, 255, 255), C.C_GOOD,
                   (seg.right - 8, seg.centery), "midright", pad=(8, 3))
        cr = coin_pill(surf, A, self.planner.coins, (1206, 32), "midright", size=18)
        col = C.C_BAD if st.wallet.balance < C.LOW_BUDGET_THRESHOLD else C.C_TEXT
        W.icon_chip(surf, A, "coin", money(st.wallet.balance), A.font(18, bold=True), col, (255, 255, 255),
                    (cr.x - 8, 32), "midright", isz=26, pad=(8, 3), border=C.C_PANEL_EDGE)

    def class_status_line(self):
        p, now = self.planner, self.now
        if not p.classes:
            return "Classes: add your schedule to earn Study Coins", C.C_TEXT_DIM
        nxt = p.next_session(now)
        if not nxt:
            return "Classes: nothing coming up this week", C.C_TEXT_DIM
        c, d, status = nxt
        if status == "open":
            return f"Class now: {c.name} – check in!", C.C_GOOD
        mins = (c.start_dt(d) - now).total_seconds() / 60
        if d == now.date():
            return f"Next class: {c.name} in {fmt_duration(mins)}", (122, 104, 200)
        day = "Tomorrow" if (d - now.date()).days == 1 else WEEKDAYS[d.weekday()]
        return f"Next class: {c.name} · {day} {fmt_clock(c.start)}", C.C_TEXT_DIM

    def draw_class_card(self, surf):
        A, p, now = self.assets, self.planner, self.now
        r = CLASS_CARD
        open_now = p.open_sessions(now)
        border = C.C_GOOD if open_now else C.C_PANEL_EDGE
        W.card(surf, r, (255, 252, 247), border, 16)
        tile = pygame.Rect(r.x + 12, r.y + 12, 60, 60)
        pygame.draw.rect(surf, (238, 236, 248), tile, border_radius=14)
        ic = A.icon("class", 46)
        surf.blit(ic, ic.get_rect(center=tile.center))
        x = tile.right + 12
        maxw = (self.class_btn.rect.x if self.class_btn else r.right) - x - 10
        if open_now:
            c = open_now[0]
            W.text(surf, "Class is on now!", A.font(13, bold=True), C.C_GOOD, (x, r.y + 14))
            f = A.font(18, bold=True)
            W.text(surf, W.fit(c.name, f, maxw), f, C.C_TEXT, (x, r.y + 32))
            sub = f"until {fmt_clock(c.end)}" + (f" · {c.room}" if c.room else "")
            W.text(surf, W.fit(sub, A.font(13), maxw), A.font(13), C.C_TEXT_DIM, (x, r.y + 56))
        elif not p.classes:
            W.text(surf, "Class Schedule", A.font(17, bold=True), C.C_TEXT, (x, r.y + 16))
            W.text_block(surf, "Check in to class to earn Study Coins", A.font(13), C.C_TEXT_DIM, x, r.y + 40,
                         maxw, 1, max_lines=2)
        else:
            nxt = p.next_session(now)
            W.text(surf, "Next class", A.font(13, bold=True), (122, 104, 200), (x, r.y + 14))
            if nxt:
                c, d, _ = nxt
                f = A.font(18, bold=True)
                W.text(surf, W.fit(c.name, f, maxw), f, C.C_TEXT, (x, r.y + 32))
                if d == now.date():
                    when = f"{fmt_clock(c.start)} · in {fmt_duration((c.start_dt(d) - now).total_seconds() / 60)}"
                else:
                    when = f"{'Tomorrow' if (d - now.date()).days == 1 else WEEKDAYS[d.weekday()]} " \
                           f"{fmt_clock(c.start)}"
                W.text(surf, W.fit(when, A.font(13), maxw), A.font(13), C.C_TEXT_DIM, (x, r.y + 56))
            else:
                W.text(surf, "None this week", A.font(18, bold=True), C.C_TEXT, (x, r.y + 32))
        if self.class_btn:
            self.class_btn.draw(surf, A)

    def draw_side(self, surf):
        A, st, p = self.assets, self.state, self.state.pet
        W.panel(surf, SIDE, radius=20)
        x, y, w = SIDE.x + 22, SIDE.y + 18, SIDE.w - 44
        W.text(surf, p.name, A.font(26, bold=True), C.C_TEXT, (x, y))
        mood_lbl = {"happy": ("Content", C.C_GOOD), "hungry": ("Needs care", C.C_WARN),
                    "overweight": ("Overweight", C.C_BAD)}[p.mood]
        if p.fainted:
            mood_lbl = ("Fainted", C.C_BAD)
        W.chip(surf, mood_lbl[0], A.font(14, bold=True), (255, 255, 255), mood_lbl[1], (x + w, y + 4), "topright")
        y += 48

        def meter(icon, label, value, color, right_text):
            nonlocal y
            tile = pygame.Rect(x, y, 34, 34)
            pygame.draw.rect(surf, W.lerp_color(color, (255, 255, 255), .82), tile, border_radius=10)
            surf.blit(A.icon(icon, 26), A.icon(icon, 26).get_rect(center=tile.center))
            W.text(surf, label, A.font(17, bold=True), C.C_TEXT, (x + 44, y + 2))
            W.text(surf, right_text, A.font(16, bold=True), C.C_TEXT_DIM, (x + w, y + 3), "topright")
            W.bar(surf, (x + 44, y + 26, w - 44, 14), value, color, radius=7)
            y += 58

        d = self.disp
        hp_col = C.C_HP if p.hp >= 35 else C.C_BAD
        meter("heart", "HP", d["hp"], hp_col, f"{p.hp:.0f} / 100")
        hcol = C.C_GOOD if p.hunger < 35 else (C.C_HUNGER if p.hunger < C.HUNGER_CRITICAL else C.C_BAD)
        meter("hunger", "Hunger", d["hunger"], hcol, p.hunger_status)
        meter("happy", "Happiness", d["happiness"], C.C_HAPPY, f"{p.happiness:.0f}%")

        tile = pygame.Rect(x, y, 34, 34)
        pygame.draw.rect(surf, W.lerp_color(C.C_WEIGHT, (255, 255, 255), .82), tile, border_radius=10)
        surf.blit(A.icon("weight", 26), A.icon("weight", 26).get_rect(center=tile.center))
        W.text(surf, "Weight", A.font(17, bold=True), C.C_TEXT, (x + 44, y + 2))
        ws = p.weight_status
        wcol = C.C_GOOD if ws == "Healthy" else (C.C_WARN if ws in ("Underweight", "Overweight") else C.C_BAD)
        W.text(surf, f"{p.weight:.2f} kg · {ws}", A.font(16, bold=True), wcol, (x + w, y + 3), "topright")
        g = pygame.Rect(x + 44, y + 26, w - 44, 14)
        lo, hi = 3.0, 5.6

        def gx(kg):
            return g.x + int(g.w * (max(lo, min(hi, kg)) - lo) / (hi - lo))

        pygame.draw.rect(surf, (236, 226, 214), g, border_radius=7)
        pygame.draw.rect(surf, (186, 226, 190), (gx(C.HEALTHY_MIN), g.y, gx(C.HEALTHY_MAX) - gx(C.HEALTHY_MIN), g.h))
        pygame.draw.rect(surf, (246, 196, 186), (gx(C.OBESE_AT), g.y, g.right - gx(C.OBESE_AT), g.h),
                         border_top_right_radius=7, border_bottom_right_radius=7)
        mx = gx(p.weight)
        pygame.draw.polygon(surf, C.C_TEXT, [(mx - 7, g.y - 8), (mx + 7, g.y - 8), (mx, g.y + 2)])
        pygame.draw.line(surf, C.C_TEXT, (mx, g.y), (mx, g.bottom), 3)
        W.text(surf, f"healthy {C.HEALTHY_MIN:g}-{C.HEALTHY_MAX:g} kg", A.font(12), C.C_TEXT_DIM,
               (gx((C.HEALTHY_MIN + C.HEALTHY_MAX) / 2), g.bottom + 3), "midtop")
        y += 74

        pygame.draw.line(surf, C.C_PANEL_EDGE, (x, y), (x + w, y), 2)
        y += 12
        W.text(surf, "Today's meals", A.font(17, bold=True), C.C_TEXT, (x, y))
        y += 30
        cw = (w - 16) // 3
        for i, m in enumerate(st.schedule.meals):
            r = pygame.Rect(x + i * (cw + 8), y, cw, 58)
            label, col = STATUS_STYLE[m.status]
            pygame.draw.rect(surf, W.lerp_color(col, (255, 255, 255), .9), r, border_radius=12)
            pygame.draw.rect(surf, col, r, 2, border_radius=12)
            W.text(surf, m.name, A.font(14, bold=True), C.C_TEXT, (r.centerx, r.y + 6), "midtop")
            W.text(surf, fmt_time(m.time), A.font(12), C.C_TEXT_DIM, (r.centerx, r.y + 24), "midtop")
            W.text(surf, label, A.font(12, bold=True), col, (r.centerx, r.y + 40), "midtop")
        y += 72

        title, desc, _ = daily_goal(st.day)
        W.text(surf, f"Goal: {title}", A.font(15, bold=True), C.C_INFO, (x, y))
        W.text_block(surf, desc, A.font(14), C.C_TEXT_DIM, x, y + 22, w, 2)
