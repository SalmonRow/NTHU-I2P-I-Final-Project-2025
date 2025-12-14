from typing import Dict, Optional, List
import random
from src.utils import Logger

class BattleManager:
    # Constants for battle results: Victory, Defeat, Coward, Caught
    ENDING_MESS = ['Victory', 'Defeat', 'Coward', 'Caught'] 
    
    phase: str
    result: Optional[str]

    def __init__(self, player_mon: Dict, enemy_mon: Dict, is_wild: bool = False):
        self.player_mon = player_mon
        self.enemy_mon = enemy_mon
        self.is_wild = is_wild

        self.phase = "player"
        self.result = None
        self._turn_counter = 0

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
        # Full Gen 6+ Type Chart
        # Key: Attacking Type -> Value: { Defending Type: Multiplier }
        # Omitted types default to 1.0
        from src.core.data_loader import DataLoader
        chart = DataLoader.instance().get_type_chart()

        modifier = 1.0
        move_chart = chart.get(move_type, {})

        for d_type in def_types:
            # Multiply existing modifier by the new type effectiveness
            # Default to 1.0 (Neutral) if the pairing isn't in the exception list
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
            self.result = self.ENDING_MESS[0] # Victory
            self.phase = "ended"
            self._handle_xp_gain() # Extracted XP logic for cleaner code
        else:
             # If player just attacked, they can't force switch, it's enemy's turn
             # unless the move caused recoil death (not implemented yet)
             self.phase = "enemy"
            
        return turn_result

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
            
        return turn_result
    
    def _has_available_pokemon(self) -> bool:
        # We need access to the full party (bag). 
        # But BattleManager only holds current player_mon ref.
        # This is a design limitation. We need the Game Manager or the List.
        # We will assume the caller (Scene) handles the "forced_switch" phase 
        # because the Scene has access to the Game Manager/Bag.
        # Wait, if we set phase="forced_switch", the Scene can see that and open the menu.
        # BUT we need to know if we SHOULD force switch or just die.
        # Pass the bag validation to the Scene?
        # Ideally BattleManager should know about the party.
        # For now, let's always propose "forced_switch" if HP <= 0, 
        # and let the Scene/UI verify if there are valid monsters.
        # Actually, let's inject a "party_check_callback" or just rely on Scene.
        # Simple approach: Always set forced_switch, Scene checks availability.
        # If no mons available, Scene sets Battle Ended.
        # BETTER: Let's assume Scene checks this.
        return True # logic defered to Scene or we attach party later

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
                    Logger.info(f"What? {self.player_mon['name']} is evolving!")
                    self.player_mon['name'] = target_species
                    dl.hydrate_monster(self.player_mon)
                    Logger.info(f"Evolved into {target_species}!")

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
            self.result = self.ENDING_MESS[3] # Caught
            self.phase = "ended"
            return True
        else:
            Logger.info("Failed to catch! Enemy turn.")
            self.phase = "enemy"
            return False