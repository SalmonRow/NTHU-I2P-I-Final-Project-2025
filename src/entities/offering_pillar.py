import pygame as pg
from src.entities.entity import Entity
from src.core import GameManager
from src.utils import GameSettings, Logger, Position, PositionCamera
from src.sprites import Sprite

class OfferingPillar(Entity):
    def __init__(self, x: int, y: int, game_scene):
        # We manually init what we need, skipping Entity.__init__ which forces 4x4 animation
        
        self.scene = game_scene
        self.game_manager = game_scene.game_manager
        # Shift position so the 3x3 structure is centered/anchored on the original tile (x, y)
        # x -= 1 tile, y -= 2 tiles
        self.position = Position((x - 1) * GameSettings.TILE_SIZE, (y - 2) * GameSettings.TILE_SIZE)
        
        # Load simple sprite (3x size)
        self.sprite = Sprite("UI/cooked/Offering_pillar.png", (GameSettings.TILE_SIZE * 3, GameSettings.TILE_SIZE * 3))
        
        self.hitbox = pg.Rect(
            self.position.x, self.position.y,
            GameSettings.TILE_SIZE * 3, GameSettings.TILE_SIZE * 3
        )
        
        # For Y-sorting
        self.sort_y = self.hitbox.bottom - GameSettings.TILE_SIZE
        
        # Indicator for healing needed
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.triggered = False 

    def _needs_healing(self) -> bool:
        """Check if any pokemon in player's party needs healing."""
        party = self.game_manager.bag.monsters
        return any(m.get('hp', 0) < m.get('max_hp', 1) for m in party)

    def update(self, dt: float) -> None:
        from src.core.services import input_manager
        
        self.hitbox.topleft = (self.position.x, self.position.y)
        self.sort_y = self.hitbox.bottom - GameSettings.TILE_SIZE
        
        # Check collision with player
        player = self.game_manager.player
        self.is_colliding = player and player.hitbox.colliderect(self.hitbox)
        self.should_show_indicator = self.is_colliding and self._needs_healing()
        
        if self.should_show_indicator:
            self.scene.ui_manager.show_notification("Press [YELLOW]F[WHITE] to Offer", duration=0.6, notification_type="interaction")
            if input_manager.key_pressed(pg.K_f):
                curr_overlay = self.scene.ui_manager.current_overlay
                if curr_overlay != "offering":
                    self.scene.ui_manager.open_offering_menu()
        else:
            # Auto-close if we walk away or heal up
            curr_overlay = self.scene.ui_manager.current_overlay
            if curr_overlay == "offering":
                self.scene.ui_manager.toggle_overlay(None)

    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        # Draw sprite aligned with hitbox (both are 3x3)
        screen.blit(self.sprite.image, camera.transform_rect(self.hitbox))
        
        # Draw exclamation mark above player if healing is needed and colliding
        if hasattr(self, 'should_show_indicator') and self.should_show_indicator:
            player = self.game_manager.player
            if player:
                # Position exclamation slightly above player's head
                excl_pos = pg.Rect(
                    player.position.x + GameSettings.TILE_SIZE // 4,
                    player.position.y - GameSettings.TILE_SIZE // 2,
                    GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2
                )
                screen.blit(self.warning_sign.image, camera.transform_rect(excl_pos))
        
        if GameSettings.DRAW_HITBOXES:
            pg.draw.rect(screen, (0, 0, 255), camera.transform_rect(self.hitbox), 1)
