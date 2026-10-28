import sys
from datetime import datetime

import pygame

from . import config as C
from .assets import Assets
from .game_state import GameState, Settings
from .planner import Planner

CLASS_CHECK_SECONDS = 1.0


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        try:
            pygame.key.set_repeat(400, 35)
        except pygame.error:
            pass
        self.settings = Settings.load()
        self.assets = Assets()
        self.assets.load()
        self.assets.apply_settings(self.settings)
        try:
            pygame.display.set_icon(self.assets.icon("pet", 32))
        except pygame.error:
            pass
        self.planner = Planner.load()
        self.state = None
        self.running = True
        self._class_timer = CLASS_CHECK_SECONDS
        from .ui.menu_scene import MenuScene
        self.scene = MenuScene(self)

    def new_game(self):
        from .ui.game_scene import GameScene
        self.state = GameState(self.settings)
        self.state.planner = self.planner
        self.state.save()
        self.scene = GameScene(self, self.state, new_game=True)
        self._class_timer = CLASS_CHECK_SECONDS

    def continue_game(self):
        from .ui.game_scene import GameScene
        try:
            self.state = GameState.load(self.settings)
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("Could not load save:", e)
            return self.new_game()
        self.state.planner = self.planner
        self.state.sync(datetime.now(), away=True)
        self.state.save()
        self.scene = GameScene(self, self.state)
        self._class_timer = CLASS_CHECK_SECONDS

    def go_menu(self):
        from .ui.menu_scene import MenuScene
        self.save()
        self.state = None
        self.scene = MenuScene(self)

    def save(self):
        if self.state is not None:
            try:
                self.state.save()
            except OSError as e:
                print("Could not save:", e)
        try:
            self.planner.save()
        except OSError as e:
            print("Could not save classes:", e)

    def quit(self):
        self.save()
        self.running = False

    def attention(self, msg):
        pygame.display.set_caption(f"(!) {msg} - {C.TITLE}" if msg else C.TITLE)

    def check_classes(self, dt):
        self._class_timer += dt
        if self._class_timer < CLASS_CHECK_SECONDS:
            return
        self._class_timer = 0
        events = self.planner.update(datetime.now(), self.settings.class_reminder_lead)
        if events:
            self.scene.on_class_events(events)

    def tick(self, dt):
        self.check_classes(dt)
        self.scene.update(dt)
        self.scene.draw(self.screen)

    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.1)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                self.scene.handle(event)
            if not self.running:
                break
            self.tick(dt)
            pygame.display.flip()
        pygame.quit()


def main():
    App().run()
    sys.exit(0)
