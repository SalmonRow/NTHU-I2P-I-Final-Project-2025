from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Logger, Direction
# from src.core import GameManager
import math
import random
from typing import override
from src.sprites.particle import Particle

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager, "character/ow1.png")
        self.cooldown = 0.0
        self.particle_cooldown = 0.0
        self.particles: list[Particle] = []

    def _set_direction(self, direction: Direction):
        if self.direction == direction:
            return
        self.direction = direction
        if self.direction == Direction.RIGHT:
            self.animation.switch("right")
        elif self.direction == Direction.LEFT:
            self.animation.switch("left")
        elif self.direction == Direction.UP:
            self.animation.switch("up")
        elif self.direction == Direction.DOWN:
            self.animation.switch("down")


    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        movement_speed = 1

        if input_manager.key_down(pg.K_w) or input_manager.key_down(pg.K_UP):
            dis.y -= movement_speed
            self._set_direction(Direction.UP)
        if input_manager.key_down(pg.K_s) or input_manager.key_down(pg.K_DOWN):
            dis.y += movement_speed
            self._set_direction(Direction.DOWN)
        if input_manager.key_down(pg.K_a) or input_manager.key_down(pg.K_LEFT):
            dis.x -= movement_speed
            self._set_direction(Direction.LEFT)
        if input_manager.key_down(pg.K_d) or input_manager.key_down(pg.K_RIGHT):
            dis.x += movement_speed
            self._set_direction(Direction.RIGHT)
        
        movement_vector = pg.math.Vector2(dis.x, dis.y)
        if movement_vector.length_squared() > 0:
            movement_vector = movement_vector.normalize()

        speed_multiplier = 1.0
        if input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT):
            speed_multiplier = 1.5
            
            # Spawn particles if moving
            self.particle_cooldown -= dt
            if movement_vector.length_squared() > 0:
                if self.particle_cooldown <= 0:
                    p_x = self.position.x + GameSettings.TILE_SIZE / 2
                    p_y = self.position.y + GameSettings.TILE_SIZE
                    self.particles.append(Particle(p_x, p_y))
                    self.particle_cooldown = random.uniform(0.05, 0.1)

        to_move = self.speed * dt * 1.5 * speed_multiplier
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
    

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
                

        if movement_vector.length_squared() > 0:
            if input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT):
             
                super().update(dt * 1.75)
            else:
                super().update(dt )
        else:
             super().update(0)
             self.animation.accumulator = 0


    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        for p in self.particles:
            p.draw(screen, camera)
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

