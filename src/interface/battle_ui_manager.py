import pygame as pg
from typing import Callable, Optional, Dict
from src.utils import GameSettings, load_img, Logger
from src.interface.components import Button, Popup, Label

GREEN = (0, 200, 0)
RED = (200, 0, 0)
GRAY = (130, 130, 130)
WHITE = (255, 255, 255)

class BattleUIManager:
    """
    Manages all UI elements for the Battle Scene.
    Handle inputs for buttons and drawing for everything.
    """
    
    # UI Components
    player_mon_pan: Popup
    enem_mon_pan: Popup
    
    atk_button: Button
    run_button: Button
    catch_button: Button
    
    turn_label: Label
    result_label: Label
    prompt_label: Label
    
    # Sprites
    player_sprite: pg.Surface | None = None
    enem_sprite: pg.Surface | None = None
    player_sprite_rect: pg.Rect | None = None
    enem_sprite_rect: pg.Rect | None = None

    # Constants
    ACTION_BUTTON_SIZE = 80
    HP_BAR_WIDTH = 200
    HP_BAR_HEIGHT = 20
    STATS_PAN_SIZE = (520, 130)

    def __init__(self, scene, 
                 on_attack: Callable, 
                 on_run: Callable, 
                 on_catch: Callable):
        self.scene = scene
        
        # --- Panels ---
        self.player_mon_pan = Popup("UI/raw/UI_Flat_Banner03a.png", self.STATS_PAN_SIZE, close_callback=None)
        self.enem_mon_pan = Popup("UI/raw/UI_Flat_Banner03a.png", self.STATS_PAN_SIZE, close_callback=None)
        self.player_mon_pan.interactive_components = []
        self.enem_mon_pan.interactive_components = []

        
        # --- Buttons ---
        self.atk_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 ,
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE ,
            text="ATTACK",
            on_click=on_attack
        )

        self.run_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 + 20 + self.atk_button.hitbox.width, 
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE,
            text="RUN",
            on_click=on_run
        )

        self.catch_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            GameSettings.SCREEN_WIDTH // 2 + 40 + self.atk_button.hitbox.width + self.run_button.hitbox.width, 
            GameSettings.SCREEN_HEIGHT - 170,
            self.ACTION_BUTTON_SIZE * 2, self.ACTION_BUTTON_SIZE,
            text="CATCH",
            on_click=on_catch
        )
        
        # --- Labels ---
        self.turn_label = Label(text="Turn: PLAYER", x=75, y=50, fontsize=30)
        self.result_label = Label(text="", x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT // 2, color=RED, align='center', fontsize=50)
        self.prompt_label = Label(text="Press SPACE to exit.", x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT - 50, color=WHITE, align='center', fontsize=20)

    def load_sprites(self, player_mon: Dict, enem_mon: Dict):
        try:
            player_full = load_img(player_mon.get("battle_sprite_path", "sprites/pokemon/Bulbasaur.png"))
            enemy_full  = load_img(enem_mon.get("battle_sprite_path", "sprites/pokemon/Bulbasaur.png"))

            # Processing sprites (same logic as before)
            P_SCALE = 6.5
            E_SCALE = 3
            w1, h1 = player_full.get_size()
            
            # Assuming sprite sheet/strip logic from original:
            self.player_sprite = player_full.subsurface(pg.Rect(w1 // 2, 0, w1 // 2, h1))
            pw, ph = int(self.player_sprite.get_width() * P_SCALE), int(self.player_sprite.get_height() * P_SCALE)
            self.player_sprite = pg.transform.scale(self.player_sprite, (pw, ph))

            w2, h2 = enemy_full.get_size()
            self.enem_sprite = enemy_full.subsurface(pg.Rect(0, 0, w2 // 2, h2))
            ew, eh = int(self.enem_sprite.get_width() * E_SCALE), int(self.enem_sprite.get_height() * E_SCALE)
            self.enem_sprite = pg.transform.scale(self.enem_sprite, (ew, eh))
            
            # Positioning
            self.player_sprite_rect = self.player_sprite.get_rect()
            self.player_sprite_rect.bottomleft = (-20, GameSettings.SCREEN_HEIGHT)

            self.enem_sprite_rect = self.enem_sprite.get_rect()
            self.enem_sprite_rect.topleft = (GameSettings.SCREEN_WIDTH - self.enem_sprite_rect.width - 80, 60)
            
        except Exception as e:
            Logger.error(f"Failed to load sprites in UI Manager: {e}")

    def update(self, dt: float, current_turn: str, is_wild: bool, battle_ended: bool):
        self.turn_label.set_text(f"Turn: {current_turn.upper()}")
        
        if not battle_ended and current_turn == 'player':
            self.atk_button.update(dt)
            self.run_button.update(dt)
            if is_wild:
                 self.catch_button.update(dt)

    def draw(self, screen: pg.Surface, player_mon: Dict, enem_mon: Dict, 
             current_turn: str, is_wild: bool, battle_ended: bool, result_text: str | None):
        
        # Draw Labels
        self.turn_label.draw(screen)

        # Draw Panels
        self.player_mon_pan.set_position(100, 250)
        self.enem_mon_pan.set_position(900, 50)
        self.player_mon_pan.draw(screen)
        self.enem_mon_pan.draw(screen)

        # Draw Sprites
        if self.player_sprite and self.player_sprite_rect:
            screen.blit(self.player_sprite, self.player_sprite_rect)
        if self.enem_sprite and self.enem_sprite_rect:
            screen.blit(self.enem_sprite, self.enem_sprite_rect)

        # Draw HP Bars
        player_panel = self.player_mon_pan.frame_rect
        hpx = player_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        hpy = player_panel.centery - (self.HP_BAR_HEIGHT // 2)
        self._draw_hp_bar(screen, hpx, hpy, player_mon.get('hp', 0), player_mon.get('max_hp', 100), player_mon.get('name', '???'))

        enem_panel = self.enem_mon_pan.frame_rect
        en_hpx = enem_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        en_hpy = enem_panel.centery - (self.HP_BAR_HEIGHT // 2)
        self._draw_hp_bar(screen, en_hpx, en_hpy, enem_mon.get('hp', 0), enem_mon.get('max_hp', 100), enem_mon.get('name', '???'))

        # Draw Buttons
        if not battle_ended and current_turn == 'player':
            self.atk_button.draw(screen)
            self.run_button.draw(screen)
            if is_wild:
                self.catch_button.draw(screen)

        # Draw Result Overlay
        if battle_ended and result_text:
            self.result_label.set_text(f"{result_text.upper()}!")
            self.result_label.draw(screen)
            self.prompt_label.draw(screen)

    def _draw_hp_bar(self, screen: pg.Surface, x: int, y: int, current_hp: int, max_hp: int, name: str):
        hp_ratio = current_hp / max_hp if max_hp > 0 else 0
        cur_bar_wid = int(self.HP_BAR_WIDTH * hp_ratio)
        
        # Determine Color
        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = (225, 225, 0) # YELLOW
        elif hp_ratio > 0.10:
            color = RED
        else:
            color = (139, 0, 0) # DARK RED

        pg.draw.rect(screen, GRAY, (x, y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, color, (x, y, cur_bar_wid, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, WHITE, (x, y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT), 2)

        name_lbl = Label(name, x, y - 5, align="midbottom", fontsize=16)
        hp_lbl = Label(f"{current_hp}/{max_hp}", x + self.HP_BAR_WIDTH // 2, y + self.HP_BAR_HEIGHT // 2, align="center", fontsize=18)
        
        name_lbl.draw(screen)
        hp_lbl.draw(screen)