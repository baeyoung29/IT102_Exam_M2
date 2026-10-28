from datetime import datetime, timedelta

import pygame

from .. import config as C
from ..planner import (WEEKDAYS, WEEKDAYS_LONG, days_label, fmt_clock, fmt_duration, validate)
from . import widgets as W
from .scene import Overlay

STATUS = {
    "upcoming": ("Upcoming", C.C_INFO),
    "open": ("Check-in open", C.C_WARN),
    "attended": ("Attended", C.C_GOOD),
    "missed": ("Missed", C.C_BAD),
    "untracked": ("Added later", C.C_TEXT_DIM),
}
COIN_PURPLE = (122, 104, 200)


def _lanes(classes):
    group, group_end = [], -1
    for c in classes + [None]:
        if c is None or (group and c.start >= group_end):
            ends = []
            placed = []
            for g in group:
                for i, e in enumerate(ends):
                    if g.start >= e:
                        ends[i] = g.end
                        placed.append((g, i))
                        break
                else:
                    ends.append(g.end)
                    placed.append((g, len(ends) - 1))
            for g, i in placed:
                yield g, i, len(ends)
            group, group_end = [], -1
        if c is not None:
            group.append(c)
            group_end = max(group_end, c.end)


def coin_pill(surf, assets, amount, pos, anchor="topleft", size=16):
    return W.icon_chip(surf, assets, "studycoin", f"{amount:,}", assets.font(size, bold=True), C.C_TEXT,
                       (255, 255, 255), pos, anchor, isz=size + 8, pad=(8, 3), border=(214, 206, 240))


