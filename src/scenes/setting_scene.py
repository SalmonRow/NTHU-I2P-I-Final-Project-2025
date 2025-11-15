#TODO HACKATHON 5
import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

class SettingScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Buttons
    play_button: Button
    settings_button : Button

    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")
        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            px - 100, py, 100, 100,
            lambda: scene_manager.change_scene("menu")
        )

    @override
    def handle(self, event):
        self.back_button.handle_event(event)
        
    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
        pass

    @override
    def exit(self) -> None:
        sound_manager.stop_all_sounds() #stop musics for now, idk bruh

        pass

    @override
    def update(self, dt: float) -> None:
        self.back_button.update(dt)
    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.back_button.draw(screen)
