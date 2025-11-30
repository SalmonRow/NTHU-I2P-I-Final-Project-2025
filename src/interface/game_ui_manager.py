import pygame as pg
from src.utils import Logger, GameSettings
from src.core.services import sound_manager
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent
from src.core import GameManager

class GameSceneUIManager:
    def __init__(self, game_scene):
        self.scene = game_scene
        self.game_manager: GameManager = game_scene.game_manager
        
        self.current_overlay = None
        self._last_volume = 0.5
        
        # UI Components
        self.setting_popup: Popup = None
        self.bag_popup: Popup = None
        self.setting_button: Button = None
        self.bag_button: Button = None
        self.save_button: Button = None
        self.load_button: Button = None
        self.volume_slider: Slider = None
        self.hitbox_checkbox: Checkbox = None
        self.mute_check: Checkbox = None
        self.monster_list: MonsterListComponent = None
        self.item_list: ItemListComponent = None

        # Initialize everything
        self._init_popups()
        self._init_overlay_buttons()
        self._init_setting_components()
        self._init_bag_components()

    def _init_popups(self) -> None:
        """Create setting and bag popup windows."""
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(self.current_overlay)
        
        self.setting_popup = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.bag_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)

    def _init_overlay_buttons(self) -> None:
        """Create overlay buttons and save/load buttons."""
        # Top-right overlay toggle buttons
        self.setting_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 70, 10, 
            60,
            60,
            on_click=lambda : self.toggle_overlay("setting")
        )

        self.bag_button = Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 140, 10,
            60,
            60,
            on_click=lambda : self.toggle_overlay("bag")
        )

        # Save/Load buttons inside setting popup
        JASON = "saves/game0.json"
        self.save_button = Button(
            "UI/button_save.png",
            "UI/button_save_hover.png",
            self.setting_popup.frame_rect.left + 30,
            self.setting_popup.frame_rect.top + 30,
            80,
            80,
            on_click=lambda: self.game_manager.save(JASON)
        )
        self.setting_popup.interactive_components.append(self.save_button)

        self.load_button = Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            self.setting_popup.frame_rect.left + 120,
            self.setting_popup.frame_rect.top + 30,
            80,
            80,
            on_click=lambda: self.scene.load_game_action(JASON)
        )
        self.setting_popup.interactive_components.append(self.load_button)

    def _init_setting_components(self) -> None:
        """Create sliders and checkboxes for the settings popup."""
        setting_frame_x = self.setting_popup.frame_rect.x
        setting_frame_y = self.setting_popup.frame_rect.y
        setting_frame_width = self.setting_popup.frame_rect.width
        
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
            bar_path="assets/images/UI/raw/UI_Flat_Bar05a.png",
            handle_path="assets/images/UI/raw/UI_Flat_Button01a_3.png",
            label= "Master Volume"
        )
        self.setting_popup.interactive_components.append(self.volume_slider)

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
            unchecked_path="assets/images/UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='assets/images/UI/raw/UI_Flat_ToggleLeftOn01a.png',
        )
        self.setting_popup.interactive_components.append(self.hitbox_checkbox)

        self.mute_check = Checkbox(
            x=cb_x, y=cb_y + 75,
            size=cb_size, 
            initial_checked= (sound_manager.get_volume() == 0), 
            on_toggle=self.toggle_mute, 
            label="Mute Audio",
            unchecked_path="assets/images/UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='assets/images/UI/raw/UI_Flat_ToggleLeftOn01a.png',
        )
        self.setting_popup.interactive_components.append(self.mute_check)

    def _init_bag_components(self) -> None:
        """Create monster and item list components for the bag popup."""
        bag_frame_x = self.bag_popup.frame_rect.x
        bag_frame_y = self.bag_popup.frame_rect.y
        bag_frame_width = self.bag_popup.frame_rect.width
        bag_frame_height = self.bag_popup.frame_rect.height

        list_width = (bag_frame_width // 2) - 40
        list_height = bag_frame_height - 100

        self.monster_list = MonsterListComponent(
            x=bag_frame_x + 20, y=bag_frame_y + 80,
            width=list_width,height=list_height,
            monster_list=self.game_manager.bag._monsters_data
        )
        self.bag_popup.interactive_components.append(self.monster_list)

        self.item_list = ItemListComponent(
            x=bag_frame_x + list_width + 30, y=bag_frame_y + 80,
            width=list_width,height=list_height,
            item_list=self.game_manager.bag._items_data
        )
        self.bag_popup.interactive_components.append(self.item_list)

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
            sound_manager.set_volume(restore_volume)

    def update(self, dt: float) -> None:
        # Update overlay buttons
        self.setting_button.update(dt) 
        self.bag_button.update(dt) 
        
        if self.current_overlay == "setting":
            self.setting_popup.update(dt)
        
        if self.current_overlay == "bag":
            self.bag_popup.update(dt)

    def draw(self, screen: pg.Surface) -> None:
        # Draw overlay background if active
        if self.current_overlay is not None:
            darken = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
            )
            darken.set_alpha(128)
            darken.fill((0,0,0))
            screen.blit(darken, (0, 0))  

            if self.current_overlay == "setting":
                self.setting_popup.draw(screen)
            if self.current_overlay == "bag":
                self.bag_popup.draw(screen)

        # Draw buttons
        self.setting_button.draw(screen)
        self.bag_button.draw(screen)
