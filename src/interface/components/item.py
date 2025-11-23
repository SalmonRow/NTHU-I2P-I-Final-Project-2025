import pygame as pg
from src.utils import GameSettings, Logger
from typing import List, Any
from src.interface.components.label import Label

class Item:
    def __init__(self, name, count, sprite_path):
        self.name = name
        self.count = count
        self.sprite_path = sprite_path

class ItemListComponent:
    SPRITE_SIZE = 40
    LINE_HEIGHT = 50
    FILL_PLACEHOLDER = (255, 0, 255)

    def __init__(self, x: int, y: int, width: int, height: int, item_list: List[Item]):
        self.rect = pg.Rect(x,y,width,height)
        self.items = item_list
        self.line_height = 50
        self.scroll_offset = 0
        self.item_image = {}

    def _load_and_scale(self, path: str, size: tuple[int,int]):
        try:
            image = pg.image.load(path).convert_alpha()
            return pg.transform.scale(image, size)
        except pg.error as e:
            Logger.warning(f'Failed to load asset {path} : {e}')
            placerholder = pg.Surface(size)
            placerholder.fill(self.FILL_PLACEHOLDER)
            return placerholder
        
    def _get_item_sprites(self, path: str):
        if path not in self.item_image:
            complete_path = f'assets/images/{path}'
            self.item_image[path] = self._load_and_scale(complete_path, (self.SPRITE_SIZE, self.SPRITE_SIZE))
        return self.item_image[path]
        

    def update(self, dt):
        pass

    def draw(self, screen: pg.Surface):
        SPRITE_OFFSET_x = 5
        TEXT_OFFSET_X = self.SPRITE_SIZE + SPRITE_OFFSET_x + 5

        y_pos = self.rect.top + 5 + self.scroll_offset

        for item in self.items:
            if y_pos > self.rect.bottom:
                break

            sprite = self._get_item_sprites(item['sprite_path'])
            sprite_x = self.rect.left + SPRITE_OFFSET_x
            sprite_y = y_pos + (self.line_height - sprite.get_height()) // 2
            screen.blit(sprite, (sprite_x, sprite_y))

            name_label = Label(
                item['name'], 
                x=self.rect.left +TEXT_OFFSET_X,
                y=y_pos + (self.line_height // 2) - 10 
            )
            name_label.draw(screen)

            count_label = Label(
                str(item['count']),
                x=self.rect.right - TEXT_OFFSET_X,
                y=y_pos + (self.line_height // 2) - 10
            )
            count_label.draw(screen)

            y_pos += self.line_height


            




    
        