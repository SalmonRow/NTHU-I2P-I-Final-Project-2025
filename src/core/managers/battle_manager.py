from typing import Dict, Optional, List
import random
from src.utils import Logger

class BattleManager:
    # Constants for battle results: Victory, Defeat, Coward, Caught
    ENDING_MESS = ['Victory', 'Defeat', 'Coward', 'Caught'] 
    
    phase: str
    result: Optional[str]

    talk_cooldown: int = 0
    ignore_def_next_turn: bool = False
    
    # New Phase for Multi-Enemy
    PHASE_ENEMY_FAINT = 'enemy_faint'

    def __init__(self, player_mon: Dict, enemy_mon: Dict, player_party: List[Dict], enemy_party: List[Dict] = None, is_wild: bool = False):
        self.player_mon = player_mon
        self.enemy_mon = enemy_mon
        self.player_party = player_party
        self.enemy_party = enemy_party if enemy_party else [enemy_mon]
        self.is_wild = is_wild
        
        self.talk_cooldown = 0
        self.ignore_def_next_turn = False

        self.talk_cooldown = 0
        self.ignore_def_next_turn = False

        self.result = None
        self._turn_counter = 0
        
        # Speed Check (Turn Order)
        p_speed = player_mon.get('speed', 10)
        e_speed = enemy_mon.get('speed', 10)
        
        if p_speed >= e_speed:
            self.phase = "player"
            Logger.info(f"Player Speed ({p_speed}) >= Enemy ({e_speed}). Player starts.")
        else:
            self.phase = "enemy"
            Logger.info(f"Enemy Speed ({e_speed}) > Player ({p_speed}). Enemy starts.")

    def _calculate_dmg(self, attacker: Dict, defender: Dict, move_name: str) -> int:
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()
        
        # 1. Get Move Data
        move_data = dl.get_move_data(move_name)
        power = move_data.get('power', 40)
        move_type = move_data.get('type', 'Normal')
        
        # 2. Get Stats
        atk_stat = attacker.get('atk', 10)
        def_stat = defender.get('defense', 10)
        level = attacker.get('level', 5)
        
        # Check for Talk No Jutsu Penalty
        if defender == self.player_mon and self.ignore_def_next_turn:
            def_stat = 1 # Ignore defense (avoid div by zero)
            self.ignore_def_next_turn = False
            Logger.info("Defense was ignored due to failed Talk No Jutsu!")
        
        # 3. Base Damage Formula
        # ((2 * Level / 5 + 2) * Power * A / D) / 50 + 2
        base_dmg = ((2 * level / 5 + 2) * power * (atk_stat / def_stat)) / 50 + 2
        
        # 4. Modifiers
        modifier = 1.0
        
        # STAB (Same Type Attack Bonus)
        # Handle if monster has multiple types (e.g., ["Fire", "Flying"])
        att_types = attacker.get('type', ['Normal'])
        if isinstance(att_types, str):
            att_types = [att_types]  # Normalize to list
            
        if move_type in att_types:
            modifier *= 1.5
            
        # Type Effectiveness
        def_types = defender.get('type', ['Normal'])
        if isinstance(def_types, str):
            def_types = [def_types] # Normalize to list

        type_effectiveness = self._get_type_effectiveness(move_type, def_types)
        modifier *= type_effectiveness

        # Log Effectiveness for UI/Debug
        if type_effectiveness >= 2.0:
            Logger.info("It's super effective!")
        elif type_effectiveness == 0.0:
            Logger.info("Immune!")
        elif type_effectiveness <= 0.5:
            Logger.info("It's not very effective...")
            
        # Random variance (0.85 to 1.00)
        modifier *= random.uniform(0.85, 1.0)
        
        final_dmg = int(base_dmg * modifier)
        
        # Return tuple: (damage, effectiveness_multiplier)
        return max(0, final_dmg), type_effectiveness 

    def _get_type_effectiveness(self, move_type: str, def_types: List[str]) -> float:
        """
        Returns the damage multiplier (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
        based on the move type vs the defender's type(s).
        """
        # Full Gen 6+ Type Chart
        # Key: Attacking Type -> Value: { Defending Type: Multiplier }
        # Omitted types default to 1.0
        from src.core.data_loader import DataLoader
        chart = DataLoader.instance().get_type_chart()

        modifier = 1.0
        move_chart = chart.get(move_type, {})

        for d_type in def_types:
            # Multiply existing modifier by the new type effectiveness
            # Default to 1.0 (Neutral) if the pairing isn't in exception list
            modifier *= move_chart.get(d_type, 1.0)

        return modifier

    def player_atk(self, move_name: Optional[str] = None) -> Dict:
        if self.phase != 'player':
            return {}
        
        # Select Move
        if not move_name:
            moves = self.player_mon.get('moves', [])
            move_name = moves[0] if moves else "Tackle"
            
        damage, effectiveness = self._calculate_dmg(self.player_mon, self.enemy_mon, move_name)
        
        original_hp = self.enemy_mon.get('hp', 0)
        new_hp = max(0, original_hp - damage)
        self.enemy_mon['hp'] = new_hp
        
        Logger.info(f"Player used {move_name}! Dealt {damage} DMG. Enemy HP: {new_hp}")

        turn_result = {
            "damage": damage,
            "move": move_name,
            "effectiveness": effectiveness,
            "target_hp": new_hp
        }

        if new_hp <= 0:
            # Multi-Enemy Logic
            if self.has_alive_enemy():
                 self.phase = self.PHASE_ENEMY_FAINT
                 self._handle_xp_gain() # Gain XP for this kill
            else:
                 self.result = self.ENDING_MESS[0] # Victory
                 self.phase = "ended"
                 self._handle_xp_gain() 
        else:
             # If player just attacked, they can't force switch, it's enemy's turn
             # unless the move caused recoil death (not implemented yet)
             self.phase = "enemy"
            
        return turn_result
        
    def talk_no_jutsu(self) -> Dict:
        """
        Attempt Talk No Jutsu.
        Returns dict with success block.
        """
        if self.phase != 'player':
            return {'success': False, 'reason': 'phase'}
            
        if self.talk_cooldown > 0:
            return {'success': False, 'reason': 'cooldown'}
            
        # chance = 5 + (PercentageLost * 100), max at 50% HP (so +50)
        max_hp = self.enemy_mon.get('max_hp', 1)
        hp = self.enemy_mon.get('hp', 1)
        
        missing_ratio = 1.0 - (hp / max(1, max_hp))
        bonus = min(50, int(missing_ratio * 100))
        chance = 5 + bonus
        
        Logger.info(f"Talk No Jutsu! Chance: {chance}% (Bonus {bonus})")
        
        if random.randint(1, 100) <= chance:
            import copy
            cloned = copy.deepcopy(self.enemy_mon)
            cloned['hp'] = cloned['max_hp'] # Full HP
            
            
            # Key Logic Update: The enemy monster is "gone" (converted)
            # So we must set its HP to 0 so it counts as dead/gone for the enemy team
            
            # --- DEBUG LOGGING ---
            Logger.info("--- TALK NO JUTSU DEBUG ---")
            for i, mon in enumerate(self.enemy_party):
                Logger.info(f"Mon {i}: {mon['name']} (ID: {id(mon)}) HP: {mon.get('hp')}")
            
            # Correctly remove from party (same fix as catch)
            if self.enemy_mon in self.enemy_party:
                self.enemy_party.remove(self.enemy_mon)
            
            # If no more enemies, it's a Victory (handled by Scene via result)
            # If there are more enemies, we need to transition. 
            # Current scene logic for talk_no_jutsu calls _handle_end() immediately which might be wrong for multi-enemy?
            # User requirement: "you win immediately with the copy of that pokemon" -> implies immediate win?
            # Let's stick to immediate win for now as per "Talk No Jutsu" implies ending the conflict?
            # Or maybe just "converting" one enemy?
            # For now, let's keep it consistent with "Win immediately" logic observed in previous code comments.
            
            self.result = 'Victory' 
            self.phase = "ended"
            
            return {'success': True, 'monster': cloned}
        else:
            self.ignore_def_next_turn = True
            # Cooldown: used (0), 1, 2, 3, 4 (avail). So set to 4.
            # We decrement at start of player turn.
            self.talk_cooldown = 4 
            self.phase = "enemy"
            Logger.info("Talk No Jutsu Failed!")
            return {'success': False, 'reason': 'failed'}

    def enemy_atk(self) -> Dict:
        if self.phase != 'enemy':
            return {}
            
        # AI Select Move
        moves = self.enemy_mon.get('moves', [])
        move_name = random.choice(moves) if moves else "Tackle"

        damage, effectiveness = self._calculate_dmg(self.enemy_mon, self.player_mon, move_name)
        
        original_hp = self.player_mon.get('hp', 0)
        new_hp = max(0, original_hp - damage)
        self.player_mon['hp'] = new_hp
        
        Logger.info(f"Enemy used {move_name}! Dealt {damage} DMG. Player HP: {new_hp}")

        turn_result = {
            "damage": damage,
            "move": move_name,
            "effectiveness": effectiveness,
            "target_hp": new_hp
        }

        if new_hp <= 0:
            # Check if player has other pokemon
            if self._has_available_pokemon():
                 Logger.info("Player's Pokemon Fainted! Choose another one.")
                 self.phase = "forced_switch"
                 # Do NOT set result to ENDING_MESS[1] yet
            else:
                 self.result = self.ENDING_MESS[1] # Defeat (Lose)
                 self.phase = "ended"
        else:
            self.phase = "player"
            self._turn_counter += 1
            if self.talk_cooldown > 0:
                self.talk_cooldown -= 1
            
        return turn_result
    
    def has_alive_enemy(self) -> bool:
        if not self.enemy_party:
            return False
        for mon in self.enemy_party:
            if mon.get('hp', 0) > 0:
                return True
        return False

    def next_enemy_pokemon(self) -> Dict | None:
        """Switch to next available enemy pokemon"""
        for mon in self.enemy_party:
            if mon.get('hp', 0) > 0:
                self.enemy_mon = mon
                self.phase = 'player' # Reset phase to player turn
                Logger.info(f"Enemy sent out {mon['name']}!")
                return mon
        return None

    def _has_available_pokemon(self) -> bool:
        if not self.player_party:
            return False
            
        for pokemon in self.player_party:
            if pokemon.get('hp', 0) > 0:
                return True
        return False

    def switch_pokemon(self, new_mon: Dict):
        """
        Switches the active player monster.
        """
        if self.phase not in ['player', 'forced_switch']:
             return False

        Logger.info(f"Go! {new_mon['name']}!")
        self.player_mon = new_mon
        
        # If valid switch, consume turn (unless it was forced?)
        # Standard rules: Manual switch = turn used. Forced switch = new turn for player (usually).
        # Implement: If phase was 'player' (manual), set to 'enemy'.
        # If phase was 'forced_switch' (death), set to 'player' (fresh start).
        
        if self.phase == 'player':
             self.phase = 'enemy'
        elif self.phase == 'forced_switch':
             self.phase = 'player'
             
        return True
    
    def _handle_xp_gain(self):
        """Encapsulated XP and Level Up Logic"""
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()
        
        # 1. Calc XP
        enemy_name = self.enemy_mon.get('name')
        # Use safe get just in case
        species_data = dl.get_monster_species_data(enemy_name) or {} 
        enemy_base_xp = species_data.get('base_xp', 50)
        enemy_level = self.enemy_mon.get('level', 1)
        
        xp_gain = int((enemy_base_xp * enemy_level) / 7)
        
        # 2. Add to Player
        current_xp = self.player_mon.get('xp', 0)
        current_xp += xp_gain
        self.player_mon['xp'] = current_xp
        Logger.info(f"Gained {xp_gain} XP! Total: {current_xp}")
        
        # 3. Check Level Up
        current_level = self.player_mon.get('level', 1)
        threshold = dl.get_xp_requirement(current_level)
        
        if current_xp >= threshold:
            self.player_mon['level'] += 1
            self.player_mon['xp'] = current_xp - threshold
            Logger.info(f"{self.player_mon['name']} leveled up to {self.player_mon['level']}!")
            
            # Re-calc stats
            dl.hydrate_monster(self.player_mon)
            self.player_mon['hp'] = self.player_mon['max_hp'] 

            # 3.5 Check Learnset
            player_species_data = dl.get_monster_species_data(self.player_mon.get('name'))
            learnset = player_species_data.get('learnset', {})
            
            # Check if current level is in learnset (keys are strings in json)
            lvl_str = str(self.player_mon['level'])
            if lvl_str in learnset:
                new_move = learnset[lvl_str]
                current_moves = self.player_mon.get('moves', [])
                
                if new_move not in current_moves:
                    Logger.info(f"{self.player_mon['name']} is trying to learn {new_move}!")
                    
                    if len(current_moves) < 4:
                        current_moves.append(new_move)
                        Logger.info(f"Learned {new_move}!")
                    else:
                        # Simple logic: Replace first move
                        forgotten = current_moves[0]
                        current_moves[0] = new_move
                        Logger.info(f"Forgot {forgotten} and learned {new_move}!")
                        
                    self.player_mon['moves'] = current_moves 
            
            # 4. Check Evolution
            player_species_data = dl.get_monster_species_data(self.player_mon.get('name'))
            evo_data = player_species_data.get('evolution')
            if evo_data:
                req_level = evo_data.get('level')
                target_species = evo_data.get('to')
                if self.player_mon['level'] >= req_level:
                    Logger.info(f"{self.player_mon['name']} is ready to evolve!")
                    self.player_mon['can_evolve'] = True
                    # self.player_mon['name'] = target_species
                    # dl.hydrate_monster(self.player_mon)
                    # Logger.info(f"Evolved into {target_species}!")

    def distribute_catch_xp(self):
        """
        Distribute XP to ALL party members upon catch.
        Formula: 50 + ((caught_level * 2) + caught_hp_left) * 10
        """
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()
        
        c_level = self.enemy_mon.get('level', 1)
        c_hp = self.enemy_mon.get('hp', 0)
        
        xp_gain = 50 + ((c_level * 2) + c_hp) * 10
        
        Logger.info(f"Catch Success! Team gained {xp_gain} XP!")
        
        for mon in self.player_party:
             # Add XP
             current_xp = mon.get('xp', 0)
             current_xp += xp_gain
             mon['xp'] = current_xp
             
             # Check Level Up (Simplified copy of handle_xp_gain logic)
             current_level = mon.get('level', 1)
             threshold = dl.get_xp_requirement(current_level)
             
             while current_xp >= threshold:
                 mon['level'] += 1
                 mon['xp'] = current_xp - threshold
                 current_xp = mon['xp'] # Update for next loop if multiple levels
                 
                 Logger.info(f"{mon.get('name')} leveled up to {mon['level']}!")
                 
                 # Re-calc stats
                 dl.hydrate_monster(mon)
                 mon['hp'] = mon['max_hp'] # Full heal on level up?
                 
                 # Note: Learnset/Evolution logic for non-active mons 
                 # is complex (Needs UI prompts). Skipping for now to avoid blocking.
                 threshold = dl.get_xp_requirement(mon['level'])

    def use_item(self, item_data: Dict) -> bool:
        """
        Apply item effect. Returns True if turn consumed.
        """
        if self.phase != 'player':
            return False

        effect = item_data.get('effect')
        val = item_data.get('value', 0)
        
        success = False
        
        if effect == 'heal_hp':
            max_hp = self.player_mon.get('max_hp', 1)
            current_hp = self.player_mon.get('hp', 0)
            
            if current_hp >= max_hp:
                Logger.info("HP is already full!")
                return False
                
            new_hp = min(max_hp, current_hp + val)
            self.player_mon['hp'] = new_hp
            Logger.info(f"Used {item_data.get('name')}! Recovered HP. ({current_hp} -> {new_hp})")
            success = True
            
        elif effect == 'buff_stat':
            stat_name = item_data.get('stat')
            if stat_name in self.player_mon:
                original = self.player_mon[stat_name]
                new_val = int(original * val)
                self.player_mon[stat_name] = new_val
                Logger.info(f"Used {item_data.get('name')}! {stat_name} rose from {original} to {new_val}!")
                success = True
            else:
                Logger.info(f"Stat {stat_name} not found on monster.")
                
        if success:
            self.phase = "enemy"
            return True
            
        return False

    def run(self) -> bool:
        if self.phase != 'player':
            return False
            
        Logger.info("Player ran away!")
        self.result = self.ENDING_MESS[2] # Coward (Run)
        self.phase = "ended"
        return True

    def catch(self, has_item: bool = True) -> bool:
        if self.phase != 'player':
            return False
        
        if not self.is_wild:
            Logger.info("Cannot catch trainer pokemon!")
            return False
            
        if not has_item:
            Logger.info("No items to catch with!")
            return False

        # Catch Formula
        max_hp = self.enemy_mon.get('max_hp', 1)
        hp = self.enemy_mon.get('hp', 1)
        
        # Avoid division by zero
        max_hp = max(1, max_hp)
        
        # Simplified formula: Lower HP = Higher chance
        bonus = max(0, (max_hp - hp) * 30 // max_hp) 
        catch_rate = 30 + bonus # Base 30% + bonus
        
        success = random.randint(1, 100) <= catch_rate
        
        if success:
            Logger.info("Caught the monster!")
            # Remove from active enemy party so it doesn't get picked again or count as alive
            if self.enemy_mon in self.enemy_party:
                self.enemy_party.remove(self.enemy_mon)
            
            self.result = self.ENDING_MESS[3] # Caught
            self.phase = "ended"
            return True
        else:
            Logger.info("Failed to catch! Enemy turn.")
            self.phase = "enemy"
            return False