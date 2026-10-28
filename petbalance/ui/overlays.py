import math

import pygame

from .. import config as C
from ..economy import cost_per_serving
from ..game_state import money
from ..schedule import fmt_time
from . import widgets as W
from .scene import Overlay

COIN = (122, 104, 200)

STATUS_STYLE = {
    "upcoming": ("Upcoming", C.C_INFO),
    "due": ("Due now", C.C_WARN),
    "overdue": ("Overdue", C.C_BAD),
    "on_time": ("On time", C.C_GOOD),
    "late": ("Late", C.C_WARN),
    "missed": ("Missed", C.C_BAD),
    "skipped": ("Before start", C.C_TEXT_DIM),
}


class FeedOverlay(Overlay):
    icon = "feed"

    def __init__(self, scene, preselect=None):
        super().__init__(scene, 960, 620, "Feeding")
        self.state = scene.state
        self.sel = preselect
        self.portion = "Regular"
        self.cards = []
        self.rebuild()

    def foods(self):
        return self.state.inv.items(("food", "treat"))

    def rebuild(self):
        self.buttons = []
        foods = self.foods()
        keys = [it.key for it, _ in foods]
        if self.sel not in keys:
            self.sel = keys[0] if keys else None
        self.cards = []
        y = self.body.y + 4
        for it, qty in foods:
            r = pygame.Rect(self.body.x, y, 392, 66)
            self.cards.append((r, it.key))
            y += 76
        rx = self.rect.x + 450
        if self.sel:
            item = C.ITEMS_BY_KEY[self.sel]
            if item.kind == "food":
                for i, label in enumerate(C.PORTIONS):
                    r = pygame.Rect(rx + i * 158, self.rect.y + 240, 148, 44)
                    self.btn(r, f"{label} ({C.PORTIONS[label]:g})",
                             on_click=lambda l=label: self.set_portion(l),
                             style="selected" if label == self.portion else "secondary", font_size=16)
            servings = C.PORTIONS[self.portion] if item.kind == "food" else 1
            ok = self.state.inv.has(self.sel, servings)
            label = "Feed" if item.kind == "food" else "Give treat"
            self.btn((self.rect.right - 230, self.rect.bottom - 74, 200, 52), label,
                     on_click=self.do_feed, style="primary", enabled=ok, icon="feed", font_size=20)
        else:
            self.btn((self.rect.centerx - 110, self.rect.centery + 40, 220, 56), "Go to Shop",
                     on_click=self.go_shop, style="primary", icon="shop", font_size=20)
        if self.state.inv.has("vitamins"):
            q = self.state.inv.count("vitamins")
            given = self.state.pet.vitamins_day == self.state.day
            self.btn((self.body.x, self.rect.bottom - 74, 250, 52), f"Give Vitamins (x{q:g})",
                     on_click=self.do_vitamin, icon="vitamins", enabled=not given, font_size=17)

    def set_portion(self, label):
        self.portion = label
        self.rebuild()

    def go_shop(self):
        self.close()
        self.scene.open_shop()

    def do_feed(self):
        ok, msg = self.state.feed(self.sel, self.portion)
        self.scene.report(ok, msg, "feed")
        if ok:
            self.scene.on_fed()
            self.close()
        else:
            self.rebuild()

    def do_vitamin(self):
        ok, msg = self.state.give_vitamin()
        self.scene.report(ok, msg, "success")
        self.rebuild()

    def on_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for r, key in self.cards:
                if r.collidepoint(event.pos):
                    self.sel = key
                    self.rebuild()
                    self.assets.play("click")
                    return

    def draw_body(self, surf):
        A, st = self.assets, self.state
        f14, f16, f18 = A.font(14), A.font(16), A.font(18, bold=True)
        if not self.sel:
            W.text(surf, "Your food bowl and pantry are empty!", A.font(24, bold=True), C.C_TEXT,
                   (self.rect.centerx, self.rect.centery - 40), "center")
            W.text(surf, "Buy food in the shop, then come back to feed your pet.", f16, C.C_TEXT_DIM,
                   (self.rect.centerx, self.rect.centery - 6), "center")
            return
        mouse = pygame.mouse.get_pos()
        for r, key in self.cards:
            it = C.ITEMS_BY_KEY[key]
            qty = st.inv.count(key)
            sel = key == self.sel
            col = (255, 232, 216) if sel else ((252, 246, 238) if r.collidepoint(mouse) else (255, 255, 255))
            W.card(surf, r, col, C.C_ACCENT if sel else C.C_PANEL_EDGE)
            surf.blit(A.icon(key, 48), (r.x + 10, r.y + 9))
            W.text(surf, it.name, f18, C.C_TEXT, (r.x + 70, r.y + 10))
            unit = ("treat" if it.kind == "treat" else "serving") + ("" if qty == 1 else "s")
            W.text(surf, f"{qty:g} {unit}  ·  fills {it.satiety:g} hunger each", f14, C.C_TEXT_DIM,
                   (r.x + 70, r.y + 38))
        it = C.ITEMS_BY_KEY[self.sel]
        rx, ry = self.rect.x + 450, self.body.y + 4
        surf.blit(A.icon(it.key, 72), (rx, ry))
        W.text(surf, it.name, A.font(26, bold=True), C.C_TEXT, (rx + 88, ry + 4))
        W.text_block(surf, it.desc, f16, C.C_TEXT_DIM, rx + 88, ry + 42, 380)
        if it.kind == "food":
            W.text(surf, "Portion", f18, C.C_TEXT, (rx, self.rect.y + 210))
        else:
            W.text(surf, "Treats are a happiness boost, not a meal.", f16, C.C_TEXT_DIM,
                   (rx, self.rect.y + 220))
        servings = C.PORTIONS[self.portion] if it.kind == "food" else 1
        r = st.pet.preview_feed(it, servings)

        y = self.rect.y + 304
        W.text(surf, "Hunger", f18, C.C_TEXT, (rx, y))
        W.text(surf, f"{r.hunger_before:.0f}  ->  {r.hunger_after:.0f}", f18, C.C_TEXT,
               (rx + 470, y), "topright")
        W.bar(surf, (rx, y + 30, 470, 18), r.hunger_before, C.C_HUNGER,
              ghost=r.hunger_after, ghost_color=C.C_GOOD)
        y += 62
        wc = r.weight_change
        effects = [
            ("Weight", f"{'+' if wc >= 0 else ''}{wc:.2f} kg  (now {st.pet.weight:.2f} kg)",
             C.C_BAD if wc > 0.02 else C.C_TEXT),
            ("Happiness", f"{r.happiness_change:+.0f}", C.C_GOOD if r.happiness_change > 0 else C.C_BAD),
            ("HP", f"{r.hp_change:+.0f}", C.C_GOOD if r.hp_change > 0 else C.C_TEXT_DIM),
        ]
        for label, val, col in effects:
            W.text(surf, label, f16, C.C_TEXT_DIM, (rx, y))
            W.text(surf, val, A.font(16, bold=True), col, (rx + 470, y), "topright")
            y += 26
        y += 6
        if it.kind == "food":
            verdict = {"good": ("Good portion", C.C_GOOD),
                       "too_much": ("Too much: extra becomes weight", C.C_BAD),
                       "too_little": ("Too little: still hungry after", C.C_WARN)}[r.verdict]
            W.chip(surf, verdict[0], A.font(16, bold=True), (255, 255, 255), verdict[1], (rx, y))
            meal = st.schedule.current_meal(st.minute)
            if meal:
                late = st.minute > meal.time + C.ON_TIME_WINDOW
                s = f"Counts as {meal.name} ({'late' if late else 'on time'})"
                col = C.C_WARN if late else C.C_GOOD
            else:
                nxt = st.schedule.next_meal(st.minute)
                s = "Extra meal: no meal is due" + (f" (next: {nxt.name} {fmt_time(nxt.time)})" if nxt else "")
                col = C.C_WARN
            W.text(surf, s, f16, col, (rx, y + 38))
        if not st.inv.has(self.sel, servings):
            W.text(surf, "Not enough in stock for this portion.", f16, C.C_BAD,
                   (self.rect.right - 30, self.rect.bottom - 84), "bottomright")


