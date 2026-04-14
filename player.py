# ----------------------------------------------------------------
# Imports
import json
import os
import pygame
import requests
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from typing import TypedDict, Optional, Literal

# ----------------------------------------------------------------
# Constants
CREATE_NO_WINDOW = 0x08000000

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
    player = subprocess.Popen([get_ffmpeg_path(), "-nodisp", "-loglevel", "quiet", url, "-af", f"volume={volume}"], creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)

def load_vars(data: dict, defaults: dict):
    for key in defaults:
        data[key] = data.get(key, defaults[key])
        globals()[key] = data[key]
    return data

def ensure_data_file(name: str):
    if not os.path.exists(os.path.join(data_dir, name)):
        shutil.copyfile(os.path.join(working_dir, "data", name), os.path.join(data_dir, name))

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
        size[1]/2 - ((scaled_title.get_height()+scaled_author.get_height())/2 + size[1]*content_padding*1.5) - controls_size*size[0],
        size[0]*(content_width + content_padding*2),
        scaled_title.get_height() + scaled_author.get_height() + size[1]*content_padding*3 + controls_size*size[0]*2)
    masksurf = pygame.Surface(size)
    masksurf.fill((0, 0, 0))
    pygame.draw.rect(masksurf, (255, 255, 255), text_rect, border_radius=round(max(size)*border_radius))
    background.blit(masksurf, (0, 0))
    mask = pygame.mask.from_threshold(masksurf, (255, 255, 255), (127, 127, 127, 127))
    background.fill((0, 0, 0))
    mask.to_surface(background, setsurface=blurred_image, unsetsurface=scaled_image)
    background.blit(scaled_title, (size[0]/2 - scaled_title.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 - controls_size*size[0] - size[1]*content_padding*0.5))
    background.blit(scaled_author, (size[0]/2 - scaled_author.get_width()/2, size[1]/2 - (scaled_title.get_height()+scaled_author.get_height())/2 + scaled_title.get_height() - controls_size*size[0] - size[1]*content_padding*0.5))
    row_1_rect.top = int(size[1]//2 + (scaled_title.get_height()+scaled_author.get_height())//2 - controls_size*size[0] + size[1]*content_padding*0.5)
    row_2_rect.top = int(size[1]//2 + (scaled_title.get_height()+scaled_author.get_height())//2 + size[1]*content_padding*0.5)

def reload_data() -> None:
    global data, image, loading, refresh_bg, image_url, error, data_loaded
    try:
        data = fetch_data()
        refresh_bg = True
        if not data_loaded or image_url != data["now_playing"]["song"]["art"]:
            image = Image.open(fetch_image(data["now_playing"]["song"]["art"])).resize(size)
            image_url = data["now_playing"]["song"]["art"]
            refresh_bg = True
        data_loaded = True
    except requests.RequestException as e:
        error = e.__class__.__name__
    finally:
        loading = False

def draw_row_1() -> pygame.Surface:
    surface = pygame.Surface(row_1_rect.size, pygame.SRCALPHA)
    pygame.draw.circle(surface, button_color, (surface.get_width()-surface.get_height()/2, surface.get_height()/2), surface.get_height()/2)
    surface.blit(unmute_icon if playing else mute_icon, (surface.get_width()-surface.get_height()*(1-(1-button_icon_size)/2), surface.get_height()*(1-button_icon_size)/2))
    mute_unmute_hitbox.left = int(surface.get_width()-surface.get_height()+row_1_rect.left)
    mute_unmute_hitbox.top = int(row_1_rect.top)
    pygame.draw.rect(surface, button_color, (surface.get_width()-surface.get_height()*(2+stream_type_button_scale), surface.get_height()*(1-stream_type_button_scale)/2, surface.get_height()*2*stream_type_button_scale, surface.get_height()*stream_type_button_scale), border_radius=int(surface.get_height()*stream_type_button_scale))
    stream_type_button_text = font.render(stream_type, False, button_font_color)
    scaled_stream_type_button_text = pygame.transform.scale_by(stream_type_button_text, min(stream_type_button_hitbox.width/stream_type_button_text.get_width(), stream_type_button_hitbox.height/stream_type_button_text.get_height())*button_text_size)
    surface.blit(scaled_stream_type_button_text, (surface.get_width()-2*surface.get_height()-scaled_stream_type_button_text.get_width()/2, surface.get_height()/2-scaled_stream_type_button_text.get_height()/2))
    stream_type_button_hitbox.left = int(surface.get_width()-surface.get_height()*(2+stream_type_button_scale)+row_1_rect.left)
    stream_type_button_hitbox.top = int(surface.get_height()*(1-stream_type_button_scale)/2+row_1_rect.top)
    progress_bar_rect = pygame.Rect((surface.get_width()-3*surface.get_height())/2-(surface.get_width()-3*surface.get_height())*progress_bar_size[0]/2, surface.get_height()/2-surface.get_height()*progress_bar_size[1]/2, (surface.get_width()-3*surface.get_height())*progress_bar_size[0], surface.get_height()*progress_bar_size[1])
    pygame.draw.rect(surface, progress_bar_color, progress_bar_rect, border_radius=progress_bar_rect.height//2)
    progress = progress_bar_rect.copy()
    progress.width = int(min((progress.width-progress.height) * (time.time()-data["now_playing"]["played_at"])/data["now_playing"]["duration"] + progress.height, progress.width))
    pygame.draw.rect(surface, button_color, progress, border_radius=min(progress.height, progress.width)//2)
    return surface

def draw_row_2() -> pygame.Surface:
    surface = pygame.Surface(row_2_rect.size, pygame.SRCALPHA)
    currentplaytime = max(time.time()-data["now_playing"]["played_at"], 0)
    timer = mono_font.render(f"{int(currentplaytime//60)}:{int(currentplaytime%60):02} / {int(data["now_playing"]['duration']//60)}:{int(data["now_playing"]['duration']%60):02}", False, font_color)
    scaled_timer = pygame.transform.scale_by(timer, surface.get_height()/timer.get_height()*timer_size)
    surface.blit(scaled_timer, (0, 0))
    pygame.draw.circle(surface, button_color, (surface.get_width()-surface.get_height()*(1+(1-stream_type_button_scale)/2), surface.get_height()/2), surface.get_height()/2)
    surface.blit(open_icon, (surface.get_width()-surface.get_height()*(1+(1-stream_type_button_scale)/2)-open_icon.get_width()/2, surface.get_height()*(1-button_icon_size)/2))
    open_hitbox.left = int(surface.get_width()-surface.get_height()*(1.5+(1-stream_type_button_scale)/2)+row_2_rect.left)
    open_hitbox.top = row_2_rect.top
    full_slider_width = surface.get_width()-surface.get_height()*(1+(1-stream_type_button_scale)/2)-open_icon.get_width()/2-scaled_timer.get_width()
    slider_hitbox.width = int(full_slider_width*slider_size)
    slider_hitbox.height = int(surface.get_height()*slider_size)
    slider_hitbox.left = int(scaled_timer.get_width()+full_slider_width/2-slider_hitbox.width/2)
    slider_hitbox.top = int(surface.get_height()/2-slider_hitbox.height/2)
    pygame.draw.rect(surface, progress_bar_color, (slider_hitbox.left, surface.get_height()*(1-slider_bar_size)/2, slider_hitbox.width, surface.get_height()*slider_bar_size), border_radius=int(surface.get_height()*slider_bar_size/2))
    pygame.draw.rect(surface, button_color, (slider_hitbox.left+slider_hitbox.width*volume-surface.get_height()*slider_bar_size/2, slider_hitbox.top, surface.get_height()*slider_bar_size, slider_hitbox.height), border_radius=int(surface.get_height()*slider_bar_size/2))
    slider_hitbox.left += row_2_rect.left
    slider_hitbox.top += row_2_rect.top
    return surface

def draw_error() -> pygame.Surface:
    surface = pygame.Surface(error_hitbox.size, pygame.SRCALPHA)
    pygame.draw.rect(surface, error_color, surface.get_rect(), border_top_left_radius=int(max(size)*border_radius), border_bottom_left_radius=int(max(size)*border_radius))
    surface.blit(error_icon, (content_padding*size[0], surface.get_height()/2-error_icon.get_height()/2))
    text = font.render(error, False, font_color)
    scaled_text = pygame.transform.scale_by(text, (surface.get_width()-2*content_padding*size[0]-error_icon.get_width())/text.get_width())
    surface.blit(scaled_text, (2*content_padding*size[0]+error_icon.get_width(), content_padding*size[1]))
    reload_text = font.render("Click to Reload", False, font_color)
    scaled_reload_text = pygame.transform.scale_by(reload_text, (surface.get_width()-2*content_padding*size[0]-error_icon.get_width())/reload_text.get_width())
    surface.blit(scaled_reload_text, (2*content_padding*size[0]+error_icon.get_width(), surface.get_height()-content_padding*size[1]-scaled_reload_text.get_height()))
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
button_text_size: float = 0
mono_font_name: str = ""
timer_size: float = 0
open_link: str = ""
slider_size: float = 0
slider_bar_size: float = 0
error_color: tuple[int, int, int] = (0, 0, 0)
error_pos: tuple[float, float] = (0, 0)
error_relative_height: float = 0
error_icon_scale: float = 0
reload_cooldown: int = 0

# ----------------------------------------------------------------
# Fallback Station Data
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
                "artist": "???",
                "custom_fields": {},
                "genre": "",
                "id": "",
                "isrc": "",
                "lyrics": "",
                "text": "",
                "title": "???"
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
                "artist": "???",
                "custom_fields": {},
                "genre": "",
                "id": "",
                "isrc": "",
                "lyrics": "",
                "text": "",
                "title": "???"
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

# ----------------------------------------------------------------
# Main
working_dir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
data_dir = os.path.join(Path.home(), "neuro_21_station_player")
settings_file_path = os.path.join(data_dir, "settings.json")
if not os.path.exists(data_dir):
    os.mkdir(data_dir)
if not os.path.exists(settings_file_path):
    shutil.copyfile(os.path.join(working_dir, "data", "default_settings.json"), settings_file_path)
for filename in ["mute.png", "unmute.png", "open.png", "error.png"]:
    ensure_data_file(filename)
with open(settings_file_path, "r") as f:
    with open(os.path.join(working_dir, "data", "default_settings.json"), "r") as f2:
        loaded_vars = load_vars(json.load(f), json.load(f2))
with open(settings_file_path, "w") as f:
    json.dump(loaded_vars, f, indent=4, sort_keys=True)
pygame.font.init()
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Neuro 21 Station Player - Loading")
font = pygame.font.SysFont(pygame.font.get_default_font(), font_quality)
screen.fill((0, 0, 0))
loadingText = font.render("Loading...", False, (255, 255, 255))
scaledLoadingText = pygame.transform.scale_by(loadingText, screen.get_width()/loadingText.get_width()/2)
screen.blit(scaledLoadingText, (screen.get_width()/2-scaledLoadingText.get_width()/2, screen.get_height()/2-scaledLoadingText.get_height()/2))
pygame.display.flip()
mono_font = pygame.font.SysFont(mono_font_name, font_quality)
clock = pygame.time.Clock()
background = pygame.Surface(size)
row_1_rect = pygame.Rect(size[0]*(1-content_width)/2, 0, size[0]*content_width, size[0]*controls_size)
row_2_rect = pygame.Rect(size[0]*(1-content_width)/2, 0, size[0]*content_width, size[0]*controls_size)
mute_unmute_hitbox = pygame.Rect(0, 0, size[0]*controls_size, size[0]*controls_size)
stream_type_button_hitbox = pygame.Rect(0, 0, size[0]*controls_size*2*stream_type_button_scale, size[0]*controls_size*stream_type_button_scale)
open_hitbox = pygame.Rect(0, 0, size[0]*controls_size, size[0]*controls_size)
slider_hitbox = pygame.Rect(0, 0, 0, 0)
error_hitbox = pygame.Rect(error_pos[0]*size[0], error_pos[1]*size[1], (1-error_pos[0])*size[0], (1-error_pos[0])*size[0]*error_relative_height)
mute_icon = pygame.transform.smoothscale(pygame.image.load(os.path.join(data_dir, "mute.png")), (size[0]*controls_size*button_icon_size, size[0]*controls_size*button_icon_size))
unmute_icon = pygame.transform.smoothscale(pygame.image.load(os.path.join(data_dir, "unmute.png")), (size[0]*controls_size*button_icon_size, size[0]*controls_size*button_icon_size))
open_icon = pygame.transform.smoothscale(pygame.image.load(os.path.join(data_dir, "open.png")), (size[0]*controls_size*button_icon_size, size[0]*controls_size*button_icon_size))
error_icon = pygame.transform.smoothscale(pygame.image.load(os.path.join(data_dir, "error.png")), ((1-error_pos[0])*size[0]*error_relative_height*error_icon_scale, (1-error_pos[0])*size[0]*error_relative_height*error_icon_scale))
window_icon = pygame.image.load(os.path.join(working_dir, "data", "icon.ico"))
pygame.display.set_icon(window_icon)
image_url = ""
loading = False
refresh_bg = False
running = True
player = None
noMenu = False
slider_selected = False
error = None
data_loaded = False
data: StationResponse = fallbackData

reload_cooldown_until = time.time() + 5
reload_data()

if playing:
    play_stream()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            noMenu = not noMenu
        elif noMenu and event.type == pygame.MOUSEBUTTONDOWN:
            noMenu = False
        elif error and event.type == pygame.MOUSEBUTTONDOWN and error_hitbox.collidepoint(event.pos):
            error = None
            loading = True
            reload_cooldown_until = time.time() + 5
            threading.Thread(target=reload_data).start()
        elif not noMenu:
            if (event.type == pygame.MOUSEBUTTONDOWN and mute_unmute_hitbox.collidepoint(event.pos)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                playing = not playing
                if playing:
                    play_stream()
                else:
                    stop_player()
            elif event.type == pygame.MOUSEBUTTONDOWN and stream_type_button_hitbox.collidepoint(event.pos):
                if stream_type == "hls":
                    stream_type = "mp3"
                else:
                    stream_type = "hls"
                stop_player()
                if playing:
                    play_stream()
            elif event.type == pygame.MOUSEBUTTONDOWN and open_hitbox.collidepoint(event.pos):
                webbrowser.open(open_link%(data["now_playing"]["song"]["custom_fields"]["songId"]))
            elif slider_selected and event.type == pygame.MOUSEMOTION:
                volume = min(1, max(0, (event.pos[0]-slider_hitbox.left)/slider_hitbox.width))
            elif event.type == pygame.MOUSEBUTTONDOWN and slider_hitbox.collidepoint(event.pos):
                slider_selected = True
            elif slider_selected and event.type == pygame.MOUSEBUTTONUP:
                slider_selected = False
                stop_player()
                if playing:
                    play_stream()

    mouse_pos = pygame.mouse.get_pos()
    if (mute_unmute_hitbox.collidepoint(mouse_pos) or stream_type_button_hitbox.collidepoint(mouse_pos) or open_hitbox.collidepoint(mouse_pos) or slider_hitbox.collidepoint(mouse_pos) or (error and error_hitbox.collidepoint(mouse_pos))) and not noMenu:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    
    if data["playing_next"]["played_at"]+1 < time.time() and not loading and reload_cooldown_until < time.time() and not error:
        loading = True
        reload_cooldown_until = time.time() + 5
        threading.Thread(target=reload_data).start()

    if data_loaded:
        if refresh_bg:
            refresh_bg = False
            draw_bg(data)
            pygame.display.set_caption(f"{data["station"]["name"]} - {data["now_playing"]["song"]["title"]}")
    
        if noMenu:
            screen.fill((0, 0, 0))
            screen.blit(scaled_image, (0, 0))
        else:
            screen.blit(background, (0, 0))
            screen.blit(draw_row_1(), row_1_rect)
            screen.blit(draw_row_2(), row_2_rect)
    if error:
        screen.blit(draw_error(), error_hitbox)

    clock.tick(fps)
    pygame.display.flip()

pygame.quit()
stop_player()