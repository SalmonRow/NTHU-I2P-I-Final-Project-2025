import pygame as pg

from src.scenes.scene import Scene
from src.core.managers import GameManager, OnlineManager, BattleManager
from src.interface.battle_ui_manager import BattleUIManager
from src.utils import Logger
from src.core.services import sound_manager, scene_manager, input_manager
from src.sprites import Sprite, BackgroundSprite
from typing import override

class BattleScene(Scene):
    game_manager: GameManager = None
    ui_manager: BattleUIManager
    battle_manager: BattleManager
    
    background: BackgroundSprite
    
    # Flags
    is_wild_encounter: bool = False
    
    # Timing (moved from scene logic to here purely for "waiting" before enemy moves)
    _enemy_turn_delay: float = 1.0 
    _turn_timer: float = 0.0

    def __init__(self, game_manger_instance):
        super().__init__()
        self.game_manager = game_manger_instance
        self.background = BackgroundSprite("backgrounds/background1.png")
        
        # Initialize UI Manager with callbacks
        self.ui_manager = BattleUIManager(
            self,
            on_attack=self.on_attack,
            on_run=self.on_run,
            on_catch=self.on_catch
        )
        
        self.battle_manager = None 
        self.is_wild_encounter = False

    @override
    def enter(self, player_monster, enemy_monster, **kwargs):
        Logger.info(f'Entering Battle... Wild encounter : {kwargs.get("is_wild_encounter", False)}')
        sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")

        self.is_wild_encounter = kwargs.get('is_wild_encounter', False)
        
        # Fallback if monsters are missing (Development safety)
        if not player_monster:
            player_monster = {"name": "Pikachu_fake", "hp": 100, "max_hp": 100, "level": 25, "atk": 60, "defense": 15}
        if not enemy_monster:
            enemy_monster = {"name": "Gengar_fake", "hp": 80, "max_hp": 80, "level": 30, "atk": 70, "defense": 15}

        # 1. Initialize Logic System
        self.battle_manager = BattleManager(player_monster, enemy_monster, self.is_wild_encounter)
        
        # 2. Initialize Visuals
        self.ui_manager.load_sprites(player_monster, enemy_monster)

    @override
    def exit(self):
        if self.game_manager and self.battle_manager and self.battle_manager.result:
            self.game_manager.last_battle_result = self.battle_manager.result
            Logger.info(f'Saved battle result: {self.battle_manager.result}')
        
        self.game_manager.current_battle_en = None

    # --- Callbacks for UI Buttons ---
    def on_attack(self):
        if self.battle_manager:
            self.battle_manager.player_atk()
            if self.game_manager:
                self.game_manager.auto_save()

    def on_run(self):
        if self.battle_manager:
            if self.battle_manager.run():
                self._handle_end()

    def on_catch(self):
        if self.battle_manager:
            if self.game_manager.bag.has_item("Pokeball"):
                self.game_manager.bag.remove_item("Pokeball")
                if self.battle_manager.catch(has_item=True):
                    self.game_manager.bag.add_monster(self.battle_manager.enemy_mon)
                    self._handle_end()
            else:
                pass # UI should probably show "No balls!" msg (future task)
            
            if self.game_manager:
                 self.game_manager.auto_save()

    def _handle_end(self):
        """Helpers to handle end of battle transition logic if needed"""
        pass

    @override
    def update(self, dt):
        if not self.battle_manager:
            return

        # 1. Check for Battle End
        if self.battle_manager.phase == "ended":
            # Wait for space to exit
            if input_manager.key_pressed(pg.K_SPACE):
                scene_manager.change_scene('game')
            
            # Allow UI to show result
            self.ui_manager.update(dt, self.battle_manager.phase, self.is_wild_encounter, battle_ended=True)
            return

        # 2. Enemy Turn Logic (Artificial Delay)
        if self.battle_manager.phase == "enemy":
            self._turn_timer += dt
            if self._turn_timer > self._enemy_turn_delay:
                self.battle_manager.enemy_atk()
                self._turn_timer = 0.0
                if self.game_manager:
                    self.game_manager.auto_save()

        # 3. Update UI
        self.ui_manager.update(dt, self.battle_manager.phase, self.is_wild_encounter, battle_ended=False)

    @override
    def draw(self, screen: pg.Surface):
        self.background.draw(screen)
        
        if self.battle_manager:
             self.ui_manager.draw(
                 screen, 
                 self.battle_manager.player_mon, 
                 self.battle_manager.enemy_mon,
                 self.battle_manager.phase,
                 self.is_wild_encounter,
                 self.battle_manager.phase == "ended",
                 self.battle_manager.result
             )