class ShopOverlay(Overlay):
    icon = "shop"

    def __init__(self, scene, tab="supplies"):
        super().__init__(scene, 1180, 620, "Pet Shop")
        self.state = scene.state
        self.tab = tab
        self.hover_key = None
        self.cards = []
        self.rebuild()

    @property
    def planner(self):
        return self.state.planner

    def rebuild(self):
        self.buttons = []
        self.cards = []
        st, coins = self.state, (self.planner.coins if self.planner else 0)
        tx = self.rect.x + 250
        for key, label, icon in (("supplies", "Supplies", "shop"), ("coins", "Coin Rewards", "studycoin")):
            w = 150 if key == "supplies" else 190
            self.btn((tx, self.rect.y + 17, w, 40), label, icon=icon, icon_size=22,
                     on_click=lambda k=key: self.set_tab(k),
                     style="selected" if self.tab == key else "secondary", font_size=16)
            tx += w + 10
        x0, y0 = self.body.x, self.body.y
        cw, ch, gap = 192, 246, 14
        items = [it for it in C.ITEMS if it.coin_only == (self.tab == "coins")]
        for i, it in enumerate(items):
            c, r = i % 4, i // 4
            rect = pygame.Rect(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch)
            self.cards.append((rect, it))
            by = rect.bottom - 50
            if self.tab == "supplies":
                price = st.price(it.key)
                half = (rect.w - 24 - 6) // 2
                self.btn((rect.x + 12, by, half, 40), money(price), on_click=lambda k=it.key: self.do_buy(k),
                         style="primary", enabled=st.wallet.can_afford(price), font_size=15,
                         tooltip=f"Pay {money(price)}")
                self.btn((rect.x + 18 + half, by, half, 40), str(it.coin_price), icon="studycoin", icon_size=20,
                         on_click=lambda k=it.key: self.do_buy_coins(k), style="coin",
                         enabled=coins >= it.coin_price, font_size=15,
                         tooltip=f"Pay {it.coin_price} {C.COIN_NAME}")
            else:
                owned = it.kind == "decor" and st.inv.has(it.key)
                label = "In your room" if owned else str(it.coin_price)
                self.btn((rect.x + 12, by, rect.w - 24, 40), label, icon=None if owned else "studycoin",
                         icon_size=22, on_click=lambda k=it.key: self.do_buy_coins(k), style="coin",
                         enabled=not owned and coins >= it.coin_price, font_size=16)
        if self.tab == "coins":
            self.btn((self.body.x + 24, self.body.y + ch + gap + 170, 260, 48), "Open Class Schedule",
                     icon="class", icon_size=26, on_click=self.open_classes, font_size=16)

    def set_tab(self, tab):
        self.tab = tab
        self.rebuild()

    def open_classes(self):
        from .classes import ClassesOverlay
        self.close()
        self.scene.open(ClassesOverlay(self.scene))

    def do_buy(self, key):
        ok, msg = self.state.buy(key)
        self.scene.report(ok, msg, "buy")
        self.rebuild()

    def do_buy_coins(self, key):
        ok, msg = self.state.buy_with_coins(key)
        self.scene.report(ok, msg, "buy")
        self.rebuild()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.hover_key = None
        for rect, it in self.cards:
            if rect.collidepoint(mouse):
                self.hover_key = it.key

    def draw_body(self, surf):
        A, st = self.assets, self.state
        f13, f14, f16 = A.font(13), A.font(14), A.font(16, bold=True)
        for rect, it in self.cards:
            hov = it.key == self.hover_key
            coin_item = it.coin_only
            edge = (178, 164, 230) if coin_item else C.C_ACCENT
            W.card(surf, rect, (255, 250, 244) if hov else (255, 255, 255), edge if hov else C.C_PANEL_EDGE, 16)
            if coin_item:
                glow = pygame.Rect(0, 0, 84, 84)
                glow.midtop = (rect.centerx, rect.y + 2)
                pygame.draw.ellipse(surf, (243, 239, 253), glow)
            surf.blit(A.icon(it.key, 56), A.icon(it.key, 56).get_rect(midtop=(rect.centerx, rect.y + 10)))
            W.text(surf, it.name, f16, C.C_TEXT, (rect.centerx, rect.y + 72), "midtop")
            if it.kind in ("food", "treat"):
                unit = "treat" if it.kind == "treat" else "serving"
                sub = f"{it.servings:g} {unit}{'' if it.servings == 1 else 's'}"
                if not coin_item:
                    sub += f" · {money(cost_per_serving(it, st.day))}/each"
            elif it.kind == "decor":
                sub = "Room decoration"
            else:
                sub = {"vitamins": "3 doses", "toy": "10 play sessions"}.get(it.key, "")
            W.text(surf, sub, f13, COIN if coin_item else C.C_ACCENT_DARK, (rect.centerx, rect.y + 96), "midtop")
            W.text_block(surf, it.desc, f13, C.C_TEXT_DIM, rect.x + 12, rect.y + 120, rect.w - 24, 2, max_lines=4)
            owned = st.inv.count(it.key)
            if owned and it.kind != "decor":
                W.chip(surf, f"Owned {owned:g}", A.font(12, bold=True), (255, 255, 255), C.C_GOOD,
                       (rect.right - 8, rect.y + 8), "topright", pad=(7, 2))
        if self.tab == "coins":
            self.draw_how_to_earn(surf)
        self.draw_sidebar(surf)

    def draw_how_to_earn(self, surf):
        A = self.assets
        box = pygame.Rect(self.body.x, self.body.y + 260, 4 * 192 + 3 * 14, 236)
        pygame.draw.rect(surf, (246, 243, 253), box, border_radius=16)
        pygame.draw.rect(surf, (214, 206, 240), box, 2, border_radius=16)
        x, y = box.x + 24, box.y + 18
        W.text(surf, f"How to earn {C.COIN_NAME}", A.font(19, bold=True), C.C_TEXT, (x, y))
        steps = [("1", "Put your real class schedule in the Class Schedule."),
                 ("2", "When a class starts, the game reminds you."),
                 ("3", "Click \"I'm in class!\" to check in and collect coins."),
                 ("4", f"Attend classes in a row for a streak bonus (up to +{C.STREAK_BONUS_CAP}).")]
        y += 36
        for n, line in steps:
            pygame.draw.circle(surf, COIN, (x + 11, y + 10), 11)
            W.text(surf, n, A.font(13, bold=True), (255, 255, 255), (x + 11, y + 10), "center")
            W.text(surf, line, A.font(15), C.C_TEXT, (x + 32, y + 1))
            y += 30
        rate = (f"Each class pays {C.CLASS_BASE_COINS} coins + {C.CLASS_COINS_PER_HOUR} per hour. "
                "Uses your computer's real clock.")
        W.text(surf, rate, A.font(13), C.C_TEXT_DIM, (box.right - 24, box.bottom - 30), "topright")

    def draw_sidebar(self, surf):
        A, st = self.assets, self.state
        f14 = A.font(14)
        coins = self.planner.coins if self.planner else 0
        sx = self.rect.right - 334
        side = pygame.Rect(sx, self.body.y, 310, self.body.h)
        pygame.draw.rect(surf, (252, 245, 236), side, border_radius=16)
        x, y = side.x + 18, side.y + 14
        half = (side.w - 36) // 2
        W.text(surf, "Pesos", A.font(14), C.C_TEXT_DIM, (x, y))
        W.text(surf, C.COIN_NAME, A.font(14), C.C_TEXT_DIM, (x + half + 8, y))
        surf.blit(A.icon("coin", 28), (x, y + 24))
        W.text(surf, money(st.wallet.balance), A.font(24, bold=True), C.C_TEXT, (x + 34, y + 38), "midleft")
        surf.blit(A.icon("studycoin", 28), (x + half + 8, y + 24))
        W.text(surf, f"{coins:,}", A.font(24, bold=True), COIN, (x + half + 42, y + 38), "midleft")
        y += 72
        if self.hover_key:
            it = C.ITEMS_BY_KEY[self.hover_key]
            parts = []
            if not it.coin_only:
                after = st.wallet.balance - st.price(it.key)
                parts.append((f"{money(after)}" if after >= 0 else "not enough", after))
            c_after = coins - it.coin_price
            parts.append((f"{c_after} coins" if c_after >= 0 else "not enough coins", c_after))
            W.text(surf, "After buying:", A.font(14, bold=True), C.C_TEXT, (x, y))
            yy = y
            for txt, val in parts:
                col = C.C_BAD if val < 0 else C.C_GOOD
                W.text(surf, txt, A.font(14, bold=True), col, (side.right - 18, yy), "topright")
                yy += 20
        else:
            W.text(surf, "Hover an item to see what's left.", f14, C.C_TEXT_DIM, (x, y))
        y += 46
        if self.tab == "supplies":
            food = st.inv.food_servings()
            W.text(surf, f"Food in stock: {food:g} servings", f14, C.C_TEXT, (x, y)); y += 22
            W.text(surf, f"About {food / 3:.1f} days of regular meals", f14, C.C_TEXT_DIM, (x, y)); y += 22
            W.text(surf, f"Spent today: {money(st.wallet.spent_on(st.day))}", f14, C.C_TEXT, (x, y)); y += 22
            W.text(surf, f"Prices today: +{int(C.PRICE_INCREASE_PER_DAY * 100 * (st.day - 1))}% vs Day 1",
                   f14, C.C_TEXT_DIM, (x, y)); y += 32
            W.text(surf, "Recent expenses", A.font(16, bold=True), C.C_TEXT, (x, y)); y += 28
            hist = [(f"D{e.day} {fmt_time(e.minute)}", e.label, e.amount, money(abs(e.amount)))
                    for e in reversed(st.wallet.history)][:8]
        else:
            p = self.planner
            n = p.streak if p else 0
            W.text(surf, f"Streak: {n} class{'' if n == 1 else 'es'} in a row", f14, C.C_TEXT, (x, y)); y += 22
            W.text(surf, f"Earned so far: {p.total_earned if p else 0} coins", f14, C.C_TEXT_DIM, (x, y)); y += 32
            W.text(surf, "Coin history", A.font(16, bold=True), C.C_TEXT, (x, y)); y += 28
            hist = [(h["when"], h["label"], h["amount"], str(abs(h["amount"])))
                    for h in reversed(p.history if p else [])][:9]
        if not hist:
            W.text(surf, "Nothing yet.", f14, C.C_TEXT_DIM, (x, y))
        for when, label, amount, amt_txt in hist:
            W.text(surf, when, A.font(12), C.C_TEXT_DIM, (x, y + 2))
            W.text(surf, W.fit(label, f14, 128), f14, C.C_TEXT, (x + 90, y))
            amt = ("+" if amount > 0 else "-") + amt_txt
            W.text(surf, amt, A.font(14, bold=True), C.C_GOOD if amount > 0 else C.C_BAD,
                   (side.right - 14, y), "topright")
            y += 24

    def draw_after(self, surf):
        for b in self.buttons:
            if b.hover and b.tooltip:
                W.tooltip(surf, self.assets, b.tooltip, b.rect)


