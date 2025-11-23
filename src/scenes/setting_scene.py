#TODO HACKATHON 5
import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button, Popup, Label, Slider, Checkbox
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

class SettingScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Buttons
    play_button: Button
    settings_button : Button
    setting_panel: Popup
    volume_slider: Slider
    check_mute: Checkbox

    current_overlay: str
    BACK_BUTTON_SIZE = 100
    CORNER_OFFSET = 15

    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")
        #the pop up thingy
        self.current_overlay = "setting"
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(self.current_overlay)

        self.setting_panel = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.setting_panel.interactive_components = []#empty the x button

        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            self.setting_panel.frame_rect.right - self.BACK_BUTTON_SIZE - self.CORNER_OFFSET,
            self.setting_panel.frame_rect.bottom - self.BACK_BUTTON_SIZE - self.CORNER_OFFSET,
            100, 100,
            on_click=lambda: scene_manager.change_scene("menu")
        )

        #components in setting popup
        rec = self.setting_panel.frame_rect
        self.volume_slider = Slider(
            x=rec.left + self.CORNER_OFFSET * 2, y=rec.center[1]-80,
            width=200, 
            height=40,
            min_val=0.0, max_val=100.0,
            initial_val=sound_manager.get_volume() * 100,
            val_change=lambda v: sound_manager.set_volume(v/100),
            bar_path="assets/images/UI/raw/UI_Flat_Bar05a.png",
            handle_path="assets/images/UI/raw/UI_Flat_Button01a_3.png",
            label= "Master Volume"
        )
        self.setting_panel.interactive_components.append(self.volume_slider)

        self.mute_check = Checkbox(
            x=rec.left + self.CORNER_OFFSET * 2, y=rec.center[1]-20,
            size= 50, 
            initial_checked= (sound_manager.get_volume() == 0), 
            on_toggle=self.toggle_mute, 
            label="Mute Audio",
            unchecked_path="assets/images/UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='assets/images/UI/raw/UI_Flat_ToggleLeftOn01a.png',
        )
        self.setting_panel.interactive_components.append(self.mute_check)
    #overlay
    def toggle_overlay(self, overlay_name) -> None:
        if overlay_name is None:
            self.current_overlay = None
        elif self.current_overlay == overlay_name:
            self.current_overlay = None
        else:
            self.current_overlay = overlay_name   
    def toggle_mute(self, is_muted: bool) -> None:
        if is_muted:
            self._last_volume = sound_manager.get_volume()
            sound_manager.set_volume(0.0) 
        else:
            restore_volume = getattr(self, '_last_volume', 0.5)
            sound_manager.set_volume(restore_volume) #

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
        self.setting_panel.update(dt)
    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)

        if self.current_overlay is not None:

            darken = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
            )
            darken.set_alpha(128)
            darken.fill((0,0,0))
            screen.blit(darken, (0, 0))  

            if self.current_overlay == "setting":
                self.setting_panel.draw(screen)

        self.back_button.draw(screen)