import os

from niatools.settings import Settings
from pathlib import Path

settings = Settings(os.path.join(Path.home(), "neuro_21_station_player", "settings_v2.json"), os.path.join("data", "default_settings_v2.json"))

settings.set("size", (600, 600))
settings.set("data_url", "https://radio.twinskaraoke.com/api/nowplaying_static/neuro_21.json")
settings.set("darken_factor", 0.75)
settings.set("blur_scale", 20)
settings.set("main_container_width", 0.7)
settings.set("border_radius", 0.1)

print(settings)

settings.save()
