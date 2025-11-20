import pygame as pg
import threading
import time

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import sound_manager
from src.sprites import Sprite
from typing import override
from src.interface.components import Button, Popup, Checkbox, Slider

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite

    #UI components
    #popups
    setting_popup: Popup
    bag_popup: Popup
    
    #buttons
    current_overlay: str | None
    setting_button: Button
    bag_button: Button
    #sliders
    volume_slider: Slider
    #checkboxes
    hitbox_checkbox: Checkbox
    

    def __init__(self):
        super().__init__()
        # Game Manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        
        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None
        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))

        self.current_overlay = None

        #the pop up thingy
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(self.current_overlay)

        setting_popup_path = "assets/images/UI/raw/UI_Flat_Frame03a.png"
        bag_popup_path = "assets/images/UI/raw/UI_Flat_Frame02a.png"

        self.setting_popup = Popup(setting_popup_path, screen_size, close_callback)
        self.bag_popup = Popup(bag_popup_path, screen_size, close_callback)

        #creating buttons
        self.setting_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 70, 10, 
            60,
            60,
            lambda : self.toggle_overlay("setting")
        )

        self.bag_button = Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 140, 10,
            60,
            60,
            lambda : self.toggle_overlay("bag")
        )

        #for scaling stuff in setting
        setting_frame_x = self.setting_popup.frame_rect.x
        setting_frame_y = self.setting_popup.frame_rect.y
        setting_frame_width = self.setting_popup.frame_rect.width
        
        #---sliders---
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
            handle_path="assets/images/UI/raw/UI_Flat_Button01a_1.png",
            label= "Master Volume"
        )
        self.setting_popup.interactive_components.append(self.volume_slider)

        #---checkboxes---
        cb_size = 30
        cb_x = setting_frame_x + 50
        cb_y = slider_y + slider_height + 50

        self.hitbox_checkbox = Checkbox(
            x=cb_x, y=cb_y,
            size=cb_size,
            initial_checked=GameSettings.DRAW_HITBOXES,
            on_toggle=lambda checked: (
                setattr(GameSettings, "DRAW_HITBOXES", checked),
                Logger.info(f"Hitboxes has been set to :{checked}")
            ),
            label="Toggle Hitbox",
            checked_path="assets/images/UI/raw/UI_Flat_ToggleOn03a.png",
            unchecked_path="assets/images/UI/raw/UI_Flat_ToggleOff03a.png",
        )

        self.setting_popup.interactive_components.append(self.hitbox_checkbox)




    #overlay
    def toggle_overlay(self, overlay_name) -> None:
        if overlay_name is None:
            self.current_overlay = None
        elif self.current_overlay == overlay_name:
            self.current_overlay = None
        else:
            self.current_overlay = overlay_name
        
        
    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.enter()
        
    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()
        
    @override
    def update(self, dt: float):
        # Check if there is assigned next scene
        self.game_manager.try_switch_map()
        
        # Update player and other data
        if self.game_manager.player:
            self.game_manager.player.update(dt)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)
            
        # Update others
        self.game_manager.bag.update(dt)
        
        if self.game_manager.player is not None and self.online_manager is not None:
            _ = self.online_manager.update(
                self.game_manager.player.position.x, 
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name
            )

        # Update overlay buttons
        self.setting_button.update(dt) 
        self.bag_button.update(dt) 

        if self.current_overlay == "setting":
            self.setting_popup.update(dt)
            # self.back_button.update(dt)
        
        if self.current_overlay == "bag":
            self.bag_popup.update(dt)
            # self.back_button.update(dt)


        
    @override
    def draw(self, screen: pg.Surface):        
        if self.game_manager.player:
            camera = self.game_manager.player.camera
            
            self.game_manager.current_map.draw(screen, camera)
            self.game_manager.player.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)

        self.game_manager.bag.draw(screen)
        
        if self.online_manager and self.game_manager.player:
            list_online = self.online_manager.get_list_players()
            for player in list_online:
                if player["map"] == self.game_manager.current_map.path_name:
                    cam = self.game_manager.player.camera
                    pos = cam.transform_position_as_position(Position(player["x"], player["y"]))
                    self.sprite_online.update_pos(pos)
                    self.sprite_online.draw(screen)


        #the overlay part
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

            # self.back_button.draw(screen)

        self.setting_button.draw(screen)
        self.bag_button.draw(screen)