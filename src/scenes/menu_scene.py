import pygame as pg
from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.utils import GameSettings, Logger
from src.sprites import BackgroundSprite, Sprite
from src.scenes.scene import Scene
from src.interface.components import Button, Checkbox, Label
from src.interface.components import Button, Checkbox, Label, Popup, Slider
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override
class MenuScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Decorative
    title_bg: Sprite
    # Buttons
    play_button: Button
    settings_button : Button
    
    # Settings Overlay
    setting_panel: Popup
    volume_slider: Slider
    check_mute: Checkbox
    hitbox_checkbox: Checkbox
    back_button: Button
    current_overlay: str | None
    
    BACK_BUTTON_SIZE = 100
    CORNER_OFFSET = 15
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background4.png")
        # Load your asset here. Change "backgrounds/menu_art.png" to your file.
        # If you want to resize it, pass a tuple size=(width, height) as the second argument.
        self.title_bg = Sprite("UI/raw/UI_Flat_Banner02a.png", size=(760,198)) 
        self.title_bg.rect.center = (GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2 - 15 )

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.play_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            px + 50, py, 100, 100,
            on_click=lambda: scene_manager.change_scene("game")
        )
        
        self.settings_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            px - 100, py, 100, 100,
            on_click=lambda: self.toggle_overlay("setting")
        )
        self.title = Label(text=f"BROKENMON", x=GameSettings.SCREEN_WIDTH // 2 + 3, y=GameSettings.SCREEN_HEIGHT // 2 - 50,
                           color=(16, 106, 255),align='center',fontsize=112, fontfam=2)
        self.title_outline = Label(text=f"BROKENMON",
                                    x=GameSettings.SCREEN_WIDTH // 2,
                                    y=GameSettings.SCREEN_HEIGHT // 2 - 50,
                           color=(2, 20, 49),align='center',fontsize=112, fontfam=2)

        self.title_shad = Label(text=f"BROKENMON", x=GameSettings.SCREEN_WIDTH // 2 + 3,
                                y=GameSettings.SCREEN_HEIGHT // 2 - 40,
                           color=(7, 52, 126), align='center',fontsize=112, fontfam=2)
        
        # --- Settings Overlay Initialization ---
        self.current_overlay = None
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(None)
        self.setting_panel = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.setting_panel.interactive_components = [] # Clear default X button to match desired style
        # Back button for the settings panel
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            self.setting_panel.frame_rect.right - self.BACK_BUTTON_SIZE - self.CORNER_OFFSET,
            self.setting_panel.frame_rect.bottom - self.BACK_BUTTON_SIZE - self.CORNER_OFFSET,
            100, 100,
            on_click=close_callback
        )
        # Components in setting popup
        rec = self.setting_panel.frame_rect
        setting_frame_x = rec.x
        setting_frame_y = rec.y
        setting_frame_width = rec.width
        
        # Volume slider
        slider_width = 300
        slider_height = 40
        slider_x = setting_frame_x + (setting_frame_width // 2) - (slider_width // 2)
        slider_y = setting_frame_y + 150
        self.volume_slider = Slider(
            x=slider_x, y=slider_y,
            width=slider_width, height=slider_height,
            min_val=0.0, max_val=100.0,
            initial_val=sound_manager.get_volume() * 100,
            val_change=lambda v: sound_manager.set_volume(v/100),
            bar_path="UI/raw/UI_Flat_Bar05a.png",
            handle_path="UI/raw/UI_Flat_Button01a_3.png",
            label= "Master Volume"
        )
        self.setting_panel.interactive_components.append(self.volume_slider)
        # Checkboxes
        cb_size = 50
        cb_x = setting_frame_x + 140
        cb_y = slider_y + slider_height + 50
        self.hitbox_checkbox = Checkbox(
            x=cb_x, y=cb_y,
            size=cb_size,
            initial_checked=GameSettings.DRAW_HITBOXES,
            on_toggle=lambda checked: (
                setattr(GameSettings, "DRAW_HITBOXES", checked),
                Logger.info(f"Hitboxes has been set to :{checked}")
            ),
            label="Hitbox",
            unchecked_path="UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='UI/raw/UI_Flat_ToggleOn01a.png',
        )
        self.setting_panel.interactive_components.append(self.hitbox_checkbox)
        self.mute_check = Checkbox(
            x=cb_x, y=cb_y + 75,
            size=cb_size, 
            initial_checked= (sound_manager.get_volume() == 0), 
            on_toggle=self.toggle_mute, 
            label="Mute Audio",
            unchecked_path="UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='UI/raw/UI_Flat_ToggleOn01a.png',
        )
        self.setting_panel.interactive_components.append(self.mute_check)
    def toggle_overlay(self, overlay_name: str | None) -> None:
        if overlay_name == self.current_overlay:
            self.current_overlay = None
        else:
            self.current_overlay = overlay_name
    def toggle_mute(self, is_muted: bool) -> None:
        if is_muted:
            self._last_volume = sound_manager.get_volume()
            sound_manager.set_volume(0.0) 
        else:
            restore_volume = getattr(self, '_last_volume', 0.5)
            sound_manager.set_volume(restore_volume) 
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
        if input_manager.key_pressed(pg.K_SPACE):
            scene_manager.change_scene("game")
            return
        self.play_button.update(dt)
        self.settings_button.update(dt)
        if self.current_overlay == "setting":
            self.setting_panel.update(dt)
            self.back_button.update(dt)
        else:
            if input_manager.key_pressed(pg.K_SPACE):
                scene_manager.change_scene("game")
                return
            self.play_button.update(dt)
            self.settings_button.update(dt)
    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        
        self.play_button.draw(screen)
        self.settings_button.draw(screen)
        
        # Draw the decorative sprite BEFORE the text so it appears behind
        self.title_bg.draw(screen)
        self.title_shad.draw(screen)
        self.title.draw(screen)
        if self.current_overlay == "setting":
            # Draw semi-transparent background
            darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            darken.set_alpha(128)
            darken.fill((0,0,0))
            screen.blit(darken, (0, 0))
            
            self.setting_panel.draw(screen)
            self.back_button.draw(screen)