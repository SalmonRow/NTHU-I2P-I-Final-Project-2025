from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from typing import Callable, override
from .component import UIComponent

class Slider(UIComponent):
    def __init__(
            self,
            x: int, y: int, 
            width: int, height: int,
            min_val: float, max_val: float,initial_val: float,
            val_change: Callable[[float], None],
            bar_path: str, handle_path: str,
            label: str
    ):
        super().__init__()

        self.rect = pg.Rect(x,y,width,height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.val_change = val_change
        self.dragging = False

        self.label = label
        self.font = pg.font.Font(None, height)

        handle_size = height

        self.bar_img = self._load_and_scale(bar_path, width, height)
        self.handle_img = self._load_and_scale(handle_path, handle_size, handle_size)

        self.handle_rect = self.handle_img.get_rect()
        self.handle_half_width = self.handle_rect.width // 2

        self._update_handle_pos()

    def _load_and_scale(self, path: str, width: int, height: int):
        try:
            img = pg.image.load(path).convert_alpha()
            return pg.transform.scale(img, (width, height))
        except pg.error:
            missing = pg.Surface((width,height))
            missing.fill((255,0,255))
            return missing

    def _update_handle_pos(self):    
        normalized = (self.value - self.min_val) / (self.max_val - self.min_val)

        d_range = self.rect.width - (2*self.handle_half_width)
        handle_center = self.rect.left + self.handle_half_width + (normalized * d_range)

        self.handle_rect.center = (int(handle_center), self.rect.centery)

    def _get_value_from_mouse(self, mouse_x: int):
        x_min = self.rect.left + self.handle_half_width
        x_max = self.rect.right - self.handle_half_width

        prevent_x = max(x_min, min(mouse_x, x_max))
        normalized = (prevent_x - x_min) / (x_max - x_min)
        new_val = self.min_val + (normalized * (self.max_val - self.min_val))
        return new_val
    
    @override
    def update(self, dt: float):
        mouse_pos = input_manager.mouse_pos 
        mouse_down = input_manager.mouse_pressed(1)

        if self.handle_rect.collidepoint(mouse_pos) and mouse_down:
            self.dragging = True


        if self.dragging and pg.mouse.get_pressed()[0]:
            new_value = self._get_value_from_mouse(mouse_pos[0])
            if abs(new_value - self.value) > 0.01:
                self.value = new_value
                self.val_change(self.value)
                self._update_handle_pos()

        if not pg.mouse.get_pressed()[0]:
            self.dragging = False

    @override
    def draw(self, screen: pg.Surface):
        bar_x = self.rect.left
        bar_y = self.rect.centery - (self.bar_img.get_height()//2)
        screen.blit(self.bar_img, (bar_x, bar_y))

        screen.blit(self.handle_img, self.handle_rect)

        #labels
        label_txt = f"{self.label}: {int(self.value)}"
        label_f = self.font.render(label_txt, True, (255,255,255))

        label_x = self.rect.left
        label_y = self.rect.top - (self.handle_half_width // 2) - 40
        screen.blit(label_f, (label_x, label_y))

        






    




        