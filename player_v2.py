from __future__ import annotations
import json
import logging
import os
import pygame
import requests
import sys
import time
import traceback

from io import BytesIO
from niatools.settings import Settings
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from threading import Thread, Lock

import helpers
import surfaces
from customtypes import StationResponse

class LoadingScreen(surfaces.Screen):
    BG_COLOR = pygame.Color(0, 0, 0)

    def __init__(self, app: Main):
        self.app: Main
        super().__init__(app)
        self.text = surfaces.ScalingText(pygame.Rect(self.width/4, self.height/4, self.width/2, self.height/2), self, "Loading...", (255, 255, 255), self.app.font)

    def onResize(self):
        super().onResize()
        self.text.rect = pygame.Rect(self.width/4, self.height/4, self.width/2, self.height/2)
        self.text.onResize()

class NoMenuScreen(surfaces.Cached, surfaces.Screen):
    def render(self) -> None:
        self.app: Main
        scaled = pygame.transform.smoothscale(self.app.converted_image, self.size)
        self.surface.blit(scaled, (0, 0))
        logging.debug("NoMenuScreen redrawn")
    
    def handle_click(self, x: int, y: int) -> None:
        self.app.main_screen.show()

    def handle_keypress(self, key: int) -> None:
        if key in (pygame.K_F1, pygame.K_ESCAPE):
            self.app.main_screen.show()
    
class MainScreen(surfaces.Screen):
    def handle_keypress(self, key: int) -> None:
        self.app: Main
        if key == pygame.K_F1:
            self.app.no_menu_screen.show()

class Main(surfaces.App):
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

        Thread(target=self.init, daemon=True).start()

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
            self.no_menu_screen.redraw = True
            logging.debug("Image Reload Set")
        if self.data.get("playing_next").get("played_at")+1 < time.time() and self.data_reload_cooldown < time.time():
            self.data_reload_cooldown = time.time() + 30 # If the thread crashed for some reason we will retry after 30 seconds
            Thread(target=self.reload_data_tick, daemon=True).start()

    def run(self):
        try:
            return super().run()
        except Exception as e:
            message = "\n".join(traceback.format_exception(e))
            message = e.__class__.__name__ + "\n\n" + message
            logging.critical(message)

class MainResizeable(Main, surfaces.ResizeableApp):...

if __name__ == "__main__":
    helpers.setup_logging(debug="--debug" in sys.argv)
    app = MainResizeable() if "--resizeable" in sys.argv else Main()
    app.run()