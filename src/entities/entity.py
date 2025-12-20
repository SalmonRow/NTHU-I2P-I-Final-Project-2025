from __future__ import annotations
import pygame as pg
from typing import override
from src.sprites import Animation
from src.utils import Position, PositionCamera, Direction, GameSettings
from src.core import GameManager


class Entity:

    sprite_path: str
    
    def __init__(self, x: float, y: float, game_manager: GameManager, sprite_path: str) -> None:
        # Sprite is only for debug, need to change into animations
        self.sprite_path = sprite_path
        self.animation = Animation(
            sprite_path, ["down", "left", "right", "up"], 4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        )
        
        self.position = Position(x, y)
        self.direction = Direction.DOWN
        self.animation.update_pos(self.position)
        self.game_manager = game_manager

        self.hitbox = pg.Rect(
            x,y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )

    def update(self, dt: float) -> None:
        self.animation.update_pos(self.position)
        self.animation.update(dt)
        self.hitbox.topleft = (self.position.x, self.position.y)
        
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        self.animation.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            self.animation.draw_hitbox(screen, camera)
        
    @staticmethod
    def _snap_to_grid(value: float) -> int:
        return round(value / GameSettings.TILE_SIZE) * GameSettings.TILE_SIZE
    
    @property
    def camera(self) -> PositionCamera:
        half_width = GameSettings.SCREEN_WIDTH / 2
        half_height = GameSettings.SCREEN_HEIGHT / 2
        half_tile = GameSettings.TILE_SIZE / 2

        center_x = self.position.x + half_tile
        center_y = self.position.y + half_tile

        camera_x = center_x - half_width
        camera_y = center_y - half_height

        # Clamp to map boundaries
        if hasattr(self, 'game_manager') and self.game_manager.current_map:
            # Get map dimensions
            map_surf = self.game_manager.current_map._surface
            map_w = map_surf.get_width()
            map_h = map_surf.get_height()
            screen_w = GameSettings.SCREEN_WIDTH
            screen_h = GameSettings.SCREEN_HEIGHT
            
            # Only clamp if map is larger than screen (otherwise camera stays at 0 or specialized handling later)
            # Actually, standard clamp works: max(0, min(val, limit))
            # If map < screen, limit is negative. max(0, negative) is 0. 
            # This correctly forces camera to 0,0 for small maps (top-left aligned), 
            # which serves as a good base for the Auto-Zoom logic in GameScene.
            
            camera_x = max(0, min(camera_x, map_w - screen_w))
            camera_y = max(0, min(camera_y, map_h - screen_h))

        return PositionCamera(int(camera_x), int(camera_y))
        
    def to_dict(self) -> dict[str, object]:
        return {
            "x": self.position.x / GameSettings.TILE_SIZE,
            "y": self.position.y / GameSettings.TILE_SIZE,
        }
        
    @classmethod
    def from_dict(cls, data: dict[str, float | int], game_manager: GameManager) -> Entity:
        x = float(data["x"])
        y = float(data["y"])
        return cls(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, game_manager)
        