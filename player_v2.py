from __future__ import annotations
import json
import logging
import os
import pygame
from pygame.font import Font
import requests
import sys
import time

from io import BytesIO
from niatools.settings import Settings
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from threading import Thread, Lock
from typing import Optional

import helpers
import surfaces
from customtypes import StationResponse

class LoadingText(surfaces.Resizing, surfaces.ScalingText):
    def __init__(self, parent: Optional[surfaces.SurfaceBase] = None, font: Optional[Font] = None):
        super().__init__(parent, "Loading...", (255, 255, 255), font)
    
    def getRect(self) -> pygame.Rect:
        if not self.parent:
            raise ValueError
        return pygame.Rect(self.parent.width/4, self.parent.height/4, self.parent.width/2, self.parent.height/2)

class LoadingScreen(surfaces.Screen):
    BG_COLOR = pygame.Color(0, 0, 0)

    def __init__(self, app: Main):
        self.app: Main
        super().__init__(app)
        self.text = LoadingText(self, self.app.font)

class BgImage(surfaces.Cached, surfaces.Resizing, surfaces.Background):
    def render(self):
        self.app: Main
        scaled = pygame.transform.smoothscale(self.app.converted_image, self.size)
        self.surface.blit(scaled, (0, 0))

    def getRect(self) -> pygame.Rect:
        if not self.parent:
            raise ValueError
        return self.parent.rect.copy()

class NoMenuScreen(surfaces.Cached, surfaces.Screen):
    def onClick(self, x: int, y: int) -> None:
        self.app: Main
        self.app.main_screen.show()

    def onKeypress(self, key: int) -> None:
        if key in (pygame.K_F1, pygame.K_ESCAPE):
            self.app.main_screen.show()

    def onSetVisible(self):
        self.app.bg_image.parent = self
        return super().onSetVisible()
    
class MainScreen(surfaces.Screen):
    def __init__(self, app: surfaces.App):
        self.app: Main
        super().__init__(app)
        self.main_container = MainContainer(self)
    
    def onKeypress(self, key: int) -> None:
        if key == pygame.K_F1:
            self.app.no_menu_screen.show()

    def onSetVisible(self):
        self.app.bg_image.parent = self
        return super().onSetVisible()

class MainContainer(surfaces.Resizing):
    def __init__(self, parent: Optional[surfaces.SurfaceBase] = None):
        super().__init__(parent)
        self.app: Main
        self.parent: MainScreen
        self.bg = MainContainerBg(self)
        self.height = 200

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(self.parent.width*(0.5-self.app.settings.get("main_container_width")/2), self.parent.height/2-self.height/2, self.parent.width*self.app.settings.get("main_container_width"), self.height)
    
class MainContainerBg(surfaces.Cached, surfaces.Resizing, surfaces.Background):
    def getRect(self) -> pygame.Rect:
        self.app: Main
        self.parent: MainContainer
        return pygame.Rect((0, 0), self.parent.size)

    def render(self):
        scaled_blur = pygame.transform.smoothscale(self.app.blurred_image, self.parent.parent.size).convert_alpha()
        blur_rect = pygame.Rect((0, 0), self.size)
        mask_surf = pygame.Surface(self.size, pygame.SRCALPHA)
        mask_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(mask_surf, (255, 255, 255, 255), blur_rect, border_radius=int(max(self.size) * self.app.settings.get("border_radius")))
        mask = pygame.mask.from_surface(mask_surf)
        self.surface.blit(scaled_blur, (-self.x, -self.y))
        alpha_surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        self.surface.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

class SongTitle(surfaces.Cached, surfaces.Resizing):...

class Main(surfaces.App):
    @helpers.log_critical
    def __init__(self) -> None:
        self.data: StationResponse

        logging.info("Initializing")
        pygame.font.init()

        self.data_dir: str = os.path.join(Path.home(), "neuro_21_station_player")
        self.working_dir: str = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        self.settings: Settings = Settings(os.path.join(self.data_dir, "settings_v2.json"), os.path.join(self.working_dir, "data", "default_settings_v2.json"))
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 300)

        super().__init__(self.settings.get("size"), LoadingScreen)

        self.data_reload_cooldown = 0
        self.data_reloaded = False
        self.image_reloaded = False
        self.initialized = False
        self._screen_lock = Lock()
        self._image_lock = Lock()

        self.raw_image: Image.Image
        self.converted_image = pygame.Surface((1, 1))
        self.blurred_image = pygame.Surface((1, 1))

        self.no_menu_screen = NoMenuScreen(self)
        self.main_screen = MainScreen(self)

        self.bg_image = BgImage(self.main_screen)

        self.init_thread = Thread(target=self.init, daemon=True).start()

    @helpers.log_critical
    def init(self):
        logging.info("Secondary init thread started")
        self.data = None # We need to define it in order for it to not crash, is overwritten in refresh_data    # pyright: ignore[reportAttributeAccessIssue]
        self.refresh_data()
        self.initialized = True
        with self._screen_lock:
            self.main_screen.show()
        logging.info("Initialized")

    def fetch_data(self) -> StationResponse:
        response = requests.get(self.settings.get("data_url"))
        response.raise_for_status()
        return json.loads(response.content)

    def fetch_image(self, url: str) -> BytesIO:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    
    @helpers.log_error
    def refresh_data(self):
        """Refreshes the data from the station"""
        old_songid = self.data.get("now_playing").get("song").get("id") if self.data else None
        old_art = self.data.get("now_playing").get("song").get("art") if self.data else None
        self.data = self.fetch_data()
        if old_songid == self.data.get("now_playing").get("song").get("id"):
            return
        logging.debug("new data loaded")
        self.data_reloaded = True
        if old_art != self.data.get("now_playing").get("song").get("art"):
            with self._image_lock:
                self.raw_image = Image.open(self.fetch_image(self.data.get("now_playing").get("song").get("art")))
        logging.debug("new image loaded")
        self.image_reloaded = True

    def reload_data_tick(self):
        """Refreshes the data from the station, should be used in the tick loop as it resets the reloading flag"""
        self.refresh_data()
        self.data_reload_cooldown = time.time() + 5 # Only try to reload every 5 seconds if unsuccessful

    def tick(self):
        with self._screen_lock:
            super().tick()
        if not self.initialized:
            return
        if self.image_reloaded and self._image_lock.acquire(blocking=False):
            self.image_reloaded = False
            self.converted_image = pygame.image.frombytes(self.raw_image.tobytes(), self.raw_image.size, self.raw_image.mode).convert() # pyright: ignore[reportArgumentType]
            self.blurred_image = pygame.image.frombytes(ImageEnhance.Brightness(self.raw_image).enhance(self.settings.get("darken_factor")).filter(ImageFilter.GaussianBlur(self.settings.get("blur_scale"))).tobytes(), self.raw_image.size, self.raw_image.mode).convert() # pyright: ignore[reportArgumentType]
            self._image_lock.release()
            self.bg_image.redraw = True
            self.no_menu_screen.redraw = True
            self.main_screen.main_container.bg.redraw = True
        if self.data.get("playing_next").get("played_at")+1 < time.time() and self.data_reload_cooldown < time.time():
            self.data_reload_cooldown = time.time() + 30 # If the thread crashed for some reason we will retry after 30 seconds
            Thread(target=self.reload_data_tick, daemon=True).start()

    @helpers.log_critical
    def run(self):
        super().run()

class MainResizeable(Main, surfaces.ResizeableApp):...

if __name__ == "__main__":
    helpers.setup_logging(debug="--debug" in sys.argv)
    app = MainResizeable() if "--resizeable" in sys.argv else Main()
    app.run()