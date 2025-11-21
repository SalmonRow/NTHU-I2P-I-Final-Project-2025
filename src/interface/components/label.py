import pygame as pg
from src.utils import GameSettings

class Label:
    FONT_PATH = "assets/fonts/Minecraft.ttf"
    DEFAUL_SIZE = 24
    BLACK = (0,0,0)

    def __init__(self, text: str, x: int, y: int,
                 color: tuple[int,int,int]=BLACK, align: str = "topleft", fontsize: int = DEFAUL_SIZE):
        self.text = text
        self.color = color
        self.align = align

        self.font = pg.font.Font(self.FONT_PATH, fontsize)
        self._render_text(x,y)

    def _render_text(self, x, y):
        self.surface = self.font.render(self.text, True, self.color)
        self.rect = self.surface.get_rect()

        if self.align == "center":
            self.rect.center = (x,y)
        elif self.align == "topleft":
            self.rect.topleft = (x,y)
        elif self.align == "topright":
            self.rect.topright = (x,y)
        elif self.align == "midbottom":
            self.rect.midbottom = (x,y)

    def set_text(self, new_text: str):
        if self.text != new_text:
            self.text = new_text

            self._render_text(self.rect.x, self.rect.y)

    def draw(self, screen: pg.Surface):
        screen.blit(self.surface, self.rect)

    @classmethod
    def from_center(
        cls, text: str,
        color: tuple[int,int,int] = BLACK, 
        offset_x: int=0, offset_y: int=0, fontsize: int=DEFAUL_SIZE 
    ):
        center_x = GameSettings.SCREEN_WIDTH // 2 + offset_x
        center_y = GameSettings.SCREEN_HEIGHT // 2 + offset_y

        return cls(text, center_x, center_y, color, align="center",fontsize=fontsize)
    
    @classmethod
    def from_bottom_center(
        cls, text: str,
        color: tuple[int,int,int] = BLACK, 
        offset_y: int=0, fontsize: int=DEFAUL_SIZE 
    ):
        center_x = GameSettings.SCREEN_WIDTH // 2 
        bottom_y = GameSettings.SCREEN_HEIGHT + offset_y
        
        return cls(text, center_x, bottom_y, color, align="center",fontsize=fontsize)
        
    



        