from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Logger
from src.core import GameManager
import math
from typing import override

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        self.cooldown = 0.0

    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        movement_speed = 6
        '''
        [TODO HACKATHON 2]
        Calculate the distance change, and then normalize the distance
        '''

        if input_manager.key_down(pg.K_w) or input_manager.key_down(pg.K_UP):
            dis.y -= movement_speed
        if input_manager.key_down(pg.K_s) or input_manager.key_down(pg.K_DOWN):
            dis.y += movement_speed
        if input_manager.key_down(pg.K_a) or input_manager.key_down(pg.K_LEFT):
            dis.x -= movement_speed
        if input_manager.key_down(pg.K_d) or input_manager.key_down(pg.K_RIGHT):
            dis.x += movement_speed
        

        movement_vector = pg.math.Vector2(dis.x, dis.y)
        if movement_vector.length_squared() > 0:
            movement_vector = movement_vector.normalize()

        to_move = self.speed * dt

        self.position.x += movement_vector.x * to_move

        player_rect = pg.Rect(self.position.x, #player's rectangle here 
                              self.position.y,
                              GameSettings.TILE_SIZE,
                              GameSettings.TILE_SIZE)
        
        if self.game_manager.current_map.check_collision(player_rect):
            self.position.x -= movement_vector.x * to_move
            self.position.x = self._snap_to_grid(self.position.x)

        self.position.y += movement_vector.y * to_move

        player_rect.x = self.position.x
        player_rect.y = self.position.y

        if self.game_manager.current_map.check_collision(player_rect):
            self.position.y -= movement_vector.y * to_move
            self.position.y = self._snap_to_grid(self.position.y) #make it so that it snaps to the grid perfectly

        # Check teleportation
        if self.cooldown > 0:
            self.cooldown -= dt
        else:

            tp = self.game_manager.current_map.check_teleport(self.position)

            if tp:
                dest = tp.destination
                self.game_manager.switch_map(dest)
                self.cooldown += 0.5
                
        super().update(dt)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

