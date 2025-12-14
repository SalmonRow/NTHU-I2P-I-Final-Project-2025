import pygame as pg
from src.utils import GameSettings, Logger
from typing import List, Any
from src.interface.components.label import Label
from src.core.services import resource_manager

class Monster:
    def __init__(self, name, hp, max_hp, level, sprite_path):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.level = level
        self.sprite_path = sprite_path

class MonsterListComponent:
    PANEL_PATH = "UI/raw/UI_Flat_InputField01a.png"
    PANEL_PATH = "UI/raw/UI_Flat_InputField01a.png"
    # PANEL_SIZE Removed - we calculate dynamic size
    SPRITE_SIZE = 60
    HOVER_BORDER_COLOR = (255, 255, 255)
    HOVER_BORDER_WIDTH = 7

    def __init__(self, x: int, y: int, width: int, height: int, monster_list: List[Monster], on_click=None):
        self.rect = pg.Rect(x, y, width, height)
        self.monsters = monster_list
        self.line_height = 80
        self.monster_image = {}
        self.scroll_offset = 0
        
        self.on_click = on_click
        self.hovered_index = -1

        # Scale panel to fit the component width (minus some padding if desired, or full width)
        # 10px padding on each side? Just full width for now inside the scroll area.
        self._panel_surface = self._load_and_scale(self.PANEL_PATH, (self.rect.width, self.line_height - 5))

    def _load_and_scale(self, path: str, size: tuple[int,int]):
        img = resource_manager.get_image(path)
        return pg.transform.scale(img, size)
        
    def _get_monster_sprites(self, path: str):
        if path not in self.monster_image:
            self.monster_image[path] = self._load_and_scale(path, (self.SPRITE_SIZE, self.SPRITE_SIZE))
        return self.monster_image[path]

    def update(self, dt):
        from src.core.services import input_manager
        
        # Only scroll if mouse is somewhat over the area? Or global?
        # Let's check mouse position for better UX
        mx, my = input_manager.get_mouse_pos()
        if self.rect.collidepoint(mx, my):
            scroll_speed = 20
            
            # Assuming input_manager works like: (0, 0) if no scroll, (0, 1) up, (0, -1) down?
            # Or standard pg.event.get() loop elsewhere handles it.
            # If input_manager doesn't expose scroll, we might need to check key presses or rely on scene passing events.
            # Checking typical input_manager implementation... assuming standard keys for now if scroll not avail.
            if input_manager.get_scroll_y() > 0: # Scroll Up
                self.scroll_offset += scroll_speed
            elif input_manager.get_scroll_y() < 0: # Scroll Down
                self.scroll_offset -= scroll_speed
            
            # Simple Clamping
            # Top limit: 0 (can't pull down to see empty space above first item)
            self.scroll_offset = min(0, self.scroll_offset)
            
            # Bottom limit: Calculate total height vs visible height
            total_content_height = len(self.monsters) * self.line_height
            visible_height = self.rect.height
            min_scroll = -(total_content_height - visible_height)
            
            if total_content_height > visible_height:
                self.scroll_offset = max(min_scroll, self.scroll_offset)
            else:
                self.scroll_offset = 0
                
            # Check Hover / Click
            # Relative Y within the list content
            rel_y = my - (self.rect.top + 5 + self.scroll_offset)
            index = int(rel_y // self.line_height)
            
            if 0 <= index < len(self.monsters):
                self.hovered_index = index
                
                if input_manager.mouse_pressed(1):
                    if self.on_click:
                        monster = self.monsters[index]
                        self.on_click(monster)
        else:
            self.hovered_index = -1

    def draw(self, screen: pg.Surface):
        # Save current clip logic
        original_clip = screen.get_clip()
        
        # Set clip to our rect
        screen.set_clip(self.rect)
        
        try:
            y_pos = self.rect.top + 5 + self.scroll_offset
    
            TEXT_COLOR = (5, 5, 5)
            SPRITE_OFFSET_X = 10
            TEXT_OFFSET_X = self.SPRITE_SIZE + SPRITE_OFFSET_X + 5
    
            for i, monster in enumerate(self.monsters):
                # Optimization: Don't draw if completely out of view
                # Standard line height is 80
                if y_pos > self.rect.bottom:
                    break
                
                if y_pos + self.line_height < self.rect.top:
                    y_pos += self.line_height
                    continue
                    
                # Draw Selection/Hover Background
    
                #a background / panels for each monsers
                screen.blit(self._panel_surface, (self.rect.left, y_pos))
                if i == self.hovered_index:
                    highlight_rect = pg.Rect(self.rect.left, y_pos, self.rect.width, self.line_height)
                    pg.draw.rect(screen, self.HOVER_BORDER_COLOR, highlight_rect, self.HOVER_BORDER_WIDTH)
    
                #the monsters
                sprite = self._get_monster_sprites(monster.get('menu_sprite_path', 'menu_sprites/menusprite1.png'))
                sprite_x = self.rect.left + SPRITE_OFFSET_X
                sprite_y = y_pos + (self.line_height - sprite.get_height()) // 2 - 10
                screen.blit(sprite, (sprite_x, sprite_y))
    
                #texts
                name_text = f"Lv.{monster['level']} {monster['name']}"
                name_label = Label(
                    name_text,
                    x=self.rect.left + TEXT_OFFSET_X,
                    y=y_pos + 10, 
                    color=TEXT_COLOR
                )
                name_label.draw(screen)
    
                hp_text = f"HP: {monster['hp']} / {monster['max_hp']}"
                hp_label = Label(
                    hp_text,
                    x=self.rect.left + TEXT_OFFSET_X,
                    y=y_pos + self.line_height // 2,
                    color=TEXT_COLOR,
                    fontsize=18
                )
                hp_label.draw(screen)
    
                y_pos += self.line_height
                
        finally:
            # Always restore clip even if error
            screen.set_clip(original_clip)



        