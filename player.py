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
import subprocess
import sys
import threading
import time

from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from typing import TypedDict, Optional

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
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, "ffmpeg", "windows" if os.name == "nt" else "linux", f"ffplay{".exe" if os.name == "nt" else ""}")

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

# ----------------------------------------------------------------
# Get & Process Data
def fetch_data() -> StationResponse:
    response = requests.get("https://radio.twinskaraoke.com/api/nowplaying_static/neuro_21.json")
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
        size[1]/2 - ((scaled_title.get_height()+scaled_author.get_height())/2 + size[1]*content_padding) - controls_size*size[0]/2,
        size[0]*(content_width + content_padding*2),
        scaled_title.get_height() + scaled_author.get_height() + size[1]*content_padding*2 + controls_size*size[0])
    masksurf = pygame.Surface(size)
    masksurf.fill((0, 0, 0))
    pygame.draw.rect(masksurf, (255, 255, 255), text_rect, border_radius=round(max(size)*border_radius))
    background.blit(masksurf, (0, 0))
    mask = pygame.mask.from_threshold(masksurf, (255, 255, 255), (127, 127, 127, 127))
    background.fill((0, 0, 0))
    mask.to_surface(background, setsurface=blurred_image, unsetsurface=scaled_image)
    background.blit(scaled_title, (size[0]/2 - scaled_title.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 - controls_size*size[0]/2))
    background.blit(scaled_author, (size[0]/2 - scaled_author.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 + scaled_title.get_height() - controls_size*size[0]/2))
    controls_rect.top = int(size[1]//2 + (scaled_title.get_height()+scaled_author.get_height())//2 - controls_size*size[0]//2)

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
    return surface

# ----------------------------------------------------------------
# Settings
size = (900, 900)
fps = 60
content_width = 0.7
content_padding = 0.03
border_radius = 0.05
author_scale = 0.65
blur_scale = 10
darken_factor = 0.75
controls_size = 0.075
button_color = (134, 215, 247, 170)
mute_icon_bin = b'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'
unmute_icon_bin = b'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'
button_icon_size = 0.5
font_quality = 150
font_color = (255, 255, 255)
button_font_color = (0, 0, 0)
volume = 0.1
stream_type = "mp3"
stream_type_button_scale = 0.8
playing = True


# ----------------------------------------------------------------
# Main
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