"""Displays the infos about the Neuro 21 Station

Args:
    --size:
        the size of the Window. Defaults to 900x900.
    --fps:
        the Refresh Rate. Defaults to 10.
    --help:
        displays this menu.
"""

# ----------------------------------------------------------------
# Imports

import base64
import json
import os
import pygame
import requests
import shutil
import subprocess
import sys
import threading
import time

from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from typing import TypedDict, Optional, Literal

# ----------------------------------------------------------------
# Types
class StationListeners(TypedDict):
    total: int
    unique: int
    current: int

class StationMount(TypedDict):
    id: int
    name: str
    url: str
    bitrate: int
    format: str
    listeners: StationListeners
    path: str
    is_default: bool

class StationInfo(TypedDict):
    id: int
    name: str
    shortcode: str
    description: str
    frontend: str
    backend: str
    timezone: str
    listen_url: str
    url: str
    public_player_url: str
    playlist_pls_url: str
    playlist_m3u_url: str
    is_public: bool
    requests_enabled: bool
    mounts: list[StationMount]
    remotes: list[dict]
    hls_enabled: bool
    hls_is_default: bool
    hls_url: str
    hls_listeners: int

class StationLiveInfo(TypedDict):
    is_live: bool
    streamer_name: str
    broadcast_start: Optional[int]
    art: Optional[str]

class StationSong(TypedDict):
    id: str
    art: str
    custom_fields: dict
    text: str
    artist: str
    title: str
    album: str
    genre: str
    isrc: str
    lyrics: str

class StationNowPlaying(TypedDict):
    sh_id: int
    played_at: int
    duration: int
    playlist: str
    streamer: str
    is_request: bool
    song: StationSong
    elapsed: int
    remaining: int

class StationNextPlaying(TypedDict):
    cued_at: int
    played_at: int
    duration: float
    playlist: str
    is_request: bool
    song: StationSong

class StationResponse(TypedDict):
    station: StationInfo
    listeners: StationListeners
    live: StationLiveInfo
    now_playing: StationNowPlaying
    playing_next: StationNextPlaying
    song_history: list[StationSong]
    is_online: bool
    cache: str

# ----------------------------------------------------------------
# General Functions
def get_ffmpeg_path():
    return os.path.join(working_dir, "ffmpeg", "windows" if os.name == "nt" else "linux", f"ffplay{".exe" if os.name == "nt" else ""}")

def stop_player():
    global player
    if player and player.poll() is None:
        player.terminate()
        try:
            player.wait(timeout=2)
        except subprocess.TimeoutExpired:
            player.kill()
    player = None

def play_stream():
    global player
    url = data["station"]["hls_url"] if stream_type == "hls" else data["station"]["listen_url"]
    player = subprocess.Popen([get_ffmpeg_path(), "-nodisp", "-loglevel", "quiet", url, "-af", f"volume={volume}"])

def load_vars(data: dict):
    global size, fps, content_width, content_padding, border_radius, author_scale, blur_scale, darken_factor, controls_size, button_color
    global mute_icon_bin, unmute_icon_bin, button_icon_size, font_quality, font_color, button_font_color, volume, stream_type
    global stream_type_button_scale, playing, data_url, progress_bar_size, progress_bar_color
    size = data["size"]
    fps = data["fps"]
    content_width = data["content_width"]
    content_padding = data["content_padding"]
    border_radius = data["border_radius"]
    author_scale = data["author_scale"]
    blur_scale = data["blur_scale"]
    darken_factor = data["darken_factor"]
    controls_size = data["controls_size"]
    button_color = data["button_color"]
    mute_icon_bin = data["mute_icon_bin"]
    unmute_icon_bin = data["unmute_icon_bin"]
    button_icon_size = data["button_icon_size"]
    font_quality = data["font_quality"]
    font_color = data["font_color"]
    button_font_color = data["button_font_color"]
    volume = data["volume"]
    stream_type = data["stream_type"]
    stream_type_button_scale = data["stream_type_button_scale"]
    playing = data["playing"]
    data_url = data["data_url"]
    progress_bar_size = data["progress_bar_size"]
    progress_bar_color = data["progress_bar_color"]


# ----------------------------------------------------------------
# Get & Process Data
def fetch_data() -> StationResponse:
    response = requests.get(data_url)
    response.raise_for_status()
    return json.loads(response.content)

def fetch_image(url: str) -> BytesIO:
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

# ----------------------------------------------------------------
# Render functions

