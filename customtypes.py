from __future__ import annotations
from typing import TypedDict, Optional

__all__ = ["Coordinate", "Color", "Colors", "StationResponse"]

type percent = float # from 0 to 1
type Byte = int # from 0 to 255
type Color = tuple[Byte, Byte, Byte] # A pygame color
type Colora = tuple[Byte, Byte, Byte, Byte] # A pygame color with alpha
type percent_vector = tuple[percent, percent] # A Vecor defining a size or position
type Coordinate = tuple[int, int] # A coordinate defining a size or position

class Colors:
    BLACK: Color = (0, 0, 0)
    BLUE: Color = (0, 0, 255)
    GREEN: Color = (0, 255, 0)
    CYAN: Color = (0, 255, 255)
    RED: Color = (255, 0, 0)
    PINK: Color = (255, 0, 255)
    YELLOW: Color = (255, 255, 0)
    WHITE: Color = (255, 255, 255)

class _Station:
    class Listeners(TypedDict):
        total: int
        unique: int
        current: int

    class Mount(TypedDict):
        id: int
        name: str
        url: str
        bitrate: int
        format: str
        listeners: _Station.Listeners
        path: str
        is_default: bool

    class Info(TypedDict):
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
        mounts: list[_Station.Mount]
        remotes: list[dict]
        hls_enabled: bool
        hls_is_default: bool
        hls_url: str
        hls_listeners: int

    class LiveInfo(TypedDict):
        is_live: bool
        streamer_name: str
        broadcast_start: Optional[int]
        art: Optional[str]

    class Song(TypedDict):
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

    class NowPlaying(TypedDict):
        sh_id: int
        played_at: int
        duration: int
        playlist: str
        streamer: str
        is_request: bool
        song: _Station.Song
        elapsed: int
        remaining: int

    class NextPlaying(TypedDict):
        cued_at: int
        played_at: int
        duration: float
        playlist: str
        is_request: bool
        song: _Station.Song

    class Response(TypedDict):
        station: _Station.Info
        listeners: _Station.Listeners
        live: _Station.LiveInfo
        now_playing: _Station.NowPlaying
        playing_next: _Station.NextPlaying
        song_history: list[_Station.Song]
        is_online: bool
        cache: str

StationResponse = _Station.Response