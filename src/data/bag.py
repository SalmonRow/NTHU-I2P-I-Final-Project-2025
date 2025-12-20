import pygame as pg
import json
from src.utils import GameSettings
from src.utils.definition import Monster, Item
from src.utils import Logger


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]
    coins: int

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None, coins: int = 0):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []
        self.coins = coins

    @property
    def monsters(self) -> list[Monster]:
        return self._monsters_data

    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        pass

    def to_dict(self) -> dict[str, object]:
        # Filter monster data to only save essential fields
        clean_monsters = []
        for mon in self._monsters_data:
            clean_mon = {
                "name": mon.get("name"),
                "level": mon.get("level", 1),
                "hp": mon.get("hp", 0),
                "moves": mon.get("moves", []),
                # "xp": mon.get("xp", 0) # Save XP if present
            }
            if "xp" in mon:
                clean_mon["xp"] = mon["xp"]
            clean_monsters.append(clean_mon)

        # Clean items (remove sprite_path)
        clean_items = []
        for item in self._items_data:
            clean_item = {
                "name": item.get("name"),
                "count": item.get("count", 0)
            }
            clean_items.append(clean_item)

        return {
            "monsters": clean_monsters,
            "items": clean_items,
            "coins": self.coins
        }
    def get_item(self, item_name: str) -> dict | None:
        """Helper to find an item dictionary by name (case-insensitive)."""
        for item in self._items_data:
            if item.get('name', '').lower() == item_name.lower():
                return item
        return None
    
    def has_item(self, item_name: str) -> bool:
        item = self.get_item(item_name)
        return item is not None and item.get('count', 0) > 0

    def remove_item(self, item_name: str, count: int = 1) -> bool:
        item = self.get_item(item_name)
        if item and item.get('count', 0) >= count:
            item['count'] -= count
            if item['count'] == 0:
                self._items_data.remove(item)
            Logger.info(f"Removed {count} x {item_name}. Remaining: {item.get('count', 0)}")
            return True
        Logger.warning(f"Failed to remove {count} x {item_name}. Item not found or count too low.")
        return False
        
    def add_item(self, item_name: str, count: int = 1):
        item = self.get_item(item_name)
        if item:
            item['count'] = item.get('count', 0) + count
        else:
            # Need to fetch item data to ensure correct structure
            from src.core.data_loader import DataLoader
            static_data = DataLoader.instance().get_item_data(item_name)
            new_item = {
                "name": item_name,
                "count": count
            }
            if static_data and 'sprite_path' in static_data:
                new_item['sprite_path'] = static_data['sprite_path']
            self._items_data.append(new_item)
        Logger.info(f"Added {count} x {item_name} to bag.")

    def add_monster(self, monster_data: dict):
        self._monsters_data.append(monster_data)
        Logger.info(f"Monster {monster_data.get('name', 'Unknown')} added to bag.")

    def remove_monster(self, monster_data: dict) -> bool:
        if monster_data in self._monsters_data:
            self._monsters_data.remove(monster_data)
            Logger.info(f"Monster {monster_data.get('name', 'Unknown')} removed from bag.")
            return True
        return False

    def get_first_available_monster(self) -> dict | None:
        """Returns the first monster with HP > 0, or None if all are dead."""
        for mon in self._monsters_data:
            if mon.get('hp', 0) > 0:
                return mon
        return None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        
        # Hydrate monsters with calculated stats
        from src.core.data_loader import DataLoader
        for mon in monsters:
            DataLoader.instance().hydrate_monster(mon)
            
        items = data.get("items") or []
        for item in items:
            name = item.get('name')
            static_data = DataLoader.instance().get_item_data(name)
            if static_data and 'sprite_path' in static_data:
                item['sprite_path'] = static_data['sprite_path']

        bag = cls(monsters, items, coins=data.get("coins", 0))
        return bag

    def sort_items(self):
        """Sorts items by type, then by name."""
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()
        
        def get_sort_key(item):
            name = item.get('name', '')
            data = dl.get_item_data(name)
            # Default to zzz so unknown types go last? Or empty string for first?
            # Let's go with type string. 
            i_type = data.get('type', 'misc')
            return (i_type, name)

        self._items_data.sort(key=get_sort_key)
        Logger.info("Bag items sorted by type.")

    def add_coins(self, amount: int):
        self.coins += amount
        Logger.info(f"Added {amount} coins. Total: {self.coins}")

    def remove_coins(self, amount: int) -> bool:
        if self.coins >= amount:
            self.coins -= amount
            Logger.info(f"Removed {amount} coins. Remaining: {self.coins}")
            return True
        return False