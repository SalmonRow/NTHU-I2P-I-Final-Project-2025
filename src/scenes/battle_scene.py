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
    _enemy_turn_delay: float = 0.8 
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
            on_catch=self.on_catch,
            on_move_click=self.on_move_selected
        )
        
        self.battle_manager = None 
        self.is_wild_encounter = False
        self._music_played = False
        
        # Message Queue
        self.message_queue = []
        self.message_timer = 0.0
        # Message Queue
        self.message_queue = []
        self.message_timer = 0.0
        # Message Queue
        self.message_queue = []
        self.message_timer = 0.0
        self.message_delay = 0.8
        self.is_processing_messages = False
        self._end_message_shown = False


    @override
    def enter(self, player_monster, enemy_monster, **kwargs):
        Logger.info(f'Entering Battle... Wild encounter : {kwargs.get("is_wild_encounter", False)}')

        self.is_wild_encounter = kwargs.get('is_wild_encounter', False)
        if self.is_wild_encounter:
            sound_manager.play_bgm("RBY 110 Battle! (Wild Pokemon).ogg")
        else:
            sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")
            
        self._music_played = False
        self._end_message_shown = False

        # Fallback if monsters are missing (Development safety)
        if not player_monster:
            player_monster = {"name": "Pikachu_fake", "hp": 100, "max_hp": 100, "level": 25, "atk": 60, "defense": 15}
        if not enemy_monster:
            enemy_monster = {"name": "Gengar_fake", "hp": 80, "max_hp": 80, "level": 30, "atk": 70, "defense": 15}

        # 1. Initialize Logic System
        self.battle_manager = BattleManager(player_monster, enemy_monster, self.is_wild_encounter)
        
        # 2. Initialize Visuals
        self.ui_manager.load_sprites(player_monster, enemy_monster)
        
        # 3. Initial Log
        p_name = player_monster['name']
        self.ui_manager.add_log_message(f"What will \n[CYAN]{p_name}[WHITE] do?")

    @override
    def exit(self):
        if self.game_manager and self.battle_manager and self.battle_manager.result:
            self.game_manager.last_battle_result = self.battle_manager.result
            Logger.info(f'Saved battle result: {self.battle_manager.result}')
        
        self.game_manager.current_battle_en = None

    # --- Callbacks for UI Buttons ---
    def on_attack(self):
        # Now just opens the menu
        pass

    def on_move_selected(self, move_name: str):
        self.ui_manager.close_attack_menu()
        if self.battle_manager:
            # 1. Execute Player Attack
            result = self.battle_manager.player_atk(move_name)
            
            # TRIGGER ANIMATION (Only if supported, currently player is static)
            # if hasattr(self.ui_manager.player_sprite, 'play_attack'):
            #    self.ui_manager.player_sprite.play_attack()
            
            # 2. Queue Messages
            p_name = self.battle_manager.player_mon['name']
            dmg = result.get('damage', 0)
            eff = result.get('effectiveness', 1.0)
            
            self.queue_message(f"[CYAN]{p_name} [WHITE]used \n[YELLOW]{move_name}[WHITE]!")
            
            # Effectiveness
            if eff > 1.0:
                self.queue_message("[YELLOW]It's super effective!")
            elif eff == 0:
                self.queue_message("[WHITE]It had no effect...")
            elif eff < 1.0:
                self.queue_message("[WHITE]It's not very effective...")

            if self.game_manager:
                self.game_manager.auto_save()


    def on_run(self):
        if self.battle_manager:
            if self.battle_manager.run():
                self.queue_message("[CYAN]Player [WHITE]got away \n[WHITE]safely!")
                self._handle_end()


    def on_catch(self):
        if self.battle_manager:
            if self.game_manager.bag.has_item("Pokeball"):
                self.game_manager.bag.remove_item("Pokeball")
                if self.battle_manager.catch(has_item=True):
                    e_name = self.battle_manager.enemy_mon.get('name', 'Enemy')
                    self.game_manager.bag.add_monster(self.battle_manager.enemy_mon)
                    self.queue_message(f"[WHITE]Gotcha! [CYAN]{e_name} \n[WHITE]was caught!")
                    self._handle_end()

            else:
                self.queue_message("You don't have any \nPOKEBALLS!")

            
            if self.game_manager:
                 self.game_manager.auto_save()

    def on_bag(self):
        Logger.info("Bag button clicked - Feature not implemented yet")
        pass

    def queue_message(self, message: str):
        """Add a message to be shown in the log sequentially"""
        self.message_queue.append(message)


    def _handle_end(self):
        """Helpers to handle end of battle transition logic if needed"""
        pass

    @override
    def update(self, dt):
        # ALWAYS Update UI (Animations, Buttons, etc.)
        self.ui_manager.update(dt, self.battle_manager.phase if self.battle_manager else 'wait', self.is_wild_encounter, battle_ended=(self.battle_manager and self.battle_manager.phase == "ended"))

        # 0. Handle Message Queue
        if self.is_processing_messages:
            self.message_timer += dt
            if self.message_timer >= self.message_delay:
                self.message_timer = 0.0
                if self.message_queue:
                    next_msg = self.message_queue.pop(0)
                    self.ui_manager.add_log_message(next_msg)
                else:
                    self.is_processing_messages = False
                    # Only show prompt if it is PLAYER turn and battle isn't over
                    if self.battle_manager.phase == 'player' and self.battle_manager.result is None:
                        p_name = self.battle_manager.player_mon['name']
                        self.ui_manager.add_log_message(f"What will \n[CYAN]{p_name}[WHITE] do?")
            return

        if self.message_queue:
            self.is_processing_messages = True
            next_msg = self.message_queue.pop(0)
            self.ui_manager.add_log_message(next_msg)
            self.message_timer = 0.0
            return

        if not self.battle_manager:
            return

        # 1. Check for Battle End
        if self.battle_manager.phase == "ended":
            # 1.5 One-time End Message
            if not getattr(self, "_end_message_shown", False):
                if self.battle_manager.result == BattleManager.ENDING_MESS[0]:
                    self.queue_message(f"[CYAN]{self.battle_manager.player_mon['name']} [YELLOW]Won!")
                elif self.battle_manager.result == BattleManager.ENDING_MESS[1]:
                    self.queue_message(f"[CYAN]{self.battle_manager.player_mon['name']} [RED]Fainted...")
                self._end_message_shown = True

            # Play Victory Music (Sync with End Screen)
            # Only play if messages are done processing
            if not self._music_played and not self.is_processing_messages and not self.message_queue:
                if self.is_wild_encounter:
                    sound_manager.play_bgm("RBY 111 Victory! (Wild Pokemon).ogg")
                else:
                    sound_manager.play_bgm("RBY 108 Victory! (Trainer).ogg")
                self._music_played = True

            # Wait for space to exit
            if input_manager.key_pressed(pg.K_SPACE):
                sound_manager.play_bgm("RBY 109 Road to Viridian City (Route 1).ogg")
                scene_manager.change_scene('game')
            # Allow UI to show result
            self.ui_manager.update(dt, self.battle_manager.phase, self.is_wild_encounter, battle_ended=True)
            return

        # 2. Enemy Turn Logic
        if self.battle_manager.phase == "enemy":
            self._turn_timer += dt
            if self._turn_timer > self._enemy_turn_delay:
                # Execute Enemy Attack
                result = self.battle_manager.enemy_atk()
                 
                # TRIGGER ANIMATION
                if self.ui_manager.enem_sprite:
                     self.ui_manager.enem_sprite.play_attack()
                
                # Queue Messages
                e_name = self.battle_manager.enemy_mon['name']
                move = result.get('move', 'Attack')
                eff = result.get('effectiveness', 1.0)
                
                self.queue_message(f"[CYAN]{e_name} [WHITE]used \n[YELLOW]{move}[WHITE]!")
                
                if eff > 1.0:
                    self.queue_message("[YELLOW]It's super effective!")
                elif eff == 0:
                    self.queue_message("[WHITE]It had no effect...")
                elif eff < 1.0:
                    self.queue_message("[WHITE]It's not very effective...")

                self._turn_timer = 0.0
                if self.game_manager:
                    self.game_manager.auto_save()
                    
        # 3. Forced Switch Check
        if self.battle_manager.phase == "forced_switch":
             has_alive = False
             if self.game_manager and self.game_manager.bag:
                 # Check if any monster has HP > 0
                 # Accessing protected member _monsters_data as widely used elsewhere
                 for m in self.game_manager.bag._monsters_data:
                     if m.get('hp', 0) > 0:
                         has_alive = True
                         break
             
             if not has_alive:
                 # No pokemon left -> Defeat
                 self.battle_manager.result = BattleManager.ENDING_MESS[1]
                 self.battle_manager.phase = "ended"
             elif not self.ui_manager.showing_pokemon_menu:
                 self.ui_manager.open_pokemon_menu(force_selection=True)

    @override
    def draw(self, screen: pg.Surface):
        self.background.draw(screen)
        
        visual_phase = self.battle_manager.phase
        # Hide menu actions if we are still playing messages (e.g. enemy attack text)
        if self.battle_manager.phase == 'player' and (self.is_processing_messages or self.message_queue):
            visual_phase = 'wait'

        if self.battle_manager:
             self.ui_manager.draw(
                 screen,
                 self.battle_manager.player_mon, 
                 self.battle_manager.enemy_mon,
                 visual_phase,
                 self.is_wild_encounter,
                 self.battle_manager.phase == "ended" and not self.is_processing_messages and not self.message_queue and self._end_message_shown,
                 self.battle_manager.result
             )
