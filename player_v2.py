from __future__ import annotations
import json
import logging
import neurokaraoke_hook as nkh
import os
import pygame
import requests
import sys
import time

from io import BytesIO
from niatools.settings import Settings
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from pygame.font import Font
from threading import Thread, Lock
from typing import Any, Optional, Literal

import helpers
import surfaces
from customtypes import StationResponse

fallbackData: StationResponse = {
        "cache": "",
        "is_online": False,
        "listeners": {
            "current": 0,
            "total": 0,
            "unique": 0
            },
        "live": {
            "art": None,
            "broadcast_start": None,
            "streamer_name": "",
            "is_live": False
        },
        "now_playing": {
            "duration": 1,
            "elapsed": 0,
            "is_request": False,
            "played_at": 0,
            "playlist": "",
            "remaining": 0,
            "sh_id": 0,
            "song": {
                "album": "",
                "art": "",
                "artist": "unknown",
                "custom_fields": {},
                "genre": "",
                "id": "",
                "isrc": "",
                "lyrics": "",
                "text": "",
                "title": "No Song"
            },
            "streamer": ""
        },
        "playing_next": {
            "cued_at": 0,
            "duration": 1,
            "is_request": False,
            "played_at": 0,
            "playlist": "",
            "song": {
                "album": "",
                "art": "",
                "artist": "unknown",
                "custom_fields": {},
                "genre": "",
                "id": "",
                "isrc": "",
                "lyrics": "",
                "text": "",
                "title": "No Song"
            }
        },
        "song_history": [],
        "station": {
            "backend": "",
            "description": "",
            "frontend": "",
            "hls_enabled": False,
            "hls_is_default": False,
            "hls_listeners": 0,
            "hls_url": "",
            "id": 0,
            "is_public": False,
            "listen_url": "",
            "mounts": [],
            "name": "",
            "playlist_m3u_url": "",
            "playlist_pls_url": "",
            "public_player_url": "",
            "remotes": [],
            "requests_enabled": False,
            "shortcode": "",
            "timezone": "",
            "url": ""
        },
    }

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
        self.main_container.onResize()
        return super().onSetVisible()

class MainContainer(surfaces.Resizing):
    def __init__(self, parent: Optional[surfaces.SurfaceBase] = None):
        self._height = 0
        super().__init__(parent)
        self.app: Main
        self.parent: MainScreen
        self.bg = MainContainerBg(self)
        self.title = SongTitle(self)
        self.row1 = ControlsRow1(self)
        self.row2 = ControlsRow2(self)
        self.height = 0

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width*(0.5-self.app.settings.get("main_container_width")/2)-self.app.content_padding,
            self.parent.height/2-self._height/2,
            self.parent.width*self.app.settings.get("main_container_width")+self.app.content_padding*2,
            self._height
        )
    
    def update(self) -> Any:
        self._height = (
            self.title.height +
            self.row1.height +
            self.row2.height +
            self.app.button_padding +
            self.app.content_padding*3
        )
        if self._height != self.height:
            self.resize()
        return super().update()
    
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
        pygame.draw.rect(mask_surf, (255, 255, 255, 255), blur_rect, border_radius=int(self.app.content_padding*2))
        mask = pygame.mask.from_surface(mask_surf)
        self.surface.blit(scaled_blur, (-self.x, -self.y))
        alpha_surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        self.surface.blit(alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

class SongTitle(surfaces.Cached, surfaces.Resizing):
    def render(self):
        self.app: Main
        self.parent: MainContainer
        title = self.app.font.render(self.app.data.get("now_playing").get("song").get("title"), True, self.app.settings.get("font_color"))
        author = self.app.font.render(self.app.data.get("now_playing").get("song").get("artist"), True, self.app.settings.get("font_color"))
        title_scale_factor = self.width/max(title.get_width(), author.get_width()*self.app.settings.get("author_scale"))
        scaled_title = pygame.transform.smoothscale_by(title, title_scale_factor)
        scaled_author = pygame.transform.smoothscale_by(author, title_scale_factor*self.app.settings.get("author_scale"))
        new_height = scaled_title.get_height()+scaled_author.get_height()
        if new_height != self.height:
            self.height = new_height
        self.surface.blit(scaled_title, (self.width/2 - scaled_title.get_width()/2, 0))
        self.surface.blit(scaled_author, (self.width/2 - scaled_author.get_width()/2, scaled_title.get_height()))

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.app.content_padding,
            self.app.content_padding,
            self.parent.width-self.app.content_padding*2,
            self.height
        )
    
