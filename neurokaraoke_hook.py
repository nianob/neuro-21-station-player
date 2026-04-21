import io
import os
import regex
import requests
import subprocess
import webview

from pathlib import Path
from typing import Any, Optional
from niatools.settings import Settings, getGlobal

# --------------------------------------------------------------------------------
# Internals

class SensitiveSettings(Settings):
    def save(self, filename: Optional[str] = None) -> None:
        super().save(filename)
        final_filename = filename or self.filename
        if not final_filename:
            raise ValueError("Location to save the file is unknown")
        if os.name == "nt":
            try:
                subprocess.run(["attrib", "+H", final_filename], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to hide sensitive file \"{final_filename}\": {e}")

sensitive_settings: SensitiveSettings
settings: Settings

# --------------------------------------------------------------------------------
# Internals

def _webview_on_loaded(window: webview.Window) -> None:
    url = window.get_current_url()
    if not url:
        return
    match = regex.match(r"https://neurokaraoke\.com/discord-auth-callback.*token=([^&]+)", url)
    if not match:
        return
    window.destroy()
    sensitive_settings.set("token", match[1])
    sensitive_settings.save()

def _send_request(method: str, url: str) -> str:
    response = requests.request(method, url, headers={"authorization": f"Bearer {sensitive_settings.get("token")}", "Referer": settings.get("referal_url")})
    response.raise_for_status()
    return response.content.decode("UTF-8")

def _send_json_request(method: str, url: str) -> Any:
    response = requests.request(method, url, headers={"authorization": f"Bearer {sensitive_settings.get("token")}", "Referer": settings.get("referal_url")})
    response.raise_for_status()
    return response.json()

# --------------------------------------------------------------------------------
# Public Functions

def init():
    global settings, sensitive_settings
    sensitive_settings = SensitiveSettings(os.path.join(Path.home(), "neuro_21_station_player", ".nk_settings.json"), io.StringIO("{}"))
    if __name__ != "__main__":
        settings = getGlobal()
    if not sensitive_settings.get("token"):
        login()

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

if __name__ == "__main__":
    init()