class ClassesOverlay(Overlay):
    icon = "class"

    def __init__(self, scene):
        super().__init__(scene, 1200, 650, "Class Schedule")
        self.planner = scene.planner
        self.blocks = []
        self.today_cards = []
        self.hover = None
        self.sig = None
        self.now = datetime.now()
        self.rebuild()

    @property
    def left(self):
        return pygame.Rect(self.body.x, self.body.y, 372, self.body.h)

    @property
    def grid(self):
        x = self.body.x + 392
        return pygame.Rect(x, self.body.y, self.body.right - x, self.body.h)

    def hours(self):
        lo, hi = 7, 18
        if self.planner.classes:
            lo = min(lo, min(c.start for c in self.planner.classes) // 60)
            hi = max(hi, -(-max(c.end for c in self.planner.classes) // 60))
        return max(0, lo), min(24, max(hi, lo + 6))

    def signature(self):
        d = self.now.date()
        return (self.planner.version, d,
                tuple(self.planner.status(c, d, self.now) for c in self.planner.sessions_on(d)))

    def rebuild(self):
        self.buttons = []
        self.sig = self.signature()
        p, now, d = self.planner, self.now, self.now.date()
        L = self.left
        self.today_cards = []
        y = L.y + 34
        for c in p.sessions_on(d)[:4]:
            st = p.status(c, d, now)
            r = pygame.Rect(L.x, y, L.w, 84)
            self.today_cards.append((r, c, st))
            if st == "open":
                b = self.btn((r.right - 150, r.y + 40, 138, 36), f"Check in +{p.reward_for(c)}",
                             on_click=lambda e=c: self.check_in(e), style="good", font_size=15)
                b.pulse = 1
            y += 94
        self.btn((L.x, L.bottom - 52, L.w, 52), "Add Class", icon="plus", style="primary",
                 on_click=self.add_class, font_size=19, icon_size=22,
                 enabled=len(p.classes) < C.MAX_CLASSES)

    def add_class(self):
        self.scene.open(ClassEditOverlay(self.scene))

    def edit(self, entry):
        self.scene.open(ClassEditOverlay(self.scene, entry))

    def check_in(self, entry):
        self.scene.check_in(entry)
        self.rebuild()

    def update(self, dt):
        self.now = datetime.now()
        if self.signature() != self.sig:
            self.rebuild()
        mouse = pygame.mouse.get_pos()
        self.hover = None
        for r, c in self.blocks:
            if r.collidepoint(mouse):
                self.hover = c

    def on_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for r, c in self.blocks:
                if r.collidepoint(event.pos):
                    self.assets.play("click")
                    self.edit(c)
                    return
            for r, c, st in self.today_cards:
                if r.collidepoint(event.pos):
                    self.assets.play("click")
                    self.edit(c)
                    return
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_a:
            self.add_class()

    def draw_body(self, surf):
        A, p, now = self.assets, self.planner, self.now
        x = self.rect.right - 72
        r = coin_pill(surf, A, p.coins, (x, self.rect.y + 37), "midright")
        x = r.x - 8
        r = W.icon_chip(surf, A, "streak", f"Streak {p.streak}", A.font(15, bold=True), C.C_TEXT,
                        (255, 240, 228), (x, self.rect.y + 37), "midright", isz=22, pad=(8, 4))
        x = r.x - 14
        W.text(surf, now.strftime("%a, %b ") + str(now.day) + " · " + fmt_clock(now.hour * 60 + now.minute),
               A.font(15, bold=True), C.C_TEXT_DIM, (x, self.rect.y + 37), "midright")
        self.draw_today(surf)
        self.draw_grid(surf)

    def draw_today(self, surf):
        A, p, now = self.assets, self.planner, self.now
        L = self.left
        d = now.date()
        W.text(surf, f"Today · {WEEKDAYS_LONG[d.weekday()]}", A.font(19, bold=True), C.C_TEXT, (L.x, L.y))
        sessions = p.sessions_on(d)
        if not sessions:
            box = pygame.Rect(L.x, L.y + 34, L.w, 110)
            W.card(surf, box, (255, 252, 247))
            W.text(surf, "No classes today", A.font(18, bold=True), C.C_TEXT, (box.centerx, box.y + 30), "midtop")
            W.text(surf, "Enjoy the free day with Mochi!" if p.classes else "Add your classes to start earning",
                   A.font(14), C.C_TEXT_DIM, (box.centerx, box.y + 58), "midtop")
        for r, c, st in self.today_cards:
            label, col = STATUS[st]
            W.card(surf, r, border=col if st == "open" else C.C_PANEL_EDGE)
            pygame.draw.rect(surf, c.rgb, (r.x + 2, r.y + 2, 8, r.h - 4),
                             border_top_left_radius=12, border_bottom_left_radius=12)
            f = A.font(17, bold=True)
            W.text(surf, W.fit(c.name, f, r.w - 150), f, C.C_TEXT, (r.x + 22, r.y + 10))
            W.text(surf, c.time_label(), A.font(14), C.C_TEXT_DIM, (r.x + 22, r.y + 36))
            if c.room:
                W.text(surf, W.fit(c.room, A.font(14), r.w - 190), A.font(14), C.C_TEXT_DIM, (r.x + 22, r.y + 58))
            if st == "attended":
                rec = p.records.get(p.key(c, now.date()))
                W.icon_chip(surf, A, "check", f"+{rec.coins if rec else 0}", A.font(14, bold=True),
                            (255, 255, 255), C.C_GOOD, (r.right - 12, r.y + 12), "topright", isz=18, pad=(6, 3))
            elif st != "open":
                if st == "upcoming":
                    mins = (c.start_dt(now.date()) - now).total_seconds() / 60
                    label = f"in {fmt_duration(mins)}"
                W.chip(surf, label, A.font(13, bold=True), (255, 255, 255), col, (r.right - 12, r.y + 12),
                       "topright", pad=(8, 3))
            else:
                W.chip(surf, "Now", A.font(13, bold=True), (255, 255, 255), C.C_WARN, (r.right - 12, r.y + 10),
                       "topright", pad=(8, 3))
        more = len(sessions) - len(self.today_cards)
        if more > 0:
            W.text(surf, f"+{more} more today (see calendar)", A.font(14), C.C_TEXT_DIM,
                   (L.x, L.y + 34 + 4 * 94 - 6))
        ws = p.week_stats(now.date())
        y = L.bottom - 52 - 74
        box = pygame.Rect(L.x, y, L.w, 62)
        pygame.draw.rect(surf, (252, 245, 236), box, border_radius=14)
        cols = [("This week", f"{ws['attended']} attended"), ("Missed", str(ws["missed"])),
                ("Best streak", str(p.best_streak))]
        cw = box.w // 3
        for i, (k, v) in enumerate(cols):
            cx = box.x + cw * i + cw // 2
            W.text(surf, k, A.font(12), C.C_TEXT_DIM, (cx, box.y + 10), "midtop")
            W.text(surf, v, A.font(16, bold=True), C.C_TEXT, (cx, box.y + 30), "midtop")

    def draw_grid(self, surf):
        A, p, now = self.assets, self.planner, self.now
        G = self.grid
        pygame.draw.rect(surf, (255, 255, 255), G, border_radius=16)
        pygame.draw.rect(surf, C.C_PANEL_EDGE, G, 2, border_radius=16)
        lo, hi = self.hours()
        axis_w, head_h = 58, 40
        cols = pygame.Rect(G.x + axis_w, G.y + head_h, G.w - axis_w - 10, G.h - head_h - 12)
        cw = cols.w / 7
        span = (hi - lo) * 60

        def y_of(minute):
            return cols.y + int(cols.h * (minute - lo * 60) / span)

        today = now.date()
        monday = today - timedelta(days=today.weekday())
        tx = int(cols.x + cw * today.weekday())
        pygame.draw.rect(surf, (255, 244, 234), (tx, G.y + 6, int(cw), G.h - 12), border_radius=10)
        for i in range(7):
            cx = int(cols.x + cw * i + cw / 2)
            d = monday + timedelta(days=i)
            is_today = d == today
            W.text(surf, WEEKDAYS[i], A.font(15, bold=True), C.C_ACCENT_DARK if is_today else C.C_TEXT,
                   (cx, G.y + 8), "midtop")
            W.text(surf, str(d.day), A.font(12), C.C_ACCENT_DARK if is_today else C.C_TEXT_DIM,
                   (cx, G.y + 25), "midtop")
        step = 1 if hi - lo <= 12 else 2
        for h in range(lo, hi + 1):
            y = y_of(h * 60)
            pygame.draw.line(surf, (240, 232, 222), (cols.x, y), (cols.right, y), 1)
            if (h - lo) % step == 0:
                W.text(surf, fmt_clock(h * 60).replace(":00", ""), A.font(12), C.C_TEXT_DIM,
                       (G.x + axis_w - 8, y), "midright")
        for i in range(1, 7):
            x = int(cols.x + cw * i)
            pygame.draw.line(surf, (240, 232, 222), (x, cols.y), (x, cols.bottom), 1)

        self.blocks = []
        for wd in range(7):
            d = monday + timedelta(days=wd)
            day_classes = sorted((c for c in p.classes if wd in c.days), key=lambda c: (c.start, c.end))
            for c, lane, lanes in _lanes(day_classes):
                lw = (cw - 6) / lanes
                r = pygame.Rect(int(cols.x + cw * wd + 3 + lw * lane), y_of(c.start) + 1, int(lw) - (2 if lanes > 1 else 0),
                                max(22, y_of(c.end) - y_of(c.start) - 2))
                self.blocks.append((r, c))
                st = p.status(c, d, now) if d <= today else "upcoming"
                hov = self.hover is c
                base = W.lerp_color(c.rgb, (255, 255, 255), .55 if st in ("missed", "untracked") else .12)
                if hov:
                    base = W.lerp_color(base, (255, 255, 255), .15)
                pygame.draw.rect(surf, base, r, border_radius=8)
                pygame.draw.rect(surf, W.lerp_color(c.rgb, (40, 30, 20), .25), r, 2 if hov else 1, border_radius=8)
                faded = st in ("missed", "untracked")
                fg, fg2 = ((C.C_TEXT, C.C_TEXT_DIM) if faded else ((255, 255, 255), (255, 248, 240)))
                f = A.font(13, bold=True)
                if r.w >= 30:
                    W.text(surf, W.fit(c.name, f, r.w - 10), f, fg, (r.x + 6, r.y + 4))
                if r.h >= 40 and r.w >= 50:
                    W.text(surf, W.fit(fmt_clock(c.start), A.font(11), r.w - 10), A.font(11), fg2,
                           (r.x + 6, r.y + 22))
                if st == "attended" and r.h >= 30:
                    ic = A.icon("check", 18)
                    surf.blit(ic, ic.get_rect(bottomright=(r.right - 4, r.bottom - 4)))
        nm = now.hour * 60 + now.minute
        if lo * 60 <= nm <= hi * 60:
            y = y_of(nm)
            pygame.draw.line(surf, C.C_BAD, (tx, y), (int(tx + cw), y), 2)
            pygame.draw.circle(surf, C.C_BAD, (tx + 2, y), 5)
        if not p.classes:
            msg = pygame.Rect(0, 0, 420, 120)
            msg.center = cols.center
            W.card(surf, msg, (255, 252, 247))
            ic = A.icon("class", 44)
            surf.blit(ic, ic.get_rect(midtop=(msg.centerx, msg.y + 12)))
            W.text(surf, "Your week is empty", A.font(18, bold=True), C.C_TEXT, (msg.centerx, msg.y + 60), "midtop")
            W.text(surf, "Click Add Class to put in your schedule.", A.font(14), C.C_TEXT_DIM,
                   (msg.centerx, msg.y + 86), "midtop")

    def draw_after(self, surf):
        if self.hover:
            c = self.hover
            room = f" · {c.room}" if c.room else ""
            hov_rect = next((r for r, e in self.blocks if e is c and r.collidepoint(pygame.mouse.get_pos())), None)
            if hov_rect:
                W.tooltip(surf, self.assets, f"{c.name} · {c.time_label()}{room}  (click to edit)", hov_rect)


class ClassEditOverlay(Overlay):
    icon = "class"

    def __init__(self, scene, entry=None):
        super().__init__(scene, 760, 610, "Edit Class" if entry else "Add a Class")
        self.planner = scene.planner
        self.entry = entry
        now = datetime.now()
        if entry:
            name, room, days, start, end, color = (entry.name, entry.room, list(entry.days), entry.start,
                                                   entry.end, entry.color)
        else:
            start = min(20 * 60, max(7 * 60, (now.hour + 1) * 60))
            name, room, days, end = "", "", [now.weekday()], start + 90
            color = len(self.planner.classes) % len(C.CLASS_COLORS)
        self.days, self.start, self.end, self.color = days, start, end, color
        fx = self.rect.x + 200
        self.name_in = W.TextInput((fx, self.body.y + 2, 520, 46), name, "e.g. IT102 – Programming", 28)
        self.room_in = W.TextInput((fx, self.body.y + 62, 520, 46), room, "e.g. Room 301 (optional)", 24)
        self.inputs = [self.name_in, self.room_in]
        if not entry:
            self.name_in.focus()
        self.error = ""
        self.confirm_delete = False
        self.time_rows = {}
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        fx = self.rect.x + 200
        y = self.body.y + 128
        for i, dname in enumerate(WEEKDAYS):
            self.btn((fx + i * 75, y, 68, 42), dname, on_click=lambda d=i: self.toggle_day(d),
                     style="selected" if i in self.days else "secondary", font_size=15)
        y += 50
        for label, days in (("Mon–Fri", [0, 1, 2, 3, 4]), ("Mon/Wed/Fri", [0, 2, 4]), ("Tue/Thu", [1, 3])):
            w = 40 + self.assets.font(13, bold=True).size(label)[0]
            self.btn((fx, y, w, 30), label, on_click=lambda d=days: self.set_days(d), style="ghost", font_size=13)
            fx += w + 8
        fx = self.rect.x + 200
        y += 54
        self.time_rows = {}
        for key in ("start", "end"):
            self.time_rows[key] = y
            for j, (lbl, delta) in enumerate((("-1h", -60), ("-5m", -5))):
                self.btn((fx + j * 62, y, 56, 42), lbl, on_click=lambda k=key, dd=delta: self.nudge(k, dd),
                         font_size=15)
            for j, (lbl, delta) in enumerate((("+5m", 5), ("+1h", 60))):
                self.btn((fx + 290 + j * 62, y, 56, 42), lbl, on_click=lambda k=key, dd=delta: self.nudge(k, dd),
                         font_size=15)
            y += 56
        y += 8
        self.color_y = y
        for i, col in enumerate(C.CLASS_COLORS):
            b = self.btn((fx + i * 52, y, 42, 42), "", on_click=lambda n=i: self.set_color(n), style="ghost")
            b.swatch = col
        by = self.rect.bottom - 76
        self.btn((self.rect.right - 230, by, 200, 52), "Save Class" if self.entry else "Add Class",
                 on_click=self.save, style="primary", font_size=19)
        self.btn((self.rect.right - 408, by, 164, 52), "Cancel", on_click=self.close, font_size=18)
        if self.entry:
            self.btn((self.rect.x + 30, by, 190, 52), "Really delete?" if self.confirm_delete else "Delete class",
                     on_click=self.delete, style="danger", font_size=17)

    def toggle_day(self, d):
        if d in self.days:
            self.days.remove(d)
        else:
            self.days.append(d)
        self.error = ""
        self.rebuild()

    def set_days(self, days):
        self.days = list(days)
        self.rebuild()

    def nudge(self, key, delta):
        if key == "start":
            dur = self.end - self.start
            self.start = max(0, min(24 * 60 - 5, self.start + delta))
            self.end = min(24 * 60 - 1, self.start + dur)
        else:
            self.end = max(self.start + 5, min(24 * 60 - 1, self.end + delta))
        self.error = ""

    def set_color(self, n):
        self.color = n

    def save(self):
        name, room = self.name_in.value, self.room_in.value
        err = validate(name, self.days, self.start, self.end)
        if err:
            self.error = err
            self.assets.play("warn")
            return
        if self.entry:
            e, msg = self.planner.update_class(self.entry.id, name, self.days, self.start, self.end, room,
                                               self.color)
        else:
            e, msg = self.planner.add(name, self.days, self.start, self.end, room, self.color)
        if e is None:
            self.error = msg
            self.assets.play("warn")
            return
        self.scene.report(True, msg, "success")
        self.close()

    def delete(self):
        if not self.confirm_delete:
            self.confirm_delete = True
            self.rebuild()
            return
        ok, msg = self.planner.remove(self.entry.id)
        self.scene.report(ok, msg, "click")
        self.close()

    def on_event(self, event):
        for t in self.inputs:
            if t.handle(event):
                return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            if self.name_in.value and not self.room_in.value and event.key == pygame.K_TAB:
                self.room_in.focus()
            elif event.key == pygame.K_TAB:
                self.name_in.focus()
            else:
                self.save()
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            for key, y in self.time_rows.items():
                if y <= my <= y + 42 and self.rect.x + 320 <= mx <= self.rect.x + 490:
                    self.nudge(key, 5 * (1 if event.y > 0 else -1))

    def update(self, dt):
        for t in self.inputs:
            t.update(dt)

    def draw_body(self, surf):
        A = self.assets
        lx = self.rect.x + 30
        f = A.font(17, bold=True)
        W.text(surf, "Class name", f, C.C_TEXT, (lx, self.name_in.rect.centery), "midleft")
        W.text(surf, "Room / section", f, C.C_TEXT, (lx, self.room_in.rect.centery), "midleft")
        for t in self.inputs:
            t.draw(surf, A)
        y = self.body.y + 128
        W.text(surf, "Days", f, C.C_TEXT, (lx, y + 21), "midleft")
        W.text(surf, "Quick pick", A.font(13), C.C_TEXT_DIM, (lx, y + 65), "midleft")
        fx = self.rect.x + 200
        for key, label in (("start", "Starts"), ("end", "Ends")):
            ty = self.time_rows[key]
            W.text(surf, label, f, C.C_TEXT, (lx, ty + 21), "midleft")
            box = pygame.Rect(fx + 128, ty, 154, 42)
            pygame.draw.rect(surf, (255, 255, 255), box, border_radius=12)
            pygame.draw.rect(surf, C.C_PANEL_EDGE, box, 2, border_radius=12)
            W.text(surf, fmt_clock(self.start if key == "start" else self.end), A.font(20, bold=True), C.C_TEXT,
                   box.center, "center")
        dur = self.end - self.start
        reward = C.CLASS_BASE_COINS + (dur // 60) * C.CLASS_COINS_PER_HOUR
        ey = self.time_rows["end"] + 50
        W.text(surf, f"{fmt_duration(dur)} long", A.font(14), C.C_TEXT_DIM, (fx + 420, self.time_rows["start"] + 21),
               "midleft")
        W.icon_chip(surf, A, "studycoin", f"{reward}+ coins per class", A.font(14, bold=True), COIN_PURPLE,
                    (240, 236, 252), (fx + 420, self.time_rows["end"] + 21), "midleft", isz=20, pad=(8, 4))
        W.text(surf, "Colour", f, C.C_TEXT, (lx, self.color_y + 21), "midleft")
        days_txt = days_label(self.days) if self.days else "no days picked"
        W.text(surf, f"Repeats every {days_txt}", A.font(14), C.C_TEXT_DIM, (lx, ey + 72))
        if self.error:
            W.text(surf, self.error, A.font(15, bold=True), C.C_BAD, (self.rect.right - 30, self.rect.bottom - 88),
                   "bottomright")

    def draw_after(self, surf):
        for b in self.buttons:
            if hasattr(b, "swatch"):
                r = b.rect.inflate(-8, -8)
                pygame.draw.circle(surf, b.swatch, r.center, r.w // 2)
                if C.CLASS_COLORS.index(b.swatch) == self.color:
                    pygame.draw.circle(surf, C.C_TEXT, r.center, r.w // 2 + 4, 3)


class ClassAlertOverlay(Overlay):
    def __init__(self, scene, entry):
        super().__init__(scene, 600, 350, "")
        self.planner = scene.planner
        self.entry = entry
        self.t = 0.0
        self.reward = self.planner.reward_for(entry)
        b = self.btn((self.rect.right - 300, self.rect.bottom - 82, 270, 56), f"I'm in class!  +{self.reward}",
                     on_click=self.check_in, style="good", icon="check", font_size=19, icon_size=26)
        b.pulse = 1
        self.btn((self.rect.x + 30, self.rect.bottom - 82, 150, 56), "Later", on_click=self.close, font_size=18)

    def check_in(self):
        self.scene.check_in(self.entry)
        self.close()

    def on_close(self):
        self.app.attention(None)

    def update(self, dt):
        self.t += dt
        now = datetime.now()
        if self.planner.status(self.entry, now.date(), now) != "open":
            self.close()

    def draw_body(self, surf):
        A, e = self.assets, self.entry
        band = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 120)
        pygame.draw.rect(surf, W.lerp_color(e.rgb, (255, 255, 255), .78), band,
                         border_top_left_radius=22, border_top_right_radius=22)
        bob = int(4 * abs(((self.t * 1.6) % 2) - 1))
        ic = A.icon("class", 76)
        surf.blit(ic, ic.get_rect(center=(self.rect.x + 80, band.centery - bob)))
        W.text(surf, "Class time!", A.font(30, bold=True), C.C_TEXT, (self.rect.x + 140, band.y + 26))
        W.text(surf, "Did you make it to class?", A.font(17), C.C_TEXT_DIM, (self.rect.x + 140, band.y + 68))
        y = band.bottom + 22
        f = A.font(22, bold=True)
        W.text(surf, W.fit(e.name, f, self.rect.w - 60), f, C.C_TEXT, (self.rect.x + 30, y))
        sub = e.time_label() + (f"  ·  {e.room}" if e.room else "")
        W.text(surf, sub, A.font(16), C.C_TEXT_DIM, (self.rect.x + 30, y + 34))
        msg = f"Check in before {fmt_clock(e.end)} to earn {self.reward} {C.COIN_NAME}"
        if self.planner.streak:
            msg += f" (streak {self.planner.streak})."
        else:
            msg += "."
        W.text_block(surf, msg, A.font(15), C.C_TEXT, self.rect.x + 30, y + 70, self.rect.w - 60)