class ControlsRow1(surfaces.Resizing):
    def __init__(self, parent: MainContainer):
        self.app: Main
        self.parent: MainContainer
        super().__init__(parent)
        self.playpause_btn = PlayPauseButton(self)
        self.streamtype_btn = StreamTypeButton(self)
        self.progress = ProgressBar(self)
    
    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.app.content_padding,
            self.parent.title.height + self.app.content_padding*2,
            self.parent.width - self.app.content_padding*2,
            self.app.controls_size
        )

class ProgressBar(surfaces.Resizing):
    def __init__(self, parent: Optional[surfaces.SurfaceBase] = None):
        self.parent: ControlsRow1
        self.app: Main
        super().__init__(parent)
        self.empty_color = self.app.settings.get("progress_bar_color")
        self.color = self.app.settings.get("button_color")

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            0,
            0,
            self.parent.width - self.parent.playpause_btn.width - self.parent.streamtype_btn.width - self.app.button_padding*2,
            self.parent.height
        )
    
    def render(self):
        progress_bar_rect = pygame.Rect(0, self.height/4, self.width, self.height/2)
        pygame.draw.rect(self.surface, self.empty_color, progress_bar_rect, border_radius=progress_bar_rect.height//2)
        progress = progress_bar_rect.copy()
        progress.width = int(min(
            (progress.width-progress.height) * (time.time()-self.app.data.get("now_playing").get("played_at")) / self.app.data.get("now_playing").get("duration") + progress.height,
            progress.width
        ))
        pygame.draw.rect(self.surface, self.color, progress, border_radius=min(progress.height, progress.width)//2)

class StreamTypeButton(surfaces.Cached, surfaces.Resizing, surfaces.TextButton):
    def __init__(self, parent: ControlsRow1):
        self.app: Main
        self.parent: ControlsRow1
        super().__init__(parent, parent.app.settings.get("button_color"), parent.app.stream_type, parent.app.settings.get("button_text_color"), parent.app.font)

    def onButtonClicked(self) -> None:
        self.app.stream_type = "hls" if self.app.stream_type == "mp3" else "mp3"
        self.text.text = self.app.stream_type
        self.redraw = True
        logging.debug(f"Stream Type: {self.app.stream_type}")

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width - self.parent.height*2 - self.parent.playpause_btn.width - self.app.button_padding,
            0,
            self.parent.height*2,
            self.parent.height
        )

class PlayPauseButton(surfaces.Cached, surfaces.Resizing, surfaces.ImageButton):
    def __init__(self, parent: ControlsRow1):
        self.parent: ControlsRow1
        self.app: Main
        super().__init__(parent, parent.app.settings.get("button_color"))
        playimage = pygame.image.load(os.path.join(self.app.data_dir, "unmute.png"))
        pauseimage = pygame.image.load(os.path.join(self.app.data_dir, "mute.png"))
        self.playimage = surfaces.Image(playimage.get_rect(), None, playimage)
        self.pauseimage = surfaces.Image(pauseimage.get_rect(), None, pauseimage)
        self.subsurface = self.playimage if self.app.playing else self.pauseimage

    def onButtonClicked(self) -> None:
        self.app.playing = not self.app.playing
        self.subsurface = self.playimage if self.app.playing else self.pauseimage
        self.redraw = True
        logging.debug(f"Playing: {self.app.playing}")

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width - self.parent.height,
            0,
            self.parent.height,
            self.parent.height
        )
    
