import pygame as pg
import random
import math
from src.utils import GameSettings, Logger
from src.core.services import resource_manager, input_manager
from src.interface.components.label import Label

class ItemObtainedOverlay:
    def __init__(self, close_callback):
        self.close_callback = close_callback
        self.active = False
        
        self.item_name = ""
        self.item_count = 0
        self.item_sprite = None
        
        # UI Elements
        self.title_label = Label.from_center("OBTAINED", color=(255, 215, 0), offset_y=-100, fontsize=40)
        self.name_label = None # Created dynamically
        self.skip_label = Label.from_bottom_center("Press SPACE to continue", color=(200, 200, 200), offset_y=-50, fontsize=20)
        
        # Background
        self.dim_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.dim_surface.fill((0, 0, 0))
        self.dim_surface.set_alpha(200) # Dim amount
        
        # Particles
        self.particles = []
        try:
            self.star_img = resource_manager.get_image("ingame_ui/poke_soul.png")
        except Exception:
            Logger.warning("Particle image not found, using fallback circle.")
            self.star_img = None
            
        if not self.star_img:
             # Fallback
             self.star_img = pg.Surface((10, 10), pg.SRCALPHA)
             pg.draw.circle(self.star_img, (255, 255, 100), (5, 5), 5)

    def show(self, item_name: str, count: int, sprite_path: str = None):
        self.item_name = item_name
        self.item_count = count
        self.active = True
        
        # Load Sprite
        if sprite_path:
            self.item_sprite = resource_manager.get_image(sprite_path)
        else:
            # Try to infer or fallback
             from src.core.data_loader import DataLoader
             data = DataLoader.instance().get_item_data(item_name)
             path = data.get('sprite_path', 'items/potion.png') # Fallback
             self.item_sprite = resource_manager.get_image(path)

        if self.item_sprite:
             # Scale up for display
             self.item_sprite = pg.transform.scale(self.item_sprite, (64, 64))
        
        # Create Labels
        text = f"{item_name} x{count}"
        self.name_label = Label.from_center(text, color=(255, 255, 255), offset_y=60, fontsize=30)
        
        # Init Particles burst
        self.spawn_particles()
        
    def spawn_particles(self):
        center_x, center_y = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            self.particles.append({
                "x": center_x,
                "y": center_y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 1.0, # seconds
                "scale": random.uniform(0.5, 1.5)
            })

    def update(self, dt: float):
        if not self.active:
            return

        if input_manager.key_pressed(pg.K_SPACE):
            self.active = False
            if self.close_callback:
                self.close_callback()
            return
            
        # Update Particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= dt * 1.5
            
        self.particles = [p for p in self.particles if p["life"] > 0]
        
        if len(self.particles) < 5:
             # Keep emitting some
             self.spawn_particles()

    def draw(self, screen: pg.Surface):
        if not self.active:
            return
            
        # 1. Dim Background
        screen.blit(self.dim_surface, (0,0))
        
        # 2. Draw Particles (Behind sprite)
        center_x, center_y = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2
        
        for p in self.particles:
            alpha = int(p["life"] * 255)
            if alpha < 0: alpha = 0
            
            size = int(16 * p["scale"] * p["life"])
            if size <= 0: continue
            
            # Simple colored rect fallback or image
            img = pg.transform.scale(self.star_img, (size, size))
            img.set_alpha(alpha)
            
            # Rotate for effect?
            # img = pg.transform.rotate(img, p["life"] * 360)
            
            screen.blit(img, (int(p["x"]) - size//2, int(p["y"]) - size//2))

        # 3. Draw Sprite
        if self.item_sprite:
            rect = self.item_sprite.get_rect(center=(center_x, center_y))
            screen.blit(self.item_sprite, rect)
            
        # 4. Draw Text
        self.title_label.draw(screen)
        if self.name_label:
            self.name_label.draw(screen)
        self.skip_label.draw(screen)