class InventoryOverlay(Overlay):
    icon = "inventory"

    def __init__(self, scene):
        super().__init__(scene, 800, 600, "Inventory")
        self.state = scene.state
        self.rows = []
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        self.rows = []
        cw = (self.body.w - 12) // 2
        for i, (it, qty) in enumerate(self.state.inv.items()):
            r = pygame.Rect(self.body.x + (i % 2) * (cw + 12), self.body.y + (i // 2) * 68, cw, 60)
            self.rows.append((r, it, qty))
            if it.kind in ("food", "treat"):
                label, fn = "Feed", (lambda k=it.key: self.feed(k))
            elif it.key == "vitamins":
                label, fn = "Give", self.vitamin
            elif it.kind == "decor":
                label, fn = None, None
            else:
                label, fn = "Play", self.play
            if label:
                self.btn((r.right - 100, r.y + 11, 88, 38), label, on_click=fn, style="primary", font_size=16)
        self.btn((self.rect.right - 210, self.rect.bottom - 70, 180, 48), "Open Shop",
                 on_click=self.shop, icon="shop", font_size=17)

    def feed(self, key):
        self.close()
        self.scene.open_feed(key)

    def vitamin(self):
        self.scene.report(*self.state.give_vitamin(), "success")
        self.rebuild()

    def play(self):
        self.close()
        self.scene.do_play()

    def shop(self):
        self.close()
        self.scene.open_shop()

    def draw_body(self, surf):
        A = self.assets
        if not self.rows:
            W.text(surf, "Your inventory is empty.", A.font(22, bold=True), C.C_TEXT,
                   (self.rect.centerx, self.rect.centery - 30), "center")
            W.text(surf, "Visit the shop to buy food and supplies.", A.font(16), C.C_TEXT_DIM,
                   (self.rect.centerx, self.rect.centery + 4), "center")
        for r, it, qty in self.rows:
            W.card(surf, r)
            surf.blit(A.icon(it.key, 44), (r.x + 10, r.y + 8))
            W.text(surf, it.name, A.font(18, bold=True), C.C_TEXT, (r.x + 66, r.y + 8))
            if it.kind == "decor":
                W.text(surf, "Placed in the room", A.font(14), C.C_TEXT_DIM, (r.x + 66, r.y + 34))
                W.chip(surf, "Decor", A.font(13, bold=True), (255, 255, 255), COIN, (r.right - 16, r.centery),
                       "midright")
                continue
            unit = {"food": "servings", "treat": "treats", "supply": "uses"}[it.kind]
            W.text(surf, f"{qty:g} {unit}", A.font(14), C.C_TEXT_DIM, (r.x + 66, r.y + 34))
        food = self.state.inv.food_servings()
        W.text(surf, f"Food servings in stock: {food:g}", A.font(16), C.C_TEXT_DIM,
               (self.body.x, self.rect.bottom - 56))


class ScheduleOverlay(Overlay):
    icon = "schedule"

    def __init__(self, scene):
        super().__init__(scene, 800, 540, "Today's Feeding Schedule")
        self.state = scene.state

    def draw_body(self, surf):
        A, st = self.assets, self.state
        tl = pygame.Rect(self.body.x + 10, self.body.y + 40, self.body.w - 20, 14)
        span = C.DAY_END - C.DAY_START

        def tx(minute):
            return tl.x + int(tl.w * (minute - C.DAY_START) / span)

        pygame.draw.rect(surf, (236, 226, 214), tl, border_radius=7)
        done = tl.copy(); done.w = max(0, min(tl.w, tx(max(C.DAY_START, st.minute)) - tl.x))
        if done.w > 0:
            pygame.draw.rect(surf, (250, 210, 180), done, border_radius=7)
        for h in range(6, 23, 2):
            x = tx(h * 60)
            W.text(surf, fmt_time(h * 60).replace(":00", ""), A.font(12), C.C_TEXT_DIM, (x, tl.bottom + 6), "midtop")
        for m in st.schedule.meals:
            col = STATUS_STYLE[m.status][1]
            win = pygame.Rect(tx(m.time - C.EARLY_WINDOW), tl.y - 4,
                              tx(m.time + C.ON_TIME_WINDOW) - tx(m.time - C.EARLY_WINDOW), tl.h + 8)
            pygame.draw.rect(surf, (*col,), win, 2, border_radius=6)
            pygame.draw.circle(surf, col, (tx(m.time), tl.centery), 9)
            W.text(surf, m.name, A.font(13, bold=True), C.C_TEXT, (tx(m.time), tl.y - 10), "midbottom")
        nx = tx(max(C.DAY_START, min(C.DAY_END, st.minute)))
        pygame.draw.line(surf, C.C_ACCENT_DARK, (nx, tl.y - 8), (nx, tl.bottom + 4), 3)

        y = self.body.y + 100
        for m in st.schedule.meals:
            r = pygame.Rect(self.body.x, y, self.body.w, 74)
            pygame.draw.rect(surf, (255, 255, 255), r, border_radius=14)
            pygame.draw.rect(surf, C.C_PANEL_EDGE, r, 2, border_radius=14)
            surf.blit(A.icon("clock", 40), (r.x + 14, r.y + 17))
            W.text(surf, m.name, A.font(20, bold=True), C.C_TEXT, (r.x + 68, r.y + 12))
            W.text(surf, fmt_time(m.time), A.font(16), C.C_TEXT_DIM, (r.x + 68, r.y + 42))
            label, col = STATUS_STYLE[m.status]
            W.chip(surf, label, A.font(15, bold=True), (255, 255, 255), col, (r.right - 16, r.y + 14), "topright")
            if m.fed_at >= 0:
                note = f"Fed at {fmt_time(m.fed_at)}"
            elif m.status == "missed":
                note = "Not fed"
            elif m.status == "skipped":
                note = "Before you started - not counted"
            else:
                note = f"Reminder at {fmt_time(m.time - st.settings.reminder_lead)}"
            W.text(surf, note, A.font(14), C.C_TEXT_DIM, (r.right - 16, r.y + 48), "topright")
            y += 84
        info = (f"Real clock times. On time = up to {C.EARLY_WINDOW} min early or {C.ON_TIME_WINDOW} min late.  "
                f"After {C.MISSED_AFTER // 60} hours a meal is missed.  "
                f"Reminders come {st.settings.reminder_lead} min before (change in Settings).")
        W.text_block(surf, info, A.font(14), C.C_TEXT_DIM, self.body.x, self.rect.bottom - 60, self.body.w)


class NotificationsOverlay(Overlay):
    icon = "bell"

    def __init__(self, scene):
        super().__init__(scene, 780, 580, "Notifications")
        self.state = scene.state
        self.scroll = 0
        self.unread_ids = {id(n) for n in self.state.notifier.log if not n.read}
        self.state.notifier.mark_all_read()

    def on_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 40)

    def draw_body(self, surf):
        A = self.assets
        log = list(reversed(self.state.notifier.log))
        area = pygame.Rect(self.body.x, self.body.y, self.body.w, self.body.h)
        row_h = 56
        max_scroll = max(0, len(log) * row_h - area.h)
        self.scroll = min(self.scroll, max_scroll)
        prev_clip = surf.get_clip()
        surf.set_clip(area)
        y = area.y - self.scroll
        if not log:
            W.text(surf, "No notifications yet.", A.font(18), C.C_TEXT_DIM, area.center, "center")
        for n in log:
            if y + row_h >= area.y and y <= area.bottom:
                r = pygame.Rect(area.x, y, area.w - 12, row_h - 8)
                bg = (255, 246, 236) if id(n) in self.unread_ids else (255, 255, 255)
                pygame.draw.rect(surf, bg, r, border_radius=12)
                col = W.level_color(n.level)
                pygame.draw.rect(surf, col, (r.x, r.y, 6, r.h), border_top_left_radius=12,
                                 border_bottom_left_radius=12)
                msg = n.text
                f = A.font(16)
                while f.size(msg)[0] > r.w - 190 and len(msg) > 4:
                    msg = msg[:-5] + "..."
                W.text(surf, msg, f, C.C_TEXT, (r.x + 20, r.centery), "midleft")
                W.text(surf, f"Day {n.day} · {fmt_time(n.minute)}", A.font(13), C.C_TEXT_DIM,
                       (r.right - 14, r.centery), "midright")
            y += row_h
        surf.set_clip(prev_clip)
        if max_scroll:
            k = area.h / (len(log) * row_h)
            th = max(30, int(area.h * k))
            ty = area.y + int((area.h - th) * self.scroll / max_scroll)
            pygame.draw.rect(surf, C.C_PANEL_EDGE, (area.right - 6, ty, 6, th), border_radius=3)


def draw_star(surf, center, r, filled):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * .45
        pts.append((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a)))
    pygame.draw.polygon(surf, C.C_HAPPY if filled else (230, 220, 208), pts)
    pygame.draw.polygon(surf, (210, 160, 60) if filled else (210, 200, 190), pts, 2)