class ControlsRow2(surfaces.Resizing):
    def __init__(self, parent: MainContainer):
        self.parent: MainContainer
        self.app: Main
        super().__init__(parent)
        self.time_info = TimeInfo(self)
        self.open_btn = OpenButton(self)
        self.like_btn = LikeButton(self)

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.app.content_padding,
            self.parent.title.height + self.parent.row1.height + self.app.button_padding + self.app.content_padding*2,
            self.parent.width - self.app.content_padding*2,
            self.app.controls_size
        )

class TimeInfo(surfaces.Resizing, surfaces.ScalingText):
    def __init__(self, parent: ControlsRow2):
        self.parent: ControlsRow2
        self.app: Main
        super().__init__(parent, "", parent.app.settings.get("font_color"), parent.app.font)

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            0,
            0,
            self.parent.parent.row1.progress.width/2,
            self.parent.height/2
        )
    
    def update(self) -> bool:
        currentplaytime = max(time.time()-self.app.data.get("now_playing").get("played_at"), 0)
        self.text = f"{int(currentplaytime//60)}:{int(currentplaytime%60):02} / {int(self.app.data.get("now_playing").get("duration")//60)}:{int(self.app.data.get("now_playing").get("duration")%60):02}"
        return super().update()

class LikeButton(surfaces.Cached, surfaces.Resizing, surfaces.ImageButton):
    def __init__(self, parent: ControlsRow2):
        self.parent: ControlsRow2
        self.app: Main
        super().__init__(parent, parent.app.settings.get("button_color"))
        notlikedimage = pygame.image.load(os.path.join(self.app.data_dir, "unliked.png"))
        likedimage = pygame.image.load(os.path.join(self.app.data_dir, "liked.png"))
        self.notlikedimage = surfaces.Image(notlikedimage.get_rect(), None, notlikedimage)
        self.likedimage = surfaces.Image(likedimage.get_rect(), None, likedimage)
        self.subsurface = self.likedimage if self.app.song_liked else self.notlikedimage

    def onButtonClicked(self) -> None:
        self.redraw = True

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width - self.parent.height - self.parent.open_btn.width - self.app.button_padding,
            0,
            self.parent.height,
            self.parent.height
        )
    
    def refresh(self):
        self.subsurface = self.likedimage if self.app.song_liked else self.notlikedimage
        self.redraw = True

class OpenButton(surfaces.Cached, surfaces.Resizing, surfaces.ImageButton):
    def __init__(self, parent: ControlsRow2):
        self.parent: ControlsRow2
        self.app: Main
        image = pygame.image.load(os.path.join(parent.app.data_dir, "open.png"))
        surface = surfaces.Image(image.get_rect(), None, image)
        super().__init__(parent, parent.app.settings.get("button_color"), surface)
        self.enabled = False
    
    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width - self.parent.height,
            0,
            self.parent.height,
            self.parent.height
        )
    
    def onButtonClicked(self) -> None:
        link = self.app.settings.get("open_link")%self.app.data.get("now_playing").get("song").get("custom_fields").get("songId")
        logging.info(f"Opening {link}")

