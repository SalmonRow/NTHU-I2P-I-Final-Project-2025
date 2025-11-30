import pygame as pg
import json
from src.utils import GameSettings
from src.utils.definition import Monster, Item
from src.utils import Logger


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []

    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        pass

    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": list(self._monsters_data),
            "items": list(self._items_data)
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
        
    def add_monster(self, monster_data: dict):
        self._monsters_data.append(monster_data)
        Logger.info(f"Monster {monster_data.get('name', 'Unknown')} added to bag.")

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        items = data.get("items") or []

        bag = cls(monsters, items)
        return bag