class SummaryOverlay(Overlay):
    closable = False

    def __init__(self, scene):
        super().__init__(scene, 960, 640, "")
        self.state = scene.state
        self.s = self.state.summary
        tonight = self.state.day_over and self.s["day"] == self.state.day
        label = f"Good night, {self.state.pet.name}" if tonight else "Continue"
        self.btn((self.rect.right - 310, self.rect.bottom - 76, 280, 54), label,
                 on_click=self.done, style="primary", font_size=19)
        self.btn((self.rect.right - 540, self.rect.bottom - 76, 214, 54), "Save & Menu",
                 on_click=self.menu, font_size=18)
        self.t = 0

    def done(self):
        self.app.save()
        self.close()

    def menu(self):
        self.app.go_menu()

    def update(self, dt):
        self.t += dt

    def draw_body(self, surf):
        A, s = self.assets, self.s
        x, y = self.rect.x + 36, self.rect.y + 28
        W.text(surf, f"Day {s['day']} Summary", A.font(34, bold=True), C.C_TEXT, (x, y))
        for i in range(3):
            draw_star(surf, (self.rect.right - 190 + i * 64, y + 26), 26, i < s["stars"] and self.t > .3 + i * .25)
        W.text(surf, f"{s['rating']}  ·  Score {s['score']}/100", A.font(18, bold=True), C.C_ACCENT_DARK,
               (x, y + 48))
        y += 92
        stats = [
            ("heart", "Health", f"{s['hp']} HP"),
            ("happy", "Happiness", f"{s['happiness']}%"),
            ("weight", "Weight", f"{s['weight']:.2f} kg · {s['weight_status']}"),
            ("schedule", "Meals", f"{s['on_time']} on time · {s['late']} late · {s['missed']} missed"),
            ("coin", "Spent today", money(s["spent"])),
            ("coin", "Balance", money(s["balance"])),
        ]
        cw = (self.rect.w - 72 - 16) // 2
        for i, (ic, label, val) in enumerate(stats):
            cx = x + (i % 2) * (cw + 16)
            cy = y + (i // 2) * 62
            r = pygame.Rect(cx, cy, cw, 54)
            pygame.draw.rect(surf, (255, 255, 255), r, border_radius=12)
            surf.blit(A.icon(ic, 34), (r.x + 10, r.y + 10))
            W.text(surf, label, A.font(13), C.C_TEXT_DIM, (r.x + 54, r.y + 7))
            W.text(surf, val, A.font(18, bold=True), C.C_TEXT, (r.x + 54, r.y + 25))
        y += 3 * 62 + 8
        g = pygame.Rect(x, y, self.rect.w - 72, 58)
        col = C.C_GOOD if s["goal_met"] else C.C_WARN
        pygame.draw.rect(surf, (255, 255, 255), g, border_radius=12)
        pygame.draw.rect(surf, col, g, 2, border_radius=12)
        W.text(surf, f"Daily goal · {s['goal_title']}", A.font(14, bold=True), C.C_TEXT_DIM, (g.x + 16, g.y + 8))
        W.text(surf, s["goal_desc"], A.font(16), C.C_TEXT, (g.x + 16, g.y + 30))
        W.chip(surf, "Completed!" if s["goal_met"] else "Not met", A.font(15, bold=True),
               (255, 255, 255), col, (g.right - 14, g.centery), "midright")
        y += 74
        colw = (self.rect.w - 72 - 24) // 2
        W.text(surf, "What went well", A.font(17, bold=True), C.C_GOOD, (x, y))
        W.text(surf, "What to improve", A.font(17, bold=True), C.C_ACCENT_DARK, (x + colw + 24, y))
        yy = y + 28
        for line in s["good"][:4] or ["Keep at it — tomorrow is a new day."]:
            pygame.draw.circle(surf, C.C_GOOD, (x + 6, yy + 9), 4)
            yy = W.text_block(surf, line, A.font(15), C.C_TEXT, x + 18, yy, colw - 18, 2)
        yy = y + 28
        for line in s["improve"][:4] or ["Nothing major. Great job!"]:
            pygame.draw.circle(surf, C.C_WARN, (x + colw + 30, yy + 9), 4)
            yy = W.text_block(surf, line, A.font(15), C.C_TEXT, x + colw + 42, yy, colw - 18, 2)


class RecoveryOverlay(Overlay):
    closable = False

    def __init__(self, scene):
        super().__init__(scene, 640, 420, "")
        self.state = scene.state
        bal = self.state.wallet.balance
        label = (f"Visit the vet ({money(C.VET_COST)})" if bal >= C.VET_COST
                 else f"Visit the vet (pay {money(bal)})")
        self.btn((self.rect.centerx - 160, self.rect.bottom - 80, 320, 56), label,
                 on_click=self.vet, style="primary", font_size=19)

    def vet(self):
        self.state.vet_visit()
        self.assets.play("success")
        self.close()

    def draw_body(self, surf):
        A = self.assets
        img = A.pet_image("hungry", 220, 140)
        surf.blit(img, img.get_rect(midtop=(self.rect.centerx, self.rect.y + 24)))
        W.text(surf, f"{self.state.pet.name} fainted!", A.font(30, bold=True), C.C_BAD,
               (self.rect.centerx, self.rect.y + 180), "midtop")
        msg = ("HP reached zero after too long without proper care. "
               "A vet visit restores HP to 50.")
        if self.state.wallet.balance < C.VET_COST:
            msg += " You can't afford the full fee, so the vet will accept what you have this time."
        W.text_block(surf, msg, A.font(16), C.C_TEXT, self.rect.x + 50, self.rect.y + 226, self.rect.w - 100)


class AwayOverlay(Overlay):
    icon = "clock"

    def __init__(self, scene, report):
        super().__init__(scene, 680, 520, "While you were away")
        self.r = report
        self.btn((self.rect.right - 250, self.rect.bottom - 76, 220, 54), "Let's take care",
                 on_click=self.close, style="primary", font_size=19)

    def draw_body(self, surf):
        A, r, st = self.assets, self.r, self.scene.state
        x, y, w = self.body.x + 6, self.body.y + 4, self.body.w - 12
        mins = int(r["minutes"])
        d, rem = divmod(mins, 24 * 60)
        h, m = divmod(rem, 60)
        gone = (f"{d} day{'s' if d != 1 else ''} " if d else "") + (f"{h}h {m:02d}m" if h or not d else "")
        W.text(surf, f"You were gone for {gone.strip()}.", A.font(19, bold=True), C.C_TEXT, (x, y))
        sub = f"It's now Day {st.day}, {fmt_time(st.minute)}."
        if r["days"]:
            sub += f" {r['days']} new day{'s' if r['days'] != 1 else ''} started while you were away."
        W.text_block(surf, sub, A.font(15), C.C_TEXT_DIM, x, y + 30, w)
        y += 76
        rows = [("heart", "HP", r["hp"], "{:.0f}", True), ("hunger", "Hunger", r["hunger"], "{:.0f}", False),
                ("happy", "Happiness", r["happiness"], "{:.0f}%", True),
                ("weight", "Weight", r["weight"], "{:.2f} kg", None),
                ("coin", "Money", r["money"], None, True)]
        cw = (w - 12) // 2
        for i, (ic, label, (a, b), fmt, up_good) in enumerate(rows):
            rr = pygame.Rect(x + (i % 2) * (cw + 12), y + (i // 2) * 60, cw, 52)
            W.card(surf, rr)
            surf.blit(A.icon(ic, 30), (rr.x + 10, rr.y + 11))
            W.text(surf, label, A.font(13), C.C_TEXT_DIM, (rr.x + 50, rr.y + 6))
            fa, fb = (money(a), money(b)) if fmt is None else (fmt.format(a), fmt.format(b))
            W.text(surf, f"{fa}  ->  {fb}", A.font(16, bold=True), C.C_TEXT, (rr.x + 50, rr.y + 24))
            if up_good is not None and abs(b - a) >= 0.5:
                good = (b > a) == up_good
                W.chip(surf, "up" if b > a else "down", A.font(12, bold=True), (255, 255, 255),
                       C.C_GOOD if good else C.C_BAD, (rr.right - 10, rr.centery), "midright", pad=(7, 2))
        y += 3 * 60 + 6
        if r["missed"]:
            names = ", ".join(r["missed"][:6]) + (" ..." if len(r["missed"]) > 6 else "")
            W.text_block(surf, f"Missed meals ({len(r['missed'])}): {names}", A.font(15, bold=True), C.C_BAD,
                         x, y, w, 2, max_lines=2)
            y += 46
        if r["weak"]:
            W.text_block(surf, f"{st.pet.name} held on, but is very weak. Feed {st.pet.name} and consider vitamins!",
                         A.font(15, bold=True), C.C_WARN, x, y, w, 2, max_lines=2)


TUTORIAL = [
    ("heart", "Welcome to PetBalance!",
     "This is {name}. Your job is to keep {name} healthy and happy while managing a limited budget. "
     "Watch the four meters on the right: HP, Hunger, Happiness and Weight."),
    ("schedule", "Follow the feeding schedule",
     "Time follows your computer's real clock. {name} eats at 8:00 AM, 12:30 PM and 6:30 PM, "
     "sleeps from 10 PM to 6 AM, and keeps getting hungry even while the game is closed. "
     "A reminder pops up before each meal."),
    ("feed", "Pick the right portion",
     "Open Feed to choose food and a Small, Regular or Large portion. The preview shows what will happen. "
     "Too little leaves {name} hungry. Too much turns into extra weight."),
    ("shop", "Spend wisely",
     "You start with {start}. Buy food in the Shop, compare the cost per serving and keep money for "
     "future meals. You get a {allow} allowance each new day, but prices slowly rise."),
    ("pet", "Show some love",
     "Click {name} or press Pet to raise happiness. Buy a Toy Mouse to Play, which also burns a little weight. "
     "At 10:00 PM you get a daily summary, and a new day (with allowance) starts at midnight."),
    ("class", "Go to class, earn coins",
     "Open Classes and type in your real class schedule. When a class starts (on your computer's clock) "
     "you get a reminder. Click \"I'm in class!\" to check in and earn Study Coins to spend in the shop."),
]


class TutorialOverlay(Overlay):
    def __init__(self, scene):
        super().__init__(scene, 720, 420, "")
        self.page = 0
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        last = self.page == len(TUTORIAL) - 1
        self.btn((self.rect.right - 200, self.rect.bottom - 76, 170, 52), "Let's go!" if last else "Next",
                 on_click=self.next, style="primary", font_size=19)
        if self.page > 0:
            self.btn((self.rect.right - 384, self.rect.bottom - 76, 170, 52), "Back",
                     on_click=self.back, font_size=18)
        if not last:
            self.btn((self.rect.x + 30, self.rect.bottom - 70, 120, 40), "Skip", on_click=self.close,
                     style="ghost", font_size=16)

    def next(self):
        if self.page >= len(TUTORIAL) - 1:
            self.close()
        else:
            self.page += 1
            self.rebuild()

    def back(self):
        self.page = max(0, self.page - 1)
        self.rebuild()

    def on_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
            self.next()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.back()

    def draw_body(self, surf):
        A = self.assets
        icon, title, body = TUTORIAL[self.page]
        body = body.format(name=C.PET_NAME, start=money(C.STARTING_MONEY), allow=money(C.DAILY_ALLOWANCE))
        surf.blit(A.icon(icon, 84), (self.rect.x + 40, self.rect.y + 44))
        W.text(surf, title, A.font(28, bold=True), C.C_TEXT, (self.rect.x + 146, self.rect.y + 50))
        W.text(surf, f"Tip {self.page + 1} of {len(TUTORIAL)}", A.font(14), C.C_TEXT_DIM,
               (self.rect.x + 146, self.rect.y + 92))
        W.text_block(surf, body, A.font(18), C.C_TEXT, self.rect.x + 40, self.rect.y + 150, self.rect.w - 80, 6)
        for i in range(len(TUTORIAL)):
            pygame.draw.circle(surf, C.C_ACCENT if i == self.page else C.C_PANEL_EDGE,
                               (self.rect.centerx - 40 + i * 20, self.rect.bottom - 100), 5)


class SettingsOverlay(Overlay):
    icon = "settings"

    def __init__(self, scene):
        super().__init__(scene, 660, 560, "Settings")
        self.settings = self.app.settings
        self.rebuild()

    def rebuild(self):
        self.buttons = []
        s = self.settings
        x = self.rect.right - 330
        y = self.body.y + 8
        self.rows = []

        def row(label, options, current, setter):
            nonlocal y
            self.rows.append((label, y))
            w = (300 - 8 * (len(options) - 1)) // len(options)
            for i, (txt, val) in enumerate(options):
                self.btn((x + i * (w + 8), y, w, 42), txt, on_click=lambda v=val: setter(v),
                         style="selected" if val == current else "secondary", font_size=16)
            y += 58

        row("Meal reminder", [("10 min", 10), ("15 min", 15), ("30 min", 30)], s.reminder_lead,
            lambda v: self.set("reminder_lead", v))
        row("Class reminder", [("Off", 0), ("5 min", 5), ("10 min", 10), ("15 min", 15)], s.class_reminder_lead,
            lambda v: self.set("class_reminder_lead", v))
        row("Pop-up alerts", [("On", True), ("Off", False)], s.toasts, lambda v: self.set("toasts", v))
        row("Sound", [("On", True), ("Off", False)], s.sound, lambda v: self.set("sound", v))
        row("Volume", [("Low", 0.3), ("Medium", 0.6), ("High", 1.0)], s.volume,
            lambda v: self.set("volume", v))
        row("Tutorial on new game", [("On", True), ("Off", False)], s.show_tutorial,
            lambda v: self.set("show_tutorial", v))

    def set(self, key, value):
        setattr(self.settings, key, value)
        self.settings.save()
        self.assets.apply_settings(self.settings)
        self.rebuild()

    def draw_body(self, surf):
        for label, y in self.rows:
            W.text(surf, label, self.assets.font(18, bold=True), C.C_TEXT, (self.body.x + 8, y + 10))
        W.text(surf, "Class reminder = real minutes before class starts.", self.assets.font(14), C.C_TEXT_DIM,
               (self.body.x + 8, self.rect.bottom - 58))
        W.text(surf, "Settings are saved automatically.", self.assets.font(14), C.C_TEXT_DIM,
               (self.body.x + 8, self.rect.bottom - 36))


class PauseOverlay(Overlay):
    def __init__(self, scene):
        super().__init__(scene, 420, 420, "Menu")
        cx = self.rect.centerx
        y = self.rect.y + 90
        for label, fn, style in (("Back to game", self.close, "primary"),
                                 ("Settings", self.settings, "secondary"),
                                 ("Save & Main Menu", self.app.go_menu, "secondary"),
                                 ("Save & Exit", self.app.quit, "secondary")):
            self.btn((cx - 150, y, 300, 56), label, on_click=fn, style=style, font_size=19)
            y += 72

    def settings(self):
        self.scene.open(SettingsOverlay(self.scene))


class ConfirmOverlay(Overlay):
    def __init__(self, scene, title, message, on_yes, yes="Yes", no="Cancel"):
        super().__init__(scene, 560, 280, title)
        self.message = message
        self.on_yes = on_yes
        self.btn((self.rect.right - 210, self.rect.bottom - 72, 180, 50), yes, on_click=self.yes,
                 style="primary", font_size=18)
        self.btn((self.rect.right - 404, self.rect.bottom - 72, 180, 50), no, on_click=self.close,
                 font_size=18)

    def yes(self):
        self.close()
        self.on_yes()

    def draw_body(self, surf):
        W.text_block(surf, self.message, self.assets.font(18), C.C_TEXT, self.body.x, self.body.y + 6,
                     self.body.w)
