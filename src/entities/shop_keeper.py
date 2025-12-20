from __future__ import annotations
import pygame as pg
from typing import override
from enum import Enum

from src.entities.entity import Entity
from src.core import GameManager
from src.utils import GameSettings, Logger, Direction, Position, PositionCamera
from src.sprites import Sprite
from src.core.services import input_manager


class ShopKeeper(Entity):
    classification: str = "stationary" # Default
    max_tiles: int | None
    detected: bool
    los_direction: Direction
    warning_sign: Sprite


    def __init__(self, x: float, y: float, game_manager: GameManager, 
                 sprite_path: str = "character/ow1.png",
                 facing: Direction = Direction.DOWN,
                 max_tiles: int = 2):
        
        super().__init__(x, y, game_manager, sprite_path)
        self.hitbox = pg.Rect(x, y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        
        self.max_tiles = max_tiles
        self._set_direction(facing)
        
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        
        self.detected = False

    @override
    def update(self, dt: float):
        self._has_los_to_player()
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pg.draw.rect(screen, (0, 255, 255), camera.transform_rect(los_rect), 1) # Cyan for shop

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pg.Rect | None:
        enx = self.position.x
        eny = self.position.y
        tile_size = GameSettings.TILE_SIZE

        max_dis = (self.max_tiles or 2) * tile_size

        if self.los_direction == Direction.UP:
            return pg.Rect(enx, eny - max_dis, tile_size, max_dis)
        elif self.los_direction == Direction.DOWN:
            return pg.Rect(enx, eny + tile_size, tile_size, max_dis)
        elif self.los_direction == Direction.LEFT:
            return pg.Rect(enx - max_dis, eny, max_dis, tile_size)
        elif self.los_direction == Direction.RIGHT:
            return pg.Rect(enx + max_dis, eny, max_dis, tile_size)
        return None

    def _has_los_to_player(self) -> None:
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return
        
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return

        player_rect = pg.Rect(
            player.position.x, player.position.y,
            GameSettings.TILE_SIZE, GameSettings.TILE_SIZE
        )

        if los_rect.colliderect(player_rect):
            self.detected = True
        else:
            self.detected = False

    @classmethod
    def from_dict(cls, data: dict, game_manager: GameManager) -> "ShopKeeper":
        # Parse facing
        facing_val = data.get("facing", "DOWN")
        facing = Direction.DOWN
        if isinstance(facing_val, str):
             facing = Direction[facing_val]
        
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            data.get("sprite", "character/ow1.png"),
            facing=facing,
            max_tiles=data.get("max_tiles", 2)
        )
    
    @override
    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        base["sprite"] = self.sprite_path
        return base
