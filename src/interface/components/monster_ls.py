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
        self.rect = pg.Rect(x, y, width, height - 11)
        # Create a copy and Sort: Evolvable first, then Name
        self.monsters = list(monster_list) if monster_list else []
        self.monsters.sort(key=lambda m: (not m.get('can_evolve', False), m.get('name', '')))

        self.line_height = 80
        self.monster_image = {}
        self.scroll_offset = 0
        
        self.on_click = on_click
        self.hovered_index = -1

        # Scale panel to fit the component width (minus some padding if desired, or full width)
        # 10px padding on each side? Just full width for now inside the scroll area.
        self._panel_surface = self._load_and_scale(self.PANEL_PATH, (self.rect.width, self.line_height - 5))

    def set_monsters(self, monster_list: List[Monster]):
        """Updates the list of monsters and re-sorts them."""
        self.monsters = list(monster_list) if monster_list else []
        self.monsters.sort(key=lambda m: (not m.get('can_evolve', False), m.get('name', '')))


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
        # Use subsurface for strict clipping
        # This creates a virtual surface that is mapped to the scroll area
        # All drawing on 'sub_screen' uses coordinates relative to self.rect.topleft (0,0)
        sub_screen = screen.subsurface(self.rect)
        
        y_pos = 5 + self.scroll_offset # Relative Y start

        TEXT_COLOR = (5, 5, 5)
        SPRITE_OFFSET_X = 10
        TEXT_OFFSET_X = self.SPRITE_SIZE + SPRITE_OFFSET_X + 5

        for i, monster in enumerate(self.monsters):
            # Check relative bounds
            if y_pos > self.rect.height:
                break
            
            if y_pos + self.line_height < 0:
                y_pos += self.line_height
                continue
                
            # Draw Selection/Hover Background
            # Relative 0,0
            sub_screen.blit(self._panel_surface, (0, y_pos))
            
            highlight_rect = pg.Rect(0, y_pos, self.rect.width, self.line_height)
            
            # Evolution Border (Green) - Permanent if can evolve
            if monster.get('can_evolve'):
                 pg.draw.rect(sub_screen, (0, 255, 0), highlight_rect, self.HOVER_BORDER_WIDTH)
            # Hover Border (White) - If hovered (and not evolvable? or overlay?)
            elif i == self.hovered_index:
                pg.draw.rect(sub_screen, self.HOVER_BORDER_COLOR, highlight_rect, self.HOVER_BORDER_WIDTH)

            #the monsters
            sprite = self._get_monster_sprites(monster.get('menu_sprite_path', 'menu_sprites/menusprite1.png'))
            sprite_x = SPRITE_OFFSET_X # Relative X
            sprite_y = y_pos + (self.line_height - sprite.get_height()) // 2 - 10
            sub_screen.blit(sprite, (sprite_x, sprite_y))

            #texts
            # Note: Label expects x,y to position its internal rect. 
            # We must pass RELATIVE coordinates here.
            name_text = f"Lv.{monster['level']} {monster['name']}"
            name_label = Label(
                name_text,
                x=TEXT_OFFSET_X, 
                y=y_pos + 10, 
                color=TEXT_COLOR
            )
            name_label.draw(sub_screen)

            hp_text = f"HP: {monster['hp']} / {monster['max_hp']}"
            hp_label = Label(
                hp_text,
                x=TEXT_OFFSET_X,
                y=y_pos + self.line_height // 2,
                color=TEXT_COLOR,
                fontsize=18
            )
            hp_label.draw(sub_screen)

            # Evolution Indicator
            if monster.get('can_evolve'):
                 evo_label = Label(
                     "Evo !", 
                     x=5, # Relative X
                     y=y_pos + 5,
                     color=(0, 255, 0), # Green
                     fontsize=16
                 )
                 evo_label.draw(sub_screen)

            y_pos += self.line_height



        