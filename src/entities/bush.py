from __future__ import annotations
import pygame as pg
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera, Logger
from src.utils.definition import Monster
from src.interface.components.label import Label
import random

class BushEncounter(Entity):
    CHANCE: float = 0.9
    _last_player_tile_pos: tuple[int,int] | None = None

    monster_pool: list[Monster] 
    detected: bool = False
    warning_sign: Sprite
    
    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        monster_pool: list[Monster],
    ) -> None:
        super().__init__(x,y, game_manager, "character/ow1.png") # TODO: Add bush sprite? 

        # monster_pool is now just a list of strings (names) or Dicts with name
        # If it's a list of dicts from JSON, extract names?
        # User said "json would now only have a list of names"
        # So we assume monster_pool is a list of strings.
        self.monster_pool = monster_pool
        # Set up warning sign
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False
        self.encounter_pending = False

        self.press_e = Label(
            "press E", GameSettings.SCREEN_WIDTH // 2 - 40, GameSettings.SCREEN_HEIGHT - 40
        )
        
        Logger.info(f"BushEncounter created at ({x}, {y})")
        Logger.info(f"self.position exists: {hasattr(self, 'position')}")
        if hasattr(self, 'position'):
            Logger.info(f"self.position value: ({self.position.x // 64}, {self.position.y // 64})")
        

        self.hitbox = pg.Rect(x, y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)

    def _is_player_on_bush(self) -> bool:
        player = self.game_manager.player
        if player is None:
            return False
        return self.hitbox.colliderect(player.hitbox)
    
    @override
    def update(self, dt: float) -> None:
        self.hitbox.topleft = (self.position.x, self.position.y)
        is_colliding = self._is_player_on_bush()
        self.detected = is_colliding
        
        if not self.detected:
            # Reset tracker when leaving bush
            self._last_player_tile_pos = None
            # Also reset pending battle if player runs away from the tile
            self.encounter_pending = False
            return

        # Get Player Tile Position
        player = self.game_manager.player
        if not player:
            return
            
        current_tile_pos = (int(player.position.x // GameSettings.TILE_SIZE), 
                            int(player.position.y // GameSettings.TILE_SIZE))
        
        # Check if player moved to a NEW tile while in bush
        if self._last_player_tile_pos != current_tile_pos:
            self._last_player_tile_pos = current_tile_pos
            
            # Roll for Encounter (e.g., 15% chance per step)
            # User asked for "random chance of that pokemon appearing"
            ENCOUNTER_CHANCE = 0.15 
            
            if random.random() < ENCOUNTER_CHANCE:
                Logger.info("Wild Encounter Found! Press F to fight.")
                self.encounter_pending = True
        
        # If encounter is valid/pending, check for interaction to START logic
        if self.encounter_pending:
            if input_manager.key_pressed(pg.K_f):
                if scene_manager._next_scene is not None:
                    return

                from src.core.data_loader import DataLoader
                import copy
                
                dl = DataLoader.instance()
                
                # Calculate Dynamic Level
                party = self.game_manager.bag.monsters
                if not party: 
                     player_max = 5
                else:
                    player_max = max(m.get('level', 1) for m in party)
                
                min_lvl = max(5, player_max - 5)
                max_lvl = player_max + 5
                wild_level = random.randint(min_lvl, max_lvl)
                
                # Pick random monster name
                # Handle if monster_pool is list of strings or dicts (legacy support)
                raw = random.choice(self.monster_pool)
                if isinstance(raw, dict):
                    mon_name = raw.get('name')
                else:
                    mon_name = raw
                    
                # Create Wild Monster
                wild_mon_data = dl.create_wild_monster(mon_name, wild_level)
                
                if not wild_mon_data:
                    Logger.error("Failed to generate wild monster data.")
                    self.encounter_pending = False
                    return

                self.game_manager.current_battle_en = self
                
                player_mon = self.game_manager.bag.get_first_available_monster()
                
                if not player_mon:
                     Logger.info("Cannot start battle: No healthy pokemon!")
                     self.game_manager.current_battle_en = None
                     return

                scene_manager.change_scene(
                    'battle', 
                    player_monster=player_mon, 
                    enemy_monster=wild_mon_data, 
                    is_wild_encounter=True 
                )
                self.encounter_pending = False # Reset
                return 

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        if self.encounter_pending:
             self.warning_sign.draw(screen, camera)
        # # Check debug draw
        # if GameSettings.DRAW_HITBOXES:
        #     pg.draw.rect(screen, (0, 255, 0), camera.apply_rect(self.hitbox), 1)

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager, monster_pool: list[Monster]) -> "BushEncounter":
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            monster_pool
        )