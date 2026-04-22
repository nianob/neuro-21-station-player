import logging
import os
import pygame
import sys

from niatools.settings import Settings
from pathlib import Path

import helpers
import surfaces

class Main:
    def __init__(self) -> None:
        self.data_dir: str = os.path.join(Path.home(), "neuro_21_station_player")
        self.working_dir: str = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        self.settings: Settings = Settings(os.path.join(self.data_dir, "settings_v2.json"), os.path.join(self.working_dir, "data", "default_settings_v2.json"))

        self.screen: pygame.Surface = pygame.display.set_mode(self.settings.get("size"))
        self.current_screen: surfaces.Screen # TODO: set this to the default screen
        self.running = True
    
    def loop(self) -> None:
        while self.running:
            self.current_screen.update()

if __name__ == "__main__":
    helpers.setup_logging()
    logging.info("test")