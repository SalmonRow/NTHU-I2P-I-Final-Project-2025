import json
import os
from typing import Dict, Any, Optional
from src.utils import Logger

class DataLoader:
    _instance: Optional['DataLoader'] = None
    
    def __init__(self):
        self.monsters: Dict[str, Any] = {}
        self.moves: Dict[str, Any] = {}
        self.items: Dict[str, Any] = {}
        self.type_chart: Dict[str, Any] = {}
        self._load_data()

    @classmethod
    def instance(cls) -> 'DataLoader':
        if cls._instance is None:
            cls._instance = DataLoader()
        return cls._instance

    def _load_data(self):
        # Assume data is in d:\Coding\hell\NTHU-I2P-I-Final-Project-2025\data
        # We can construct path relative to this file or use absolute paths found earlier
        # This file is in src/core/data_loader.py
        # root is ../..
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, 'data')
        
        monsters_path = os.path.join(data_dir, 'monsters.json')
        moves_path = os.path.join(data_dir, 'moves.json')
        
        try:
            with open(monsters_path, 'r') as f:
                self.monsters = json.load(f)
            Logger.info(f"Loaded {len(self.monsters)} monsters from {monsters_path}")
        except Exception as e:
            Logger.error(f"Failed to load monsters.json: {e}")

        try:
            with open(moves_path, 'r') as f:
                self.moves = json.load(f)
            Logger.info(f"Loaded {len(self.moves)} moves from {moves_path}")
        except Exception as e:
            Logger.error(f"Failed to load moves.json: {e}")

        items_path = os.path.join(data_dir, 'items.json')
        try:
            with open(items_path, 'r') as f:
                self.items = json.load(f)
            Logger.info(f"Loaded {len(self.items)} items from {items_path}")
        except Exception as e:
            Logger.error(f"Failed to load items.json: {e}")

        types_path = os.path.join(data_dir, 'types.json')
        try:
            with open(types_path, 'r') as f:
                self.type_chart = json.load(f)
            Logger.info(f"Loaded type chart from {types_path}")
        except Exception as e:
            Logger.error(f"Failed to load types.json: {e}")

    def get_monster_species_data(self, name: str) -> Dict[str, Any]:
        return self.monsters.get(name, {})

    def get_move_data(self, move_name: str) -> Dict[str, Any]:
        return self.moves.get(move_name, {})

    def get_item_data(self, item_name: str) -> Dict[str, Any]:
        return self.items.get(item_name, {})

    def get_type_chart(self) -> Dict[str, Any]:
        return self.type_chart

    def calculate_stats(self, name: str, level: int) -> Dict[str, int]:
        species = self.get_monster_species_data(name)
        if not species:
            return {}
            
        # Formula: ((2 * Base + IV + EV) * Level / 100) + 5
        # Simplified: (2 * Base * Level / 100) + 5
        def calc_stat(base):
            return int((2 * base * level) / 100) + 5

        # HP Formula: ((2 * Base) * Level / 100) + Level + 10
        def calc_hp(base):
            return int((2 * base * level) / 100) + level + 10

        return {
            "max_hp": calc_hp(species.get('base_hp', 10)),
            "atk": calc_stat(species.get('base_atk', 10)),
            "defense": calc_stat(species.get('base_def', 10)),
            "speed": calc_stat(species.get('speed', 10)),
            "type": species.get('type', 'Normal'),
            "battle_sprite_path": species.get('battle_sprite_path', ''),
            "menu_sprite_path": species.get('menu_sprite_path', '')
        }

    def get_xp_requirement(self, level: int) -> int:
        """
        Returns the TOTAL XP required to reach the NEXT level.
        User Req: Start at 10, increase exponentially.
        Formula Used: 10 * (Level ^ 2)
        Lvl 1 -> 2: 10 XP
        Lvl 2 -> 3: 40 XP
        Lvl 5 -> 6: 250 XP
        Lvl 10 -> 11: 1000 XP
        """
        # Alternatively, could use 10 * (1.2 ** level) for true exponential.
        # But x^2 is safer for game balance usually.
        return int(10 * (level ** 2))

    def hydrate_monster(self, monster_data: Dict[str, Any]) -> None:
        """
        Updates the monster dictionary IN-PLACE with calculated stats.
        Useful for loading from save file.
        """
        name = monster_data.get('name')
        level = monster_data.get('level', 1)
        
        if not name:
            return

        stats = self.calculate_stats(name, level)
        # Update the dictionary with calculated stats
        # We preserve 'hp' (current hp) if it exists, otherwise init to max_hp
        for k, v in stats.items():
            monster_data[k] = v
            
        if 'hp' not in monster_data:
             monster_data['hp'] = stats['max_hp']
             
        # Ensure 'moves' exists if missing (auto-fill basic moves?)
        if 'moves' not in monster_data:
            # Fallback for now
            monster_data['moves'] = ["Tackle"]
