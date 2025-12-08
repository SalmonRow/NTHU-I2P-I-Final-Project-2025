from typing import Dict, Optional, Literal
import random
from src.utils import Logger

class BattleManager:
    phase: str
    result: str

    def __init__(self, player_mon: Dict,
                 enemy_mon: Dict, is_wild: bool= False):
        self.player_mon = player_mon
        self.enemy_mon = enemy_mon
        self.is_wild = is_wild

        self.phase = "player"
        self.result = None
        self._turn_counter = 0

    def _calculate_dmg(self, attacker: Dict, defender: Dict) -> int:
        atk_stat = attacker.get('atk', 10)
        # Check for 'def' or 'defense' keys since data might vary
        def_stat = defender.get('defense', defender.get('def', 10))
        
        base = atk_stat - (def_stat // 2)
        return max(1, base)

    def player_atk(self) -> int:
        if self.phase != 'player':
            return 0
        
        damage = self._calculate_dmg(self.player_mon, self.enemy_mon)
        
        original_hp = self.enemy_mon.get('hp', 0)
        new_hp = max(0, original_hp - damage)
        self.enemy_mon['hp'] = new_hp
        
        Logger.info(f"Player dealt {damage} DMG. Enemy HP: {new_hp}")

        if new_hp <= 0:
            self.result = "win"
            self.phase = "ended"
        else:
            self.phase = "enemy"
            
        return damage

    def enemy_atk(self) -> int:
        if self.phase != 'enemy':
            return 0
            
        damage = self._calculate_dmg(self.enemy_mon, self.player_mon)
        
        original_hp = self.player_mon.get('hp', 0)
        new_hp = max(0, original_hp - damage)
        self.player_mon['hp'] = new_hp
        
        Logger.info(f"Enemy dealt {damage} DMG. Player HP: {new_hp}")

        if new_hp <= 0:
            self.result = "lose"
            self.phase = "ended"
        else:
            self.phase = "player"
            self._turn_counter += 1
            
        return damage

    def run(self) -> bool:
        if self.phase != 'player':
            return False
            
        Logger.info("Player ran away!")
        self.result = "run"
        self.phase = "ended"
        return True

    def catch(self, has_item: bool = True) -> bool:
        """
        Attempts to catch the monster.
        Returns: True if caught, False otherwise.
        """
        if self.phase != 'player':
            return False
        
        if not self.is_wild:
            Logger.info("Cannot catch trainer pokemon!")
            return False
            
        if not has_item:
            Logger.info("No items to catch with!")
            return False

        # 10% chance (base)
        max_hp = self.enemy_mon.get('max_hp', 1)
        hp = self.enemy_mon.get('hp', 1)
        bonus = max(0, (max_hp - (hp // max_hp) - 10))
        success = random.randint(1, 100) <= 10 + bonus
        
        if success:
            Logger.info("Caught the monster!")
            self.result = "caught" # Or "caught" if you want specific handling
            self.phase = "ended"
            return True
        else:
            Logger.info("Failed to catch! Enemy turn.")
            self.phase = "enemy"
            return False

