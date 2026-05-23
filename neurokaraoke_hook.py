import regex
import requests
import webview

from threading import Lock
from typing import Any
from niatools.storage import StorageBase

# --------------------------------------------------------------------------------
# Internals
settings: StorageBase
_settings_lock = Lock()
_settings_lock.acquire()
logged_in: bool = False

# --------------------------------------------------------------------------------
# Internals

def _webview_on_loaded(window: webview.Window) -> None:
    global logged_in
    url = window.get_current_url()
    if not url:
        return
    match = regex.match(r"https://neurokaraoke\.com/discord-auth-callback.*token=([^&]+)", url)
    if not match:
        return
    window.destroy()
    with _settings_lock:
        settings.set("nkh_token", match[1])
        settings.save()
    logged_in = True

def _send_request(method: str, url: str) -> str:
    with _settings_lock:
        response = requests.request(method, url, headers={"authorization": f"Bearer {settings.get("nkh_token")}", "Referer": settings.get("referal_url", "")+"/", "Origin": settings.get("referal_url")})
    response.raise_for_status()
    return response.content.decode("UTF-8")

def _send_json_request(method: str, url: str) -> Any:
    with _settings_lock:
        response = requests.request(method, url, headers={"authorization": f"Bearer {settings.get("nkh_token")}", "Referer": settings.get("referal_url", "")+"/", "Origin": settings.get("referal_url")})
    response.raise_for_status()
    return response.json()

# --------------------------------------------------------------------------------
# Public Functions

def init(storage: StorageBase, autologin: bool = True):
    global settings, logged_in
    if __name__ != "__main__":
        settings = storage
    _settings_lock.release()
    if not storage.get("nkh_token") and autologin:
        login()
    elif storage.get("nkh_token"):
        logged_in = True

def login() -> None:
    """Opens a window to log in into neurokaraoke.com via discord"""
    window = webview.create_window("Login", "https://neurokaraoke.com/login?returnUrl=%2F")
    if not window:
        raise ValueError
    window.events.loaded += _webview_on_loaded
    webview.start()

def send_playcount(song_id: str) -> str:
    """Tells the server that this song has been played by the user"""
    return _send_request("PUT", f"https://api.neurokaraoke.com/api/songs/playCount/{song_id}")

def get_favourites() -> Any:
    """Gets all favourite songs of the user"""
    return _send_json_request("GET", "https://api.neurokaraoke.com/api/user/favorites")