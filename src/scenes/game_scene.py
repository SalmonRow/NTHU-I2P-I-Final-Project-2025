import pygame as pg
import threading
import time

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import sound_manager, input_manager
from src.sprites import Sprite
from typing import override
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent

from src.entities.enemy_trainer import EnemyTrainer   # Existing trainer import
from src.entities.bush import BushEncounter

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
    save_button: Button
    load_button: Button
    #sliders
    volume_slider: Slider
    #checkboxes
    hitbox_checkbox: Checkbox

    #stuff in the bags
    monster_list: MonsterListComponent
    item_list: ItemListComponent
    wild_encounters: list['BushEncounter']
    

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

        self.setting_popup = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.bag_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)

        #creating buttons
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
            on_click=lambda: self.load_game_action(JASON)
        )
        self.setting_popup.interactive_components.append(self.load_button)

        setting_frame_x = self.setting_popup.frame_rect.x
        setting_frame_y = self.setting_popup.frame_rect.y
        setting_frame_width = self.setting_popup.frame_rect.width
        
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
        #entities
        self.wild_encounters = []
        self.closest_enemy = None

    def load_map_entities(self):
        self.wild_encounters = []

        current_map_data = self.game_manager.current_map.to_dict()
        if current_map_data is None:
            return

        # Change "bush" to "busP" to match your JSON
        bush_coords = current_map_data.get("bush", [])  
        wild_monster_pool = current_map_data.get("wild_mon", [])

        if wild_monster_pool: 
            for bush_data in bush_coords:
                bush = BushEncounter.from_dict(bush_data, self.game_manager, wild_monster_pool)
                self.wild_encounters.append(bush)

    def load_game_action(self, path: str):
        Logger.info(f"Attempting to load game from :{path}...")
        new_manager = GameManager.load(path)


        if new_manager is not None:
            self.exit()
            self.game_manager = new_manager
            self.enter()
            self.current_overlay = None
            Logger.info(f"Game Loaded successfully")
        else:
            Logger.info(f"Unsuccessful. File not found or corrupt")

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
            sound_manager.set_volume(restore_volume) 
            
    def _handle_battle_win(self):
        Logger.info("Player victory! State saved without auto-heal.")
        self.game_manager.auto_save()

    def _handle_battle_lose(self):
        Logger.warning("Player loss! State saved without auto-heal or position reset.")
        self.game_manager.auto_save()
        
    def _handle_battle_run(self):
        Logger.info("Player ran from battle! State saved without auto-heal.")
        self.game_manager.auto_save()

    
    @override
    def enter(self) -> None:
        Logger.info(f'Entering Game...')
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")

        battle_result = self.game_manager.get_and_clear_battle_result() 
        
        if battle_result:
            Logger.info(f"Post-battle state received: {battle_result.upper()}. State is now clear.")
            
            if battle_result == "win":
                self._handle_battle_win() 
            elif battle_result == "lose":
                self._handle_battle_lose()
            elif battle_result == "run":
                self._handle_battle_run()

        if self.online_manager:
            self.online_manager.enter()

        self.load_map_entities()
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
        
        self.closest_enemy = None
        min_distance = float('inf')
        MAX_CHALLANGE_DIS = GameSettings.TILE_SIZE * 2
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)

            if enemy._has_los_to_player() and enemy._distance_to_player() < min_distance:
                min_distance = enemy._distance_to_player()
                self.closest_enemy = enemy 
        for bush in self.wild_encounters:
            bush.update(dt)

        if self.closest_enemy and min_distance <= MAX_CHALLANGE_DIS and input_manager.key_pressed(pg.K_SPACE):
            self.trigger_battle(self.closest_enemy)
            return
        
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
        
        if self.current_overlay == "bag":
            self.bag_popup.update(dt)
        
    def trigger_battle(self, enemy_trainer: 'enemy_trainers'):
        from src.core.services import scene_manager
        if self.game_manager.current_battle_en is not None:
            return 
        
        Logger.info(f'Battle triggered with {enemy_trainer.monster['name']}!')

        self.game_manager.current_battle_en = enemy_trainer
        player_mon = self.game_manager.bag._monsters_data[0] 
        enemy_mon = enemy_trainer.monster 

        scene_manager.change_scene(
            'battle',
            player_monster=player_mon, 
            enemy_monster=enemy_mon,
            is_wild_encounter=False
        )


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

        for bush in self.wild_encounters:
            bush.draw(screen, camera)

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

        self.setting_button.draw(screen)
        self.bag_button.draw(screen)