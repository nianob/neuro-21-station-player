from __future__ import annotations
import json
import logging
import os
import pygame
import requests
import shutil
import subprocess
import sys
import time
import webbrowser

from io import BytesIO
from niatools.storage import ThreadingStorage
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from pygame.font import Font
from threading import Thread, Lock
from types import NoneType
from typing import Any, Optional, Literal, NoReturn

import helpers
import neurokaraoke_hook as nkh
import surfaces
from customtypes import StationResponse

CREATE_NO_WINDOW = 0x08000000

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

# --------------------------------
# Classes relevant to playback
class Player:
    def __init__(self, app: Main, url: str, volume: float) -> None:
        self.app = app
        self.url = url
        self._playing = False
        self._player = None
        self._volume = volume

    @property
    def executeable_path(self) -> str:
        return os.path.join(app.working_dir, "ffmpeg", "windows" if os.name == "nt" else "linux", f"ffplay{".exe" if os.name == "nt" else ""}")

    def start(self):
        if self._player:
            raise RuntimeError("The player is already running")
        self._player = subprocess.Popen([self.executeable_path, "-nodisp", "-loglevel", "quiet", self.url, "-af", f"volume={self.volume}"], creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)

    def stop(self):
        if self._player and self._player.poll() is None:
            self._player.terminate()
            try:
                self._player.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._player.kill()
        self._player = None
    
    def restart(self):
        self.stop()
        self.start()

    @property
    def is_playing(self) -> bool:
        return bool(self._player)
    
    @property
    def volume(self) -> float:
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        self._volume = value
        if self.is_playing:
            self.restart()

# --------------------------------
# Surface Classes
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

        player_running = self.app.selected_player.is_playing
        if player_running:
            self.app.selected_player.stop()
        self.app.selected_player = self.app.mp3_player if self.app.stream_type == "mp3" else self.app.hls_player
        self.app.selected_player.volume = self.app.main_screen.main_container.row2.volume_slider.value
        if player_running:
            self.app.selected_player.start()

        self.redraw = True
        logging.info(f"Stream type set to {self.app.stream_type}")

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
        # the subsurface wll be replaced when the player object is loaded

    def onButtonClicked(self) -> None:
        self.app.selected_player.stop() if self.app.selected_player.is_playing else self.app.selected_player.start()
        self.subsurface = self.playimage if self.app.selected_player.is_playing else self.pauseimage
        self.redraw = True
        if self.app.selected_player.is_playing:
            logging.info("Playback resumed")
        else:
            logging.info("Playback paused")

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.width - self.parent.height,
            0,
            self.parent.height,
            self.parent.height
        )
    
    def set_playing(self):
        self.subsurface = self.playimage if self.app.selected_player.is_playing else self.pauseimage
    
class ControlsRow2(surfaces.Resizing):
    def __init__(self, parent: MainContainer):
        self.parent: MainContainer
        self.app: Main
        super().__init__(parent)
        self.time_info = TimeInfo(self)
        self.open_btn = OpenButton(self)
        self.like_btn = LikeButton(self)
        self.volume_slider = VolumeSlider(self)

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

