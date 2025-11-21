import pygame as pg
from src.utils import GameSettings, Logger
from typing import List, Any
from src.interface.components.label import Label

class Monster:
    def __init__(self, name, hp, max_hp, level, sprite_path):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.level = level
        self.sprite_path = sprite_path

class MonsterListComponent:
    PANEL_PATH = "assets/images/UI/raw/UI_Flat_InputField01a.png"
    PANEL_SIZE = (320, 60)
    SPRITE_SIZE = 60
    FILL_PLACEHOLDER = (255,0,255)

    def __init__(self, x: int, y: int, width: int, height: int, monster_list: List[Monster]):
        self.rect = pg.Rect(x, y, width, height)
        self.monsters = monster_list
        self.line_height = 60
        self.monster_image = {}
        self.scroll_offset = 0

        self._panel_surface = self._load_and_scale(self.PANEL_PATH, self.PANEL_SIZE) #load panel here

    def _load_and_scale(self, path: str, size: tuple[int,int]):
        try:
            image = pg.image.load(path).convert_alpha()
            return pg.transform.scale(image, size)
        except pg.error as e:
            Logger.warning(f'Failed to load asset {path} : {e}')
            placerholder = pg.Surface(size)
            placerholder.fill(self.FILL_PLACEHOLDER)
            return placerholder
        
    def _get_monster_sprites(self, path: str):
        if path not in self.monster_image:
            complete_path = f'assets/images/{path}'
            self.monster_image[path] = self._load_and_scale(complete_path, (self.SPRITE_SIZE, self.SPRITE_SIZE))
        return self.monster_image[path]

    def update(self, dt):
        pass

    def draw(self, screen: pg.Surface):
        y_pos = self.rect.top + 5 + self.scroll_offset

        TEXT_COLOR = (5, 5, 5)
        SPRITE_OFFSET_X = 5
        TEXT_OFFSET_X = self.SPRITE_SIZE + SPRITE_OFFSET_X + 5

        for monster in self.monsters:
            if y_pos > self.rect.bottom:
                break

            #a background / panels for each pokemonts
            screen.blit(self._panel_surface, (self.rect.left, y_pos))

            #the monsters
            sprite = self._get_monster_sprites(monster['sprite_path'])
            sprite_x = self.rect.left + SPRITE_OFFSET_X
            sprite_y = y_pos + (self.line_height - sprite.get_height()) // 2
            screen.blit(sprite, (sprite_x, sprite_y))

            #texts
            name_text = f"{monster["name"]} (Lv.{monster["level"]})"
            name_label = Label(
                name_text,
                x=self.rect.left + TEXT_OFFSET_X,
                y=y_pos + 5, 
                color=TEXT_COLOR
            )
            name_label.draw(screen)

            hp_text = f"HP: {monster['hp']} / {monster['max_hp']}"
            hp_label = Label(
                hp_text,
                x=self.rect.left + TEXT_OFFSET_X,
                y=y_pos + self.line_height //2 + 5,
                color=TEXT_COLOR,
                fontsize=18
            )
            hp_label.draw(screen)

            y_pos += self.line_height



        