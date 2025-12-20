from __future__ import annotations
import pygame as pg
from src.core.services import resource_manager
from .component import UIComponent

class Icon(UIComponent):
    def __init__(self, image_path: str, x: int, y: int, size: tuple[int, int]):
        super().__init__()
        self.image = resource_manager.get_image(image_path)
        self.image = pg.transform.scale(self.image, size)
        self.rect = self.image.get_rect(topleft=(x, y))

    def set_position(self, x: int, y: int):
        self.rect.topleft = (x, y)

    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        screen.blit(self.image, self.rect)