class VolumeSlider(surfaces.Cached, surfaces.Resizing):
    CURSOR = pygame.SYSTEM_CURSOR_HAND

    def __init__(self, parent: ControlsRow2):
        self.parent: ControlsRow2
        self.app: Main
        super().__init__(parent)
        self.value = self.app.settings.get("volume")
        self.bar_color = self.app.settings.get("progress_bar_color")
        self.selector_color = self.app.settings.get("button_color")
        self._listener_added = False
        self._clicked = False

    def render(self):
        bar_rect = pygame.Rect(0, self.height*4/10, self.width, self.height/5)
        pygame.draw.rect(self.surface, self.bar_color, bar_rect, border_radius=self.height//10)
        selector_rect = pygame.Rect(self.value*(self.width-self.height/5), 0, self.height/5, self.height)
        pygame.draw.rect(self.surface, self.selector_color, selector_rect, border_radius=self.height//10)
    
    def update(self) -> bool:
        self.redraw = self.redraw or self._clicked
        if not self._listener_added:
            self._listener_added = True
            self.app.main_screen.addEventHandler(self.eventHandler) # The listener must be added delayed to avoid a crash
        return super().update()
    
    def eventHandler(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.collide(*event.pos):
                self._clicked = True
            elif event.type == pygame.MOUSEMOTION and self._clicked:
                x = (event.pos[0] - self.x) / self.width
                self.value = min(1, max(0, x))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._clicked = False
                self.app.selected_player.volume = self.value

    def getRect(self) -> pygame.Rect:
        return pygame.Rect(
            self.parent.time_info.width + self.app.button_padding,
            0,
            self.parent.like_btn.rect.x - self.parent.time_info.width - self.app.button_padding*2,
            self.parent.height
        )

class LikeButton(surfaces.Cached, surfaces.Resizing, surfaces.ImageButton):
    CURSOR = pygame.SYSTEM_CURSOR_NO

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
        webbrowser.open(link)
        logging.info(f"Opening {link}")

# --------------------------------
# Main App

def cleanup(ret: NoneType, self: Main) -> NoReturn:
    if not self.__dict__.get("selected_player") is None:
        self.selected_player.stop()
        self.settings.save()
    del self
    sys.exit()

class Main(surfaces.App):
    @helpers.log_critical
    def __init__(self) -> None:
        self.data: StationResponse

        logging.info("Initializing")

        self.data_dir: str = os.path.join(Path.home(), "neuro_21_station_player")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.working_dir: str = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        self.settings: ThreadingStorage = ThreadingStorage(os.path.join(self.data_dir, "settings_v2.json"), os.path.join(self.working_dir, "data", "default_settings_v2.json"), autosave_interval=1800, total=True)

        logging.debug(f"Settings: {self.settings._storage}")

        self.nkh_login_lock = Lock()
        self.login_nkh = False
        self.init_lock = Lock()
        self.init_lock.acquire()
        self.init_thread = Thread(target=self.init, daemon=True).start()

        pygame.font.init()
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 400)
        super().__init__(self.settings.get("size"), LoadingScreen)

        self.initialized = False
        self._screen_lock = Lock()
        self._image_lock = Lock()

        self.raw_image: Image.Image

        self.init_lock.release()
        logging.info("Main thread init finished")

    @helpers.log_critical
    def init(self):
        nkh.init(self.settings, autologin=False)

        if not nkh.logged_in:
            self.nkh_login_lock.acquire()
            self.login_nkh = True

        self.data_reload_cooldown = 0
        self.data_reloaded = False
        self.image_reloaded = False
        self.song_liked = False

        # Load Data
        self.data = None # We need to define it in order for it to not crash, is overwritten in refresh_data    # pyright: ignore[reportAttributeAccessIssue]
        if not self.refresh_data(fully_initialized=False):
            self.data = fallbackData

        # Load Favourites
        with self.nkh_login_lock:
            self.favourites = [x.get("songId") for x in nkh.get_favourites() if not x.get("songId", None) is None]
            logging.debug(f"All liked songs: {self.favourites}")

        # Copy Required Files
        for name in ["mute.png", "unmute.png", "open.png", "liked.png", "unliked.png"]:
            if not os.path.exists(os.path.join(self.data_dir, name)):
                shutil.copyfile(os.path.join(self.working_dir, "data", name), os.path.join(self.data_dir, name))

        # variables
        self.content_padding = self.surface.get_width()*self.settings.get("content_padding")
        self.controls_size = self.surface.get_width()*self.settings.get("controls_size")
        self.button_padding = self.surface.get_width()*self.settings.get("button_padding")
        self.stream_type = self.settings.get("stream_type")

        # Surfaces
        self.converted_image = pygame.Surface((1, 1))
        self.blurred_image = pygame.Surface((1, 1))
        self.no_menu_screen = NoMenuScreen(self)
        self.main_screen = MainScreen(self)
        self.bg_image = BgImage(self.main_screen)

        # Load Players
        self.mp3_player = Player(self, self.data.get("station").get("listen_url"), self.main_screen.main_container.row2.volume_slider.value)
        self.hls_player = Player(self, self.data.get("station").get("hls_url"), self.main_screen.main_container.row2.volume_slider.value)
        self.selected_player = self.mp3_player if self.stream_type == "mp3" else self.hls_player
        if self.settings.get("autoplay"):
            self.selected_player.start()
        self.main_screen.main_container.row1.playpause_btn.set_playing() # set the proper symbol on the play/pause button

        # Finish init
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
    def refresh_data(self, fully_initialized: bool = True) -> Literal[True]:
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
        if fully_initialized and self.selected_player.is_playing:
            nkh.send_playcount(str(self.data.get("now_playing").get("song").get("custom_fields").get("songId")))
            logging.debug("Playcount request sent!")
        return True

    def reload_data_tick(self):
        """Refreshes the data from the station, should be used in the tick loop as it resets the reloading flag"""
        self.refresh_data()
        self.data_reload_cooldown = time.time() + 5 # Only try to reload every 5 seconds if unsuccessful

    def tick(self):
        with self._screen_lock:
            super().tick()
        if not self.initialized:
            if self.login_nkh:
                self.login_nkh = False
                nkh.login()
                self.nkh_login_lock.release()
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

    @helpers.cleanup(cleanup)
    @helpers.log_critical
    def run(self):
        super().run()
    
    @helpers.cleanup(cleanup)
    def quit(self):
        pygame.quit()

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