class Main(surfaces.App):
    @helpers.log_critical
    def __init__(self) -> None:
        self.data: StationResponse

        logging.info("Initializing")

        self.data_dir: str = os.path.join(Path.home(), "neuro_21_station_player")
        self.working_dir: str = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        self.settings: Settings = Settings(os.path.join(self.data_dir, "settings_v2.json"), os.path.join(self.working_dir, "data", "default_settings_v2.json"), isGlobal=True)

        self.init_lock = Lock()
        self.init_lock.acquire()
        self.init_thread = Thread(target=self.init, daemon=True).start()

        pygame.font.init()
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 400)
        super().__init__(self.settings.get("size"), LoadingScreen)

        nkh.init()

        self.content_padding = self.surface.get_width()*self.settings.get("content_padding")
        self.controls_size = self.surface.get_width()*self.settings.get("controls_size")
        self.button_padding = self.surface.get_width()*self.settings.get("button_padding")
        self.playing = self.settings.get("autoplay")
        self.stream_type = self.settings.get("stream_type")
        self.data_reload_cooldown = 0
        self.data_reloaded = False
        self.image_reloaded = False
        self.song_liked = False
        self.initialized = False
        self._screen_lock = Lock()
        self._image_lock = Lock()

        self.raw_image: Image.Image
        self.converted_image = pygame.Surface((1, 1))
        self.blurred_image = pygame.Surface((1, 1))

        self.no_menu_screen = NoMenuScreen(self)
        self.main_screen = MainScreen(self)

        self.bg_image = BgImage(self.main_screen)
        self.init_lock.release()
        logging.info("Main thread init finished")

    @helpers.log_critical
    def init(self):
        self.data = None # We need to define it in order for it to not crash, is overwritten in refresh_data    # pyright: ignore[reportAttributeAccessIssue]
        if not self.refresh_data():
            self.data = fallbackData
        self.favourites = [x.get("songId") for x in nkh.get_favourites() if not x.get("songId", None) is None]
        logging.debug(self.favourites)
        self.initialized = True
        with self.init_lock:
            with self._screen_lock:
                self.main_screen.show()
            logging.info("Initialization Complete")

    def fetch_data(self) -> StationResponse:
        response = requests.get(self.settings.get("data_url"))
        response.raise_for_status()
        return json.loads(response.content)

    def fetch_image(self, url: str) -> BytesIO:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    
    @helpers.log_error
    def refresh_data(self) -> Literal[True]:
        """Refreshes the data from the station"""
        old_songid = self.data.get("now_playing").get("song").get("id") if self.data else None
        old_art = self.data.get("now_playing").get("song").get("art") if self.data else None
        self.data = self.fetch_data()
        if old_songid == self.data.get("now_playing").get("song").get("id"):
            return True
        self.data_reloaded = True
        if old_art != self.data.get("now_playing").get("song").get("art"):
            with self._image_lock:
                self.raw_image = Image.open(self.fetch_image(self.data.get("now_playing").get("song").get("art")))
        self.image_reloaded = True
        return True

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
            logging.debug("Image reload recieved")
            self.image_reloaded = False
            self.converted_image = pygame.image.frombytes(self.raw_image.tobytes(), self.raw_image.size, self.raw_image.mode).convert() # pyright: ignore[reportArgumentType]
            self.blurred_image = pygame.image.frombytes(ImageEnhance.Brightness(self.raw_image).enhance(self.settings.get("darken_factor")).filter(ImageFilter.GaussianBlur(self.settings.get("blur_scale"))).tobytes(), self.raw_image.size, self.raw_image.mode).convert() # pyright: ignore[reportArgumentType]
            self._image_lock.release()
            self.bg_image.redraw = True
            self.no_menu_screen.redraw = True
            self.main_screen.main_container.bg.redraw = True
        if self.data_reloaded:
            logging.debug("Data reload recieved")
            self.data_reloaded = False
            self.main_screen.main_container.title.redraw = True
            self.main_screen.main_container.row2.open_btn.enabled = bool(self.data.get("now_playing").get("song").get("custom_fields").get("songId"))
            self.song_liked = self.data.get("now_playing").get("song").get("custom_fields").get("songId") in self.favourites
            logging.debug(f"Song liked: {self.song_liked} (ID: {self.data.get("now_playing").get("song").get("custom_fields").get("songId")})")
            self.main_screen.main_container.row2.like_btn.refresh()
        if self.data.get("playing_next").get("played_at")+1 < time.time() and self.data_reload_cooldown < time.time():
            self.data_reload_cooldown = time.time() + 30 # If the thread crashed for some reason we will retry after 30 seconds
            Thread(target=self.reload_data_tick, daemon=True).start()

    @helpers.log_critical
    def run(self):
        super().run()

class MainResizeable(Main, surfaces.ResizeableApp):
    def onResize(self, size: tuple[int, int], width: int, height: int) -> None:
        self.content_padding = width*self.settings.get("content_padding")
        self.controls_size = self.surface.get_width()*self.settings.get("controls_size")
        self.button_padding = self.surface.get_width()*self.settings.get("button_padding")
        return super().onResize(size, width, height)

if __name__ == "__main__":
    helpers.setup_logging()
    app = MainResizeable() if "--resizeable" in sys.argv else Main()
    app.run()