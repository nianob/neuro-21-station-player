import os

from niatools.settings import Settings
from pathlib import Path

settings = Settings(os.path.join(Path.home(), "neuro_21_station_player", "settings_v2.json"), os.path.join("data", "default_settings_v2.json"))

settings.set("size", (600, 600))
settings.set("data_url", "https://radio.twinskaraoke.com/api/nowplaying_static/neuro_21.json")
settings.set("darken_factor", 0.75)
settings.set("blur_scale", 20)
settings.set("border_radius", 0.1)
settings.set("author_scale", 0.65)
settings.set("font_color", (255, 255, 255))
settings.set("content_padding", 0.03)
settings.set("controls_size", 0.075)
settings.set("button_padding", 0.01)
settings.set("autoplay", False)
settings.set("button_color", (134, 215, 247, 170))
settings.set("progress_bar_color", (255, 255, 255, 100))
settings.set("steam_type", "mp3")
settings.set("button_text_color", (0, 0, 0))
settings.set("stream_type", "mp3")

print(settings)

settings.save()
