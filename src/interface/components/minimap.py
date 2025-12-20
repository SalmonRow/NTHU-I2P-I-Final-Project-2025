import pygame as pg
from typing import override
from src.utils import GameSettings, Logger
from src.core.managers.game_manager import GameManager
from src.interface.components.component import UIComponent

class MiniMap(UIComponent):
    ZOOM_SCALE = 0.18 # 64px tile -> 16px tile on minimap

    def __init__(self, game_scene, x: int = 10, y: int = 10, size: int = 200, zoom_scale: float = None, auto_zoom: bool = False):
        self.scene = game_scene
        self.game_manager = game_scene.game_manager
        self.rect = pg.Rect(x, y, size, size)
        
        # Allow custom zoom, default to class constant if not provided
        self.zoom_scale = zoom_scale if zoom_scale is not None else self.ZOOM_SCALE
        self.auto_zoom = auto_zoom
        
        # We cache the FULL map at ZOOM_SCALE
        self.cached_map_surface = None
        self.current_map_key = ""
        
        # Style settings
        self.border_color = (158, 158, 158)
        self.border_color_outer = (100, 100, 100)
        # self.border_color = (255, 255, 255)
        self.border_width = 2
        self.bg_color = (0, 0, 0, 150) # Semi-transparent black
        
        # Dot colors
        self.color_player = (0, 100, 255) # Blue
        self.color_enemy = (255, 50, 50)   # Red
        self.color_online = (50, 255, 50)  # Green

    @override
    def update(self, dt: float) -> None:
        # Check if map changed
        if self.game_manager.current_map_key != self.current_map_key:
            self._refresh_map_surface()
            
    @override
    def draw(self, screen: pg.Surface) -> None:
        # 1. Draw Background
        pg.draw.rect(screen, self.bg_color, self.rect)
        
        if not self.cached_map_surface:
            return

        # 2. Calculate Camera View
        # We want to center on the player
        if self.game_manager.player:
            # Player world pos
            px_world = self.game_manager.player.position.x
            py_world = self.game_manager.player.position.y
            
            # Convert to MiniMap Coordinate Space (Full Map)
            px_mm = px_world * self.zoom_scale
            py_mm = py_world * self.zoom_scale
            
            # View Rect Size (MiniMap Window)
            view_w = self.rect.width
            view_h = self.rect.height
            
            # Top-Left of the view rect in MiniMap Space
            view_x = px_mm - (view_w / 2)
            view_y = py_mm - (view_h / 2)
            
            # Clamp to Map Boundaries
            map_w = self.cached_map_surface.get_width()
            map_h = self.cached_map_surface.get_height()
            
            # Clamp X
            view_x = max(0, min(view_x, map_w - view_w))
            # Clamp Y
            view_y = max(0, min(view_y, map_h - view_h))
            
            # Also handle case where map is smaller than view
            if map_w < view_w:
                view_x = (map_w - view_w) / 2 # Center it
            if map_h < view_h:
                view_y = (map_h - view_h) / 2 # Center it

            view_rect = pg.Rect(view_x, view_y, view_w, view_h)
            
            # 3. Blit Subsection of Map
            # Use subsurface for clipping (or direct blit with area)
            # We need to handle out-of-bounds area calculation if we centered smaller map
            # Safest is to just blit what we can.
            
            # Source Rect on the cached surface
            src_rect = view_rect.copy()
            
            # Destination on screen (self.rect)
            # If map is smaller than view, valid area is smaller
            start_x = 0
            start_y = 0
            
            # Fix negative values (centering logic might give negative view_x)
            dest_x = self.rect.x
            dest_y = self.rect.y
            
            if view_x < 0:
                dest_x += abs(view_x)
                start_x = abs(view_x) # Skip this much on dest? No.
                src_rect.x = 0
                src_rect.width = map_w
            else:
                 src_rect.x = view_x
            
            if view_y < 0:
                 dest_y += abs(view_y)
                 src_rect.y = 0
                 src_rect.height = map_h
            else:
                 src_rect.y = view_y

            # Ensure we don't read past end
            if src_rect.right > map_w:
                src_rect.width = map_w - src_rect.x
            if src_rect.bottom > map_h:
                src_rect.height = map_h - src_rect.y

            screen.blit(self.cached_map_surface, (dest_x, dest_y), src_rect)
            
            # Helper to transform world pos to screen pos relative to this view
            def world_to_screen(wx, wy):
                mx = wx * self.zoom_scale
                my = wy * self.zoom_scale
                
                # Relative to view_rect
                rel_x = mx - view_x
                rel_y = my - view_y
                
                # Absolute screen pos
                sx = self.rect.x + rel_x
                sy = self.rect.y + rel_y
                
                # If map is centered (smaller than view), we adjusted dest_x/y
                # If view_x was negative, we shifted dest_x by abs(view_x).
                # rel_x calculated above uses negative view_x, so mx - (-10) = mx + 10.
                # sx = self.rect.x + mx + 10. This is correct logic for centering visually but
                # let's double check.
                # If view_x = -10 (map is 20px smaller than view 200) -> centered.
                # dest_x = rect.x + 10.
                # We blitted map at dest_x.
                # Point 0,0 on map is at dest_x.
                # Formula: sx = rect.x + (mx - view_x) = rect.x + mx + 10. Correct.
                
                return (sx, sy)

            # 4. Draw Entities (Clipped to MiniMap Rect?)
            # Technically we should clip, but dots slightly outside is ok or we can set clip
            screen.set_clip(self.rect)
            
            # Enemies
            for enemy in self.game_manager.current_enemy_trainers:
                 if hasattr(enemy, 'position'):
                     ex, ey = enemy.position.x, enemy.position.y
                 elif hasattr(enemy, 'animation'):
                     ex, ey = enemy.animation.rect.center
                 else:
                     continue
                 
                 screen_pos = world_to_screen(ex, ey)
                 pg.draw.circle(screen, self.color_enemy, screen_pos, 3)

            # Online Players
            if self.scene.online_manager:
                online_players = self.scene.online_manager.get_list_players()
                for p_data in online_players:
                    if p_data.get("map") == self.game_manager.current_map_key:
                        ox = p_data.get("x", 0)
                        oy = p_data.get("y", 0)
                        screen_pos = world_to_screen(ox, oy)
                        pg.draw.circle(screen, self.color_online, screen_pos, 3)

            # Player
            if self.game_manager.player:
                screen_pos = world_to_screen(px_world, py_world)
                pg.draw.circle(screen, self.color_player, screen_pos, 4)
            
            # Reset Clip
            screen.set_clip(None)
                
        # 5. Draw Border
        pg.draw.rect(screen, self.border_color, self.rect, self.border_width + 6)
        pg.draw.rect(screen, self.border_color_outer, self.rect, self.border_width)

    def _refresh_map_surface(self):
        self.current_map_key = self.game_manager.current_map_key
        current_map = self.game_manager.current_map
        
        # The map class has `_surface` (pre-baked).
        # We scale it by ZOOM_SCALE
        original_surf = current_map._surface
        w = original_surf.get_width()
        h = original_surf.get_height()
        
        if self.auto_zoom:
             # Calculate scale to fill the view (No black bars)
             # We want the map to completely cover the rect.
             # So we need the LARGER scale of (view/map_w) vs (view/map_h)
             scale_x = self.rect.width / w
             scale_y = self.rect.height / h
             self.zoom_scale = max(scale_x, scale_y)
        
        new_size = (int(w * self.zoom_scale), int(h * self.zoom_scale))
        self.cached_map_surface = pg.transform.scale(original_surf, new_size)
        
        Logger.info(f"MiniMap refreshed for {self.current_map_key}. Scale: {self.zoom_scale} (Auto: {self.auto_zoom})")
