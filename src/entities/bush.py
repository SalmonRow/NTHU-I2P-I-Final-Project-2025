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
        super().__init__(x,y, game_manager)

        self.monster_pool = monster_pool
        # Set up warning sign
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

        self.press_e = Label(
            "press E", GameSettings.SCREEN_WIDTH // 2 - 40, GameSettings.SCREEN_HEIGHT - 40
        )
        
        Logger.info(f"BushEncounter created at ({x}, {y})")
        Logger.info(f"self.position exists: {hasattr(self, 'position')}")
        if hasattr(self, 'position'):
            Logger.info(f"self.position value: ({self.position.x}, {self.position.y})")
        

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
            return
        if input_manager.key_pressed(pg.K_e):
            Logger.info('pressed e')
            if random.random() < self.CHANCE:

                if scene_manager._next_scene is not None:
                    return

                # 7. ⚔️ BATTLE TRIGGERED: Safely define variables here 
                wild_mon_data = random.choice(self.monster_pool)
                self.game_manager.current_battle_en = self
                player_mon = self.game_manager.bag._monsters_data[0]

                scene_manager.change_scene(
                    'battle', 
                    player_monster=player_mon, 
                    enemy_monster=wild_mon_data, 
                    is_wild_encounter=True 
                )
                return 
            else:
                Logger.info("E pressed, but random chance failed.")
                return 

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        if self.detected:
            self.warning_sign.draw(screen, camera)
            self.press_e.draw(screen)
            
        if GameSettings.DRAW_HITBOXES:
            pg.draw.rect(screen, (0, 255, 0), camera.transform_rect(self.hitbox), 1)

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager, monster_pool: list[Monster]) -> "BushEncounter":
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            monster_pool
        )