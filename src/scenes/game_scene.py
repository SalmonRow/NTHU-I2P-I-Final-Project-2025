import pygame as pg

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import sound_manager, input_manager
from src.sprites import Sprite
from typing import override
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent
from src.interface.game_ui_manager import GameSceneUIManager

from src.entities.enemy_trainer import EnemyTrainer   # Existing trainer import
from src.entities.bush import BushEncounter

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    ui_manager: GameSceneUIManager

    #stuff in the bags
    wild_encounters: list['BushEncounter']
    
    def __init__(self):
        super().__init__()
        self._init_managers()
        self._init_state()
        
        # Initialize UI Manager
        self.ui_manager = GameSceneUIManager(self)

    def _init_managers(self) -> None:
        # Load game manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        
        # Setup online manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None
        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))

    def _init_state(self) -> None:
        """Initialize scene state variables."""
        self.wild_encounters = []
        self.closest_enemy = None


    def load_map_entities(self):
        self.wild_encounters = []

        current_map_data = self.game_manager.current_map.to_dict()
        if current_map_data is None:
            return

        wild_monster_pool = current_map_data.get("wild_mon", [])

        if wild_monster_pool: 
            bush_rects = self.game_manager.current_map._bushmap
            
            for rect in bush_rects:
                grid_x = rect.x // GameSettings.TILE_SIZE
                grid_y = rect.y // GameSettings.TILE_SIZE
                
                bush_data = {"x": grid_x, "y": grid_y}
                
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

        # Update UI
        self.ui_manager.update(dt)
        
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
        camera = PositionCamera(0, 0)
        if self.game_manager.player:
            camera = self.game_manager.player.camera
        
        # 1. Draw Map (Background)
        self.game_manager.current_map.draw(screen, camera)

        # 2. Collect all renderable entities
        renderables = []

        # Player
        if self.game_manager.player:
            renderables.append(self.game_manager.player)
        
        # Enemy Trainers
        renderables.extend(self.game_manager.current_enemy_trainers)
        renderables.extend(self.wild_encounters)

        # Online Players
        if self.online_manager and self.game_manager.player:
            list_online = self.online_manager.get_list_players()
            for p_data in list_online:
                if p_data["map"] == self.game_manager.current_map.path_name:
                    # Create a temporary sorted object wrapper
                    class OnlinePlayerRenderable:
                        def __init__(self, data, sprite, cam_ref):
                            self.data = data
                            self.sprite = sprite
                            self.cam_ref = cam_ref
                            self.position = Position(data["x"], data["y"])
                            # Sort by Y. 
                            self.sort_y = self.position.y + GameSettings.TILE_SIZE
                        
                        def draw(self, surf, cam):
                            # Online player draw logic extracted from original loop
                            pos = cam.transform_position_as_position(self.position)
                            self.sprite.update_pos(pos)
                            self.sprite.draw(surf)

                    renderables.append(OnlinePlayerRenderable(p_data, self.sprite_online, camera))


        def get_sort_key(entity):
             # Online players have .sort_y
            if hasattr(entity, 'sort_y'):
                return entity.sort_y
            
            # Entities usually have a hitbox
            if hasattr(entity, 'hitbox'):
                return entity.hitbox.bottom
            
            # Fallback to position
            if hasattr(entity, 'position'):
                return entity.position.y + GameSettings.TILE_SIZE
            
            return 0

        renderables.sort(key=get_sort_key)

        # 4. Draw Sorted Entities
        for entity in renderables:
            entity.draw(screen, camera)

        # 5. Draw UI (Always on top)
        self.game_manager.bag.draw(screen)
        self.ui_manager.draw(screen)