def draw_bg(data: StationResponse) -> None:
    global scaled_image
    scaled_image = pygame.image.frombytes(image.tobytes(), image.size, image.mode).convert() # type: ignore
    blurred_image = pygame.image.frombytes(ImageEnhance.Brightness(image).enhance(darken_factor).filter(ImageFilter.GaussianBlur(blur_scale)).tobytes(), image.size, image.mode).convert() # type: ignore
    title = font.render(data["now_playing"]["song"]["title"], False, font_color)
    author = font.render(data["now_playing"]["song"]["artist"], False, font_color)
    title_scale_factor = size[0]/max(title.get_width(), author.get_width()*author_scale)*content_width
    scaled_title = pygame.transform.scale_by(title, title_scale_factor)
    scaled_author = pygame.transform.scale_by(author, title_scale_factor*author_scale)
    text_rect = pygame.Rect(
        size[0]*(1-(content_width + content_padding*2))/2,
        size[1]/2 - ((scaled_title.get_height()+scaled_author.get_height())/2 + size[1]*content_padding*1.5) - controls_size*size[0]/2,
        size[0]*(content_width + content_padding*2),
        scaled_title.get_height() + scaled_author.get_height() + size[1]*content_padding*3 + controls_size*size[0])
    masksurf = pygame.Surface(size)
    masksurf.fill((0, 0, 0))
    pygame.draw.rect(masksurf, (255, 255, 255), text_rect, border_radius=round(max(size)*border_radius))
    background.blit(masksurf, (0, 0))
    mask = pygame.mask.from_threshold(masksurf, (255, 255, 255), (127, 127, 127, 127))
    background.fill((0, 0, 0))
    mask.to_surface(background, setsurface=blurred_image, unsetsurface=scaled_image)
    background.blit(scaled_title, (size[0]/2 - scaled_title.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 - controls_size*size[0]/2 - size[1]*content_padding*0.5))
    background.blit(scaled_author, (size[0]/2 - scaled_author.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 + scaled_title.get_height() - controls_size*size[0]/2 - size[1]*content_padding*0.5))
    controls_rect.top = int(size[1]//2 + (scaled_title.get_height()+scaled_author.get_height())//2 - controls_size*size[0]//2 + size[1]*content_padding*0.5)

def reload_data() -> None:
    global data, image, loading, refresh_bg, image_url
    data = fetch_data()
    refresh_bg = True
    if image_url != data["now_playing"]["song"]["art"]:
        image = Image.open(fetch_image(data["now_playing"]["song"]["art"])).resize(size)
        image_url = data["now_playing"]["song"]["art"]
    refresh_bg = True
    loading = False

def draw_fg() -> pygame.Surface:
    global mute_unmute_hitbox
    surface = pygame.Surface(controls_rect.size, pygame.SRCALPHA)
    pygame.draw.circle(surface, button_color, (surface.get_width()-surface.get_height()/2, surface.get_height()/2), surface.get_height()/2)
    surface.blit(unmute_icon if playing else mute_icon, (surface.get_width()-surface.get_height()*(1-(1-button_icon_size)/2), surface.get_height()*(1-button_icon_size)/2))
    mute_unmute_hitbox.left = int(surface.get_width()-surface.get_height()+controls_rect.left)
    mute_unmute_hitbox.top = int(controls_rect.top)
    pygame.draw.rect(surface, button_color, (surface.get_width()-surface.get_height()*(2+stream_type_button_scale), surface.get_height()*(1-stream_type_button_scale)/2, surface.get_height()*2*stream_type_button_scale, surface.get_height()*stream_type_button_scale), border_radius=int(surface.get_height()*stream_type_button_scale))
    stream_type_button_text = font.render(stream_type, False, button_font_color)
    scaled_stream_type_button_text = pygame.transform.scale_by(stream_type_button_text, min(stream_type_button_hitbox.width/stream_type_button_text.get_width(), stream_type_button_hitbox.height/stream_type_button_text.get_height())*button_icon_size)
    surface.blit(scaled_stream_type_button_text, (surface.get_width()-2*surface.get_height()-scaled_stream_type_button_text.get_width()/2, surface.get_height()/2-scaled_stream_type_button_text.get_height()/2))
    stream_type_button_hitbox.left = int(surface.get_width()-surface.get_height()*(2+stream_type_button_scale)+controls_rect.left)
    stream_type_button_hitbox.top = int(surface.get_height()*(1-stream_type_button_scale)/2+controls_rect.top)
    progress_bar_rect = pygame.Rect((surface.get_width()-3*surface.get_height())/2-(surface.get_width()-3*surface.get_height())*progress_bar_size[0]/2, surface.get_height()/2-surface.get_height()*progress_bar_size[1]/2, (surface.get_width()-3*surface.get_height())*progress_bar_size[0], surface.get_height()*progress_bar_size[1])
    pygame.draw.rect(surface, progress_bar_color, progress_bar_rect, border_radius=progress_bar_rect.height//2)
    progress = progress_bar_rect.copy()
    progress.width = int(min(progress.width * (time.time()-data["now_playing"]["played_at"])/data["now_playing"]["duration"], progress.height))
    pygame.draw.rect(surface, button_color, progress, border_radius=min(progress.height, progress.width)//2)
    return surface

# ----------------------------------------------------------------
# Settings, are all overwritten by settingsfike, so everything is 0 here
size: tuple[int, int] = (0, 0)
fps: int = 0
content_width: float = 0
content_padding: float = 0
border_radius: float = 0
author_scale: float = 0
blur_scale: int = 0
darken_factor: float = 0
controls_size: float = 0
button_color: tuple[int, int, int, int] = (0, 0, 0, 0)
mute_icon_bin: str = ""
unmute_icon_bin: str = ""
button_icon_size: float = 0
font_quality: int = 0
font_color: tuple[int, int, int] = (0, 0, 0)
button_font_color: tuple[int, int, int] = (0, 0, 0)
volume: float = 0
stream_type: Literal["mp3", "hls"] = "mp3"
stream_type_button_scale: float = 0
playing: bool = False
data_url: str = ""
progress_bar_size: tuple[float, float] = (0, 0)
progress_bar_color: tuple[int, int, int, int] = (0, 0, 0, 0)

# ----------------------------------------------------------------
# Main
working_dir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
data_dir = os.path.join(Path.home(), "neuro_21_station_player")
settings_file_path = os.path.join(data_dir, "settings.json")
if not os.path.exists(data_dir):
    os.mkdir(data_dir)
if not os.path.exists(settings_file_path):
    shutil.copyfile(os.path.join(working_dir, "data", "default_settings.json"), settings_file_path)
with open(settings_file_path, "r") as f:
    load_vars(json.load(f))
pygame.font.init()
screen = pygame.display.set_mode(size)
font = pygame.font.SysFont(pygame.font.get_default_font(), font_quality)
clock = pygame.time.Clock()
background = pygame.Surface(size)
controls_rect = pygame.Rect(size[0]*(1-content_width)/2, 0, size[0]*content_width, size[0]*controls_size)
mute_unmute_hitbox = pygame.Rect(0, 0, size[0]*controls_size, size[0]*controls_size)
stream_type_button_hitbox = pygame.Rect(0, 0, size[0]*controls_size*2, size[0]*controls_size)
mute_icon = pygame.transform.smoothscale(pygame.image.load(BytesIO(base64.b64decode(mute_icon_bin))), (size[0]*controls_size*button_icon_size, size[0]*controls_size*button_icon_size))
unmute_icon = pygame.transform.smoothscale(pygame.image.load(BytesIO(base64.b64decode(unmute_icon_bin))), (size[0]*controls_size*button_icon_size, size[0]*controls_size*button_icon_size))
image_url = ""
loading = False
refresh_bg = False
running = True
player = None
noMenu = False

reload_cooldown_until = time.time() + 5
reload_data()
if playing:
    play_stream()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            noMenu = not noMenu
        if noMenu and event.type == pygame.MOUSEBUTTONDOWN:
            noMenu = False
        if not noMenu:
            if (event.type == pygame.MOUSEBUTTONDOWN and mute_unmute_hitbox.collidepoint(event.pos)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                playing = not playing
                if playing:
                    play_stream()
                else:
                    stop_player()
            if event.type == pygame.MOUSEBUTTONDOWN and stream_type_button_hitbox.collidepoint(event.pos):
                if stream_type == "hls":
                    stream_type = "mp3"
                else:
                    stream_type = "hls"
                stop_player()
                if playing:
                    play_stream()

    mouse_pos = pygame.mouse.get_pos()
    if (mute_unmute_hitbox.collidepoint(mouse_pos) or stream_type_button_hitbox.collidepoint(mouse_pos)) and not noMenu:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    
    if data["playing_next"]["played_at"]+1 < time.time() and not loading and reload_cooldown_until < time.time():
        loading = True
        reload_cooldown_until = time.time() + 5
        threading.Thread(target=reload_data).start()
    if refresh_bg:
        refresh_bg = False
        draw_bg(data)
        pygame.display.set_caption(f"{data["station"]["name"]} - {data["now_playing"]["song"]["title"]}")
    
    if noMenu:
        screen.fill((0, 0, 0))
        screen.blit(scaled_image, (0, 0))
    else:
        screen.blit(background, (0, 0))
        screen.blit(draw_fg(), controls_rect)

    clock.tick(fps)
    pygame.display.flip()

pygame.quit()
stop_player()