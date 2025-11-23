import pygame as pg
import threading
import time

from src.scenes.scene import Scene
from src.core.managers import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position, load_img, load_sound
from src.core.services import sound_manager, scene_manager, input_manager
from src.sprites import Sprite, BackgroundSprite
from typing import override, Optional, Dict, Any
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent, Label
import random

GREEN = (0, 200, 0)
RED = (200, 0, 0)
GRAY = (50, 50, 50)
WHITE = (255, 255, 255)

CATCH_ITEM = "Pokeball"
CHANCE = 10
class BattleScene(Scene):
    game_manager: GameManager = None
    online_manager: OnlineManager | None
    sprite_online: Sprite
    #stats
    current_turn: str 
    ended: bool
    result: str | None  

    enem_id: str | None = None
    enem_status: int | None = None

    player_sprite: pg.Surface | None = None
    enem_sprite: pg.Surface | None = None
    
    attack_button: Button
    run_button: Button
    turn_label: Label 
    result_label: Label 
    prompt_label: Label 
    action_hub: Popup
    mons_stat_pan: Popup

    _enemy_turn_delay: float = 1.0 
    _turn_timer: float = 0.0

    ACTION_BUTTON_SIZE = 80
    HP_BAR_WIDTH = 200
    HP_BAR_HEIGHT = 20
    STATS_PAN_SIZE = (520, 130)
    
    def __init__(self, game_manger_instance):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")
        
        #place hodler values
        self.player_mon = {}
        self.enem_mon = {}

        #panels
        self.player_mon_pan = Popup(
            "UI/raw/UI_Flat_Banner03a.png", self.STATS_PAN_SIZE,
            close_callback=None
        )
        self.player_mon_pan.interactive_components = []

        self.enem_mon_pan = Popup(
            "UI/raw/UI_Flat_Banner03a.png", self.STATS_PAN_SIZE,
            close_callback=None
        )
        self.enem_mon_pan.interactive_components = []


        #buttons & labels
        self.atk_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 ,
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE ,
            text="ATTACK",
            on_click=self.atk_action
        )

        self.run_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 + 20 + self.atk_button.hitbox.width, 
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE,
            text="RUN",
            on_click=self.run_action
        )

        self.catch_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 + 40 + self.atk_button.hitbox.width + self.run_button.hitbox.width, 
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE,
            text="CATCH",
            on_click=self.catch_action
        )

        
        self.game_manager = game_manger_instance
        self.turn_label = None
        self.result_label = None
        self.prompt_label = None
        self.current_turn = 'player'
        self.result = None
        self.ended = False
        self.is_wild_encounter = False

    @override
    def enter(self, player_monster, enemy_monster, **kwargs):
        Logger.info(f'Entering Battle... Wild encounter : {kwargs.get('is_wild_encounter', False)}')
        sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")

        self.is_wild_encounter = kwargs.get('is_wild_encounter', False)
        if player_monster and enemy_monster:
            self.player_mon = player_monster
            self.enem_mon = enemy_monster

            player_full = load_img(self.player_mon["battle_sprite_path"])
            enemy_full  = load_img(self.enem_mon["battle_sprite_path"])

            # Slice in half
            P_SCALE = 6.5
            E_SCALE = 3
            w1, h1 = player_full.get_size()
            self.player_sprite = player_full.subsurface(pg.Rect(w1 // 2, 0, w1 // 2, h1))
            pw, ph = int(self.player_sprite.get_width()*P_SCALE), int(self.player_sprite.get_height()*P_SCALE)
            self.player_sprite = pg.transform.scale(self.player_sprite, (pw, ph))

            w2, h2 = enemy_full.get_size()
            self.enem_sprite = enemy_full.subsurface(pg.Rect(0, 0, w2 // 2, h2))
            ew, eh = int(self.enem_sprite.get_width()*E_SCALE), int(self.enem_sprite.get_height()*E_SCALE)
            self.enem_sprite = pg.transform.scale(self.enem_sprite, (ew, eh))


        else:
            #if loading the monsters failed
            self.player_mon = {"name": "Pikachu_fake", "hp": 100, "max_hp": 100, "level": 25, "atk": 60, "defense": 15}
            self.enem_mon = {"name": "Gengar_fake", "hp": 80, "max_hp": 80, "level": 30, "atk": 70, "defense": 15}

        # positions
        self.player_sprite_rect = self.player_sprite.get_rect()
        self.player_sprite_rect.bottomleft = (-20, GameSettings.SCREEN_HEIGHT)

        self.enem_sprite_rect = self.enem_sprite.get_rect()
        self.enem_sprite_rect.topleft = (GameSettings.SCREEN_WIDTH - self.enem_sprite_rect.width - 80, 60)

            
        self.turn_label = Label(
            text=f"Turn: {self.current_turn.upper()}",
            x= 75, y=50, fontsize=30
        )
        self.result_label = Label(
            text="", 
            x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT // 2,
            color=RED, align='center', fontsize=50
        )
        self.prompt_label = Label(
            text="Press SPACE to exit.", 
            x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT - 50,
            color=WHITE, align='center', fontsize=20
        )

    @override
    def exit(self):
        if self.game_manager and self.result:
            self.game_manager.last_battle_result = self.result
            Logger.info(f'Saved battle result: {self.result}')
        
        # Optional: Clear the temporary reference to the enemy trainer
        self.game_manager.current_battle_en = None
        pass
        
    
#ACTIONSSSS
    def catch_action(self):
        # 1. Guards: Check for turn, battle status, and wild encounter status
        if self.current_turn != "player" or self.ended or not self.is_wild_encounter:
            return

        # 2. Check for and consume Pokeball
        if not self.game_manager.bag.has_item(CATCH_ITEM):
            Logger.info(f"Catch failed: No {CATCH_ITEM} available.")
            # In a real game, you would display a message here
            return

        # Consume the item
        self.game_manager.bag.remove_item(CATCH_ITEM)
        Logger.info(f"Used one {CATCH_ITEM}.")
        
        # 3. Random chance check (1 in 10, or 10%)
        if random.randint(1, 100) <= CHANCE:
 
            Logger.info(f"SUCCESS! {self.enem_mon['name']} was caught!")

            self.game_manager.bag.add_monster(self.enem_mon)
            
            self.result = 'win'
            self.ended = True
            
        else:
            Logger.info(f"FAIL! {self.enem_mon['name']} broke free! Enemy turn.")
            self.current_turn = "enemy"
            self._turn_timer = 0.0

        if self.game_manager:
            self.game_manager.auto_save()

    def run_action(self):
        if self.current_turn != "player" and self.ended:
            return
        self.result = 'run'
        self.ended = True
        
        Logger.info('Getting out of Battle...')
        scene_manager.change_scene('game')
        self.ended = False
        self.turn_label = None

    def atk_action(self):
        if self.current_turn != "player" and self.ended:
            return
        player_atk = self.player_mon.get('atk', 50)
        enem_def = self.enem_mon.get('defense', 40)

        base_damage = player_atk - (enem_def // 2)
        damage = max(1, base_damage)
        ################
        
        self.enem_mon['hp'] = max(0, self.enem_mon['hp'] - damage)
        Logger.info(f"Player attacks for {damage} damage! Enemy HP: {self.enem_mon['hp']}")

        if self.game_manager:
            self.game_manager.auto_save()

        if self.enem_mon['hp'] <= 0:
            self.ended = True
            self.result = "win"
        else:
            self.current_turn = "enemy"
            self._turn_timer = 0.0

    def enem_atk_action(self):
        if self.current_turn != "enemy" and self.ended:
            return
        enem_atk = self.player_mon.get('atk', 50)
        player_def = self.enem_mon.get('defense', 40)

        base_damage = enem_atk - (player_def // 2)
        damage = max(1, base_damage)
        self.player_mon['hp'] = max(0, self.player_mon['hp'] - damage)

        if self.game_manager:
            self.game_manager.auto_save()

        if self.player_mon['hp'] <= 0:

            self.ended = True
            self.result = "lose"
        else:
            self.current_turn = "player"
        
    
    def _draw_hp_bar(self, screen: pg.Surface, x: int, y: int, current_hp: int, max_hp: int, name: str):
        hp_ratio = current_hp / max_hp
        cur_bar_wid = int(self.HP_BAR_WIDTH* hp_ratio)

        pg.draw.rect(screen, GRAY, (x,y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, GREEN, (x,y, cur_bar_wid, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, WHITE, (x,y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT), 2)

        name = Label(
            name, x, y - 5,
            align="midbottom", fontsize=16
        )
        hp = Label(
            f"{current_hp}/{max_hp}",
            x + self.HP_BAR_WIDTH // 2, y + self.HP_BAR_HEIGHT // 2,
            align="center", fontsize=18
        )
        name.draw(screen)
        hp.draw(screen)

    @override
    def update(self, dt):
        # Update turn label text if it exists
        if self.turn_label:
            self.turn_label.set_text(f"Turn: {self.current_turn.upper()}")
        
        if self.ended: 
            if self.result_label and self.result:
                self.result_label.set_text(f"{self.result.upper()}!")
            if input_manager.key_pressed(pg.K_SPACE):
                scene_manager.change_scene('game')
                self.ended = False
                self.turn_label = None
            return
        
        if self.current_turn == 'player':
            self.atk_button.update(dt)
            self.run_button.update(dt)

            if self.is_wild_encounter:
                self.catch_button.update(dt)

        elif self.current_turn == "enemy":
            self._turn_timer += dt
            if self._turn_timer > self._enemy_turn_delay:
                self.enem_atk_action()
                self._turn_timer = 0.0


    @override
    def draw(self, screen: pg.Surface):
        self.background.draw(screen)

        if self.turn_label:
            self.turn_label.draw(screen)

        self.player_mon_pan.set_position(100, 250)
        self.enem_mon_pan.set_position(900, 50)

        self.player_mon_pan.draw(screen)
        self.enem_mon_pan.draw(screen)
        
        if hasattr(self, "player_sprite") and hasattr(self, "player_sprite_rect"):
            screen.blit(self.player_sprite, self.player_sprite_rect)
        if hasattr(self, "enem_sprite") and hasattr(self, "enem_sprite_rect"):
            screen.blit(self.enem_sprite, self.enem_sprite_rect)

        #hp panel thing
        player_panel = self.player_mon_pan.frame_rect
        hpx = player_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        hpy = player_panel.centery - (self.HP_BAR_HEIGHT // 2)

        self._draw_hp_bar( #player monster
            screen,
            hpx, hpy,
            self.player_mon['hp'], self.player_mon['max_hp'],self.player_mon['name']
        )
        enem_panel = self.enem_mon_pan.frame_rect
        en_hpx = enem_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        en_hpy = enem_panel.centery - (self.HP_BAR_HEIGHT // 2)
        self._draw_hp_bar( #enemy's monster 
            screen, 
            en_hpx, en_hpy, 
            self.enem_mon['hp'], self.enem_mon['max_hp'], self.enem_mon['name']
        )
        if self.current_turn == "player" and not self.ended:
            self.atk_button.draw(screen)
            self.run_button.draw(screen)
            if self.is_wild_encounter:
                self.catch_button.draw(screen)

        if self.ended:
            if self.result_label:
                self.result_label.draw(screen)
            if self.prompt_label:
                self.prompt_label.draw(screen)



        


        

