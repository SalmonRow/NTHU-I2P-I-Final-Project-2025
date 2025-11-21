from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent
from .button import Button

class Popup(UIComponent):
    frame_img: pg.Surface
    frame_rect: pg.Rect

    interactive_components: list[UIComponent]
    internal_buttons: list[Button]
    
    def __init__(
            self, 
            frame_path: str,
            size: tuple[int, int], 
            close_callback: Callable[[], None]
    ):
        super().__init__()

        self.frame_img = pg.image.load(frame_path).convert_alpha()

        frame_width = int(size[0] * 0.6)
        frame_height = int(size[1] * 0.7)
        self.frame_img = pg.transform.scale(self.frame_img, (frame_width, frame_height))
        self.frame_rect = self.frame_img.get_rect(
            center=(size[0] // 2, size[1] // 2)
        )

        #every popup window will have these components built in
        self.interactive_components = []
        self.internal_buttons = []

        internal_close_button = Button(
            "UI/button_x.png", 
            "UI/button_x_hover.png",
            self.frame_rect.right - 80, self.frame_rect.top + 20, 
            60, 60, 
            on_click=close_callback
        )
        self.internal_buttons.append(internal_close_button)
        self.interactive_components.append(internal_close_button)


    @override
    def update(self, dt: float) -> None:
        for component in self.interactive_components:
            component.update(dt)

    @override
    def draw(self, screen: pg.Surface) -> None:
        screen.blit(self.frame_img, self.frame_rect)

        for component in self.interactive_components:
            component.draw(screen)

