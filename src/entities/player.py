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
        self.path: list[Position] = []
        self.allow_teleport = False
        self.is_moving = False
        self.is_surfing = False
        self.surfing_monster = None

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

        if self.path:
            target = self.path[0]
            # Calculate direction to target
            diff_x = target.x - self.position.x
            diff_y = target.y - self.position.y
            dist = math.sqrt(diff_x**2 + diff_y**2)
            
            if dist > 0:
                movement_vector = pg.math.Vector2(diff_x, diff_y).normalize()
            else:
                movement_vector = pg.math.Vector2(0, 0)
                
            # Set direction for animation
            if abs(diff_x) > abs(diff_y):
                if diff_x > 0: self._set_direction(Direction.RIGHT)
                else: self._set_direction(Direction.LEFT)
            else:
                if diff_y > 0: self._set_direction(Direction.DOWN)
                else: self._set_direction(Direction.UP)

            # Determine move distance for this frame
            to_move = self.speed * dt * 1.5
            
            # Apply movement immediately for path following (skip collision checks as path is pre-validated)
            self.position.x += movement_vector.x * to_move
            self.position.y += movement_vector.y * to_move

            # If we are close enough to the target (or passed it), snap to it and move to next point
            # We use the original distance to check if we covered it
            if dist <= to_move:
                self.position.x = target.x
                self.position.y = target.y
                self.path.pop(0)

        else:
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
            self.update_particles(dt)
        
            # Manual movement with collision checks
            # Check if destination is water
            test_rect = pg.Rect(self.position.x + movement_vector.x * to_move,
                               self.position.y + movement_vector.y * to_move,
                               GameSettings.TILE_SIZE,
                               GameSettings.TILE_SIZE)
            
            is_water = self.game_manager.current_map.is_water_tile(test_rect)
            
            if is_water:
                # Check for water-type Pokemon
                water_mon = None
                for mon in self.game_manager.bag.monsters:
                    if mon.get('type') == 'Water':
                        water_mon = mon
                        break
                
                if water_mon:
                    self.is_surfing = True
                    self.surfing_monster = water_mon
                else:
                    # No water Pokemon, treat as collision
                    self.is_surfing = False
                    self.surfing_monster = None
            else:
                self.is_surfing = False
                self.surfing_monster = None
            
            # Spawn blue particles when surfing and moving
            if self.is_surfing and movement_vector.length_squared() > 0:
                self.particle_cooldown -= dt
                if self.particle_cooldown <= 0:
                    p_x = self.position.x + GameSettings.TILE_SIZE / 2
                    p_y = self.position.y + GameSettings.TILE_SIZE
                    self.particles.append(Particle(p_x, p_y, (0, 150, 255)))
                    self.particle_cooldown = random.uniform(0.05, 0.1)
            
            self.position.x += movement_vector.x * to_move 

            player_rect = pg.Rect(self.position.x, 
                                  self.position.y,
                                  GameSettings.TILE_SIZE,
                                  GameSettings.TILE_SIZE)
            
            # Use include_water=False when surfing to ignore water collision
            if self.game_manager.current_map.check_collision(player_rect, include_water=not self.is_surfing):
                self.position.x -= movement_vector.x * to_move
                self.position.x = self._snap_to_grid(self.position.x)

            self.position.y += movement_vector.y * to_move

            player_rect.x = self.position.x
            player_rect.y = self.position.y

            if self.game_manager.current_map.check_collision(player_rect, include_water=not self.is_surfing):
                self.position.y -= movement_vector.y * to_move
                self.position.y = self._snap_to_grid(self.position.y) 

        # Check teleportation
        tp = self.game_manager.current_map.check_teleport(self.position)

        if tp:
            if self.allow_teleport:
                dest = tp.destination
                self.game_manager.switch_map(dest)
                self.allow_teleport = False
        else:
            self.allow_teleport = True
                

        if movement_vector.length_squared() > 0:
            # Log position constantly when moving
            tile_x = int(self.position.x // GameSettings.TILE_SIZE)
            tile_y = int(self.position.y // GameSettings.TILE_SIZE)
            Logger.info(f"Player Position: ({self.position.x:.1f}, {self.position.y:.1f}) | Tile: ({tile_x}, {tile_y})")

            self.is_moving = True
            
            # Stop walking animation when surfing
            if self.is_surfing:
                super().update(0)
                self.animation.accumulator = 0
            elif input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT):
                super().update(dt * 1.75)
            else:
                super().update(dt)
        else:
             self.is_moving = False
             super().update(0)
             self.animation.accumulator = 0

    def update_particles(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]


    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        for p in self.particles:
            p.draw(screen, camera)
        
        if self.is_surfing and self.surfing_monster:
            from src.core.services import resource_manager
            
            # 1. Draw player sprite shifted up FIRST
            shifted_pos = Position(self.position.x, self.position.y - 12)
            screen_pos_p = camera.transform_position_as_position(shifted_pos)
            frames = self.animation.animations[self.animation.cur_row]
            idx = int((self.animation.accumulator / self.animation.loop) * self.animation.n_keyframes)
            screen.blit(frames[idx], (screen_pos_p.x, screen_pos_p.y))

            # 2. Draw Pokemon icon SECOND (so it is in front of the player's feet)
            menu_sprite_path = self.surfing_monster.get('menu_sprite_path')
            if menu_sprite_path:
                pokemon_icon = resource_manager.get_image(menu_sprite_path)
                # Scale to appropriate size (1.2 times Tile Size)
                icon_size = int(GameSettings.TILE_SIZE * 1.2)
                pokemon_icon = pg.transform.scale(pokemon_icon, (icon_size, icon_size))
                
                # Flip if facing right
                if self.direction == Direction.RIGHT:
                    pokemon_icon = pg.transform.flip(pokemon_icon, True, False)
                
                # Add bobbing effect
                bob_offset = math.sin(pg.time.get_ticks() * 0.005) * 4
                
                # Position at player's feet but shifted HIGHER so it's closer to character
                icon_x = self.position.x + (GameSettings.TILE_SIZE - icon_size) // 2
                icon_y = self.position.y + 8 + bob_offset # Shifted up to y + 8
                screen_pos_i = camera.transform_position(Position(icon_x, icon_y))
                screen.blit(pokemon_icon, screen_pos_i)
        else:
            # Normal drawing
            super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

