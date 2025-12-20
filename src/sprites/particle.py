import pygame as pg
import random
from src.utils import Position, GameSettings

WHITE = (255,255,255)

class Particle:
    def __init__(self, x: float, y: float, color: tuple = WHITE):
        self.position = Position(x, y)
        self.lifetime = 0.5  # Seconds the particle lasts
        self.size = random.randint(5, 10)
        self.color = color 
        self.alpha = 255
        
    def update(self, dt: float) -> bool:
        """Updates particle, returns False if it should be removed."""
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False
            
        # Fade out effect
        self.alpha = max(0, int(255 * (self.lifetime / 0.5)))
        return True

    def draw(self, screen: pg.Surface, camera):
        screen_pos = camera.transform_position_as_position(self.position)
        
        # Create a surface for transparency
        s = pg.Surface((self.size, self.size))
        s.set_alpha(self.alpha)
        s.fill(self.color)
        
        screen.blit(s, (screen_pos.x, screen_pos.y - 4))
