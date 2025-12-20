from __future__ import annotations
from typing import override
from .enemy_trainer import EnemyTrainer, EnemyTrainerClassification
from src.core import GameManager
from src.utils import Direction, GameSettings

class GymLeader(EnemyTrainer):
    """
    A stronger version of EnemyTrainer that rewards a specific Gem upon defeat.
    """
    gym_reward: str

    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        sprite_path: str,
        gym_reward: str,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 3, # Slightly longer LOS
        facing: Direction | None = None,
        monster: dict | None = None,
        party: list[dict] | None = None,
        defeated_at: float = 0
    ) -> None:
        super().__init__(x, y, game_manager, sprite_path, classification, max_tiles, facing, monster, party, defeated_at)
        self.gym_reward = gym_reward

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "GymLeader":
        # We need to parse common trainer fields first
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN
            
        # Party Support logic
        party = []
        monster_data = data.get("monster")
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()
        
        if monster_data:
            if isinstance(monster_data, list):
                for m in monster_data:
                    dl.hydrate_monster(m)
                    party.append(m)
            elif isinstance(monster_data, dict):
                dl.hydrate_monster(monster_data)
                party.append(monster_data)

        first_monster = party[0] if party else None

        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            data.get("sprite", "character/ow1.png"),
            data.get("gym_reward", "Water Gem"), # Custom field
            classification,
            max_tiles,
            facing,
            first_monster,
            party,
            data.get("defeated_at", 0)
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base["gym_reward"] = self.gym_reward
        # Add a flag so map loader knows it's a GymLeader
        base["is_gym_leader"] = True
        return base
