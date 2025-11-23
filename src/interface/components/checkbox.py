from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from typing import Callable, override
from .component import UIComponent
from src.interface.components.label import Label

class Checkbox(UIComponent):

    def __init__(
            self,
            x: int, y: int,
            size: int,
            initial_checked: bool,
            on_toggle: Callable[[bool], None],
            label: str,
            checked_path: str,
            unchecked_path: str
    
    ):
        super().__init__()

        #states
        self.is_checked = initial_checked
        self.on_toggle = on_toggle
        self.label = label

        #Apperance
        self.size = size
        self.checked_img= self._load_and_scale(checked_path, size)
        self.unchecked_img = self._load_and_scale(unchecked_path, size)

        self.rect = self.checked_img.get_rect(topleft=(x,y))
        self.hitbox = self.rect
        self.fonts = pg.font.Font(None, size)

    def _load_and_scale(self, img_path:str, size:int):
        try:
            img = pg.image.load(img_path).convert_alpha()
            return pg.transform.scale(img, (size, size))

        except pg.error:
            missing = pg.Surface((size,size))
            missing.fill((1,2,3))
            return missing
        
    @override
    def update(self, dt: float):
        mouse_pos = input_manager.mouse_pos
        clicked = input_manager.mouse_pressed(1) #left click

        if self.hitbox.collidepoint(mouse_pos) and clicked:
            self.is_checked = not self.is_checked
            self.on_toggle(self.is_checked)

    @override
    def draw(self, screen: pg.Surface):
        current_img = self.checked_img if self.is_checked else self.unchecked_img
        screen.blit(current_img, self.rect)

        label_x = self.rect.right + 10
        lable_y = self.rect.centery
        label_f = Label(
            self.label,
            x=label_x, y=lable_y
        )
        label_f.draw(screen)








    