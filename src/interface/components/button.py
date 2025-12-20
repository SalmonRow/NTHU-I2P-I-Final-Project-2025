from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent
from .label import Label

class Button(UIComponent):
    img_button: Sprite
    img_button_default: Sprite
    img_button_hover: Sprite
    img_button_disabled: Sprite
    hitbox: pg.Rect
    on_click: Callable[[], None] | None
    text: str
    button_label: Label | None


    def __init__(
        self,
        img_path: str | None, img_hovered_path: str | None,
        x: int, y: int, width: int, height: int,
        text: str = '',
        fontsize: int=24,
        text_color: tuple[int,int,int]=(0,0,0),
        on_click: Callable[[], None] | None = None,
        icon_path: str | None = None,
        icon_hover_path: str | None = None,
        icon_size: tuple[int, int] | None = None,
        margin: int = 10
    ):
        self.img_button_default = Sprite(img_path, (width, height))
        self.hitbox = pg.Rect(x, y, width, height)

        self.img_button_hover = Sprite(img_hovered_path, (width, height))
        self.img_button = Sprite(img_path, (width, height)) 
        
        # Create disabled (ghost) sprite
        self.img_button_disabled = Sprite(img_path, (width, height))
        gray_surf = self.img_button_disabled.image.copy()
        gray_surf.fill((100, 100, 100), special_flags=pg.BLEND_RGB_MULT)
        self.img_button_disabled.image = gray_surf

        self.on_click = on_click
        self.text = text
        self.disabled = False
        
        # Icon Logic
        self.has_icon = False
        self.current_icon = None
        self.icon_default = None
        self.icon_hover = None
        self.icon_rect = None
        self.margin = margin
        
        if icon_path:
            self.has_icon = True
            # Load default icon
            if icon_size:
                self.icon_default = Sprite(icon_path, icon_size)
            else:
                self.icon_default = Sprite(icon_path, (32, 32)) # Fallback size if not provided but path is? Or load raw? Sprite needs size.
                
            # Load hover icon
            hover_path = icon_hover_path if icon_hover_path else icon_path
            if icon_size:
                self.icon_hover = Sprite(hover_path, icon_size)
            else:
                 self.icon_hover = Sprite(hover_path, (32, 32))
            
            self.current_icon = self.icon_default
            self.icon_rect = self.current_icon.image.get_rect()
            
            # Initial Position
            self.icon_rect.left = self.hitbox.left + self.margin
            self.icon_rect.centery = self.hitbox.centery

        if self.text:
            self.button_label = Label(
                text=text, 
                x=self.hitbox.centerx, y=self.hitbox.centery,
                color=text_color,
                align='center',
                fontsize=fontsize
            )
            
            # Override alignment if icon is present
            if self.has_icon:
                # User req: text right rect to the right rect of button + margin (actually button right - margin)
                # We retain the Label object but manually control rect in update
                self.button_label.rect.right = self.hitbox.right - self.margin
                self.button_label.rect.centery = self.hitbox.centery
                # Note: Label.align is primarily for internal set_text re-centering. 
                # We might need to adjust logic there if text changes length. 
                # But Label.align doesn't restrict manual rect modification.
            
            # Store original center y for hover effect
            self._text_original_y = self.hitbox.centery
        else:
            self.button_label = None
            self._text_original_y = 0

    @override
    def update(self, dt: float) -> None:
        if self.disabled:
            self.img_button = self.img_button_disabled
            # Disabled icon state? Maybe create a disabled icon too or just use default.
            if self.has_icon:
                self.current_icon = self.icon_default 
            return

        mouse = self.hitbox.collidepoint(input_manager.mouse_pos) 
        if mouse:
            self.img_button = self.img_button_hover
            if self.has_icon:
                self.current_icon = self.icon_hover
            
            # Move text/icon down if it exists
            offset = 4
            target_y = self._text_original_y + offset
            
            if self.button_label:
                self.button_label.rect.centery = target_y
                if self.has_icon:
                     # Re-align right edge just in case
                     self.button_label.rect.right = self.hitbox.right - self.margin
            
            if self.has_icon:
                self.icon_rect.centery = target_y
                self.icon_rect.left = self.hitbox.left + self.margin
                
            if input_manager.mouse_pressed(1):
                if self.on_click != None: 
                    self.on_click()
        else: #if it's not hovered
            self.img_button = self.img_button_default
            if self.has_icon:
                self.current_icon = self.icon_default
            
            # Reset positions
            if self.button_label:
                self.button_label.rect.centery = self._text_original_y
                if self.has_icon:
                     self.button_label.rect.right = self.hitbox.right - self.margin
            
            if self.has_icon:
                self.icon_rect.centery = self._text_original_y
                self.icon_rect.left = self.hitbox.left + self.margin

    @override
    def draw(self, screen: pg.Surface) -> None:

        _ = screen.blit(self.img_button.image, self.hitbox)
        
        if self.has_icon:
            screen.blit(self.current_icon.image, self.icon_rect)
            
        if self.button_label:
            # Optionally darken label if disabled, but for now just draw
            self.button_label.draw(screen)

    def set_position(self, x: int, y: int) -> None:
        """Updates the button position and realigns the label."""
        self.hitbox.topleft = (x, y)
        self._text_original_y = self.hitbox.centery
        
        if self.has_icon:
            self.icon_rect.left = self.hitbox.left + self.margin
            self.icon_rect.centery = self.hitbox.centery
        
        if self.button_label:
            if self.has_icon:
                self.button_label.rect.right = self.hitbox.right - self.margin
                self.button_label.rect.centery = self.hitbox.centery
            else:
                self.button_label.rect.center = self.hitbox.center
            

def main():
    import sys
    import os
    
    # Add project root to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.append(project_root)

    pg.init()

    WIDTH, HEIGHT = 800, 800
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Button Test")
    clock = pg.time.Clock()
    
    bg_color = (0, 0, 0)
    def on_button_click():
        nonlocal bg_color
        if bg_color == (0, 0, 0):
            bg_color = (255, 255, 255)
        else:
            bg_color = (0, 0, 0)
        
    button = Button(
        img_path="UI/button_play.png",
        img_hovered_path="UI/button_play_hover.png",
        x=WIDTH // 2 - 100,
        y=HEIGHT // 2 - 150,
        width=200,
        height=60,
        text="Normal",
        on_click=on_button_click
    )
    
    # Test with Icon
    # Assuming we have some icon. using 'ingame_ui/baricon4.png' mentioned in game_ui_manager as star
    # Or just use same button png as icon for test
    button_icon = Button(
        img_path="UI/button_play.png",
        img_hovered_path="UI/button_play_hover.png",
        x=WIDTH // 2 - 100,
        y=HEIGHT // 2 + 50,
        width=200,
        height=60,
        text="With Icon",
        icon_path="ingame_ui/baricon4.png", # Hopefully exists, otherwise it might error if sprite loading fails
        icon_size=(32, 32),
        margin=20,
        on_click=on_button_click
    )
    
    running = True
    dt = 0
    
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            input_manager.handle_events(event)
        
        dt = clock.tick(60) / 1000.0
        button.update(dt)
        button_icon.update(dt)
        
        input_manager.reset()
        
        _ = screen.fill(bg_color)
        
        button.draw(screen)
        button_icon.draw(screen)
        
        pg.display.flip()
    
    pg.quit()


if __name__ == "__main__":
    main()
