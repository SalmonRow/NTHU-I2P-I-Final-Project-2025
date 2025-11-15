from __future__ import annotations
import pygame as pg

class Scene:
    def __init__(self) -> None:
        ...
        #should there be super() somthing here ?

    def enter(self) -> None:
        ...

    def exit(self) -> None:
        ...

    def update(self, dt: float) -> None:
        ...

    def draw(self, screen: pg.Surface) -> None:
        ...