from __future__ import annotations
import pygame as pg
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera
from src.utils.definition import Monster



class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"

@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return

class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    monster: Monster | None
    party: list[Monster] # New: Support full party

    defeated_at: float # Timestamp in ms

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        sprite_path: str,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
        monster: Monster | None = None,
        party: list[Monster] | None = None, # New Arg
        defeated_at: float = 0 # New Arg
    ) -> None:
        super().__init__(x, y, game_manager, sprite_path)
        self.classification = classification
        self.max_tiles = max_tiles
        self.defeated_at = defeated_at
        
        # Priority: Party > Single Monster
        if party:
            self.party = party
            self.monster = party[0] if party else None
        else:
            self.monster = monster
            self.party = [monster] if monster else []

        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                raise ValueError("Idle EnemyTrainer requires a 'facing' Direction at instantiation")
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

    @override
    def update(self, dt: float) -> None:
        self._movement.update(self, dt)
        
        # Check Cooldown (using real time for persistence)
        import time
        current_time = time.time()
        is_on_cooldown = (current_time - self.defeated_at) < 180.0 # 3 minutes in seconds

        if not is_on_cooldown:
            self._has_los_to_player()
        else:
            self.detected = False # Hide exclamation

        if self.detected and input_manager.key_pressed(pg.K_f):
            self.game_manager.current_battle_en = self

            if not self.party:
                return

            # Find first alive one (in the ORIGINAL party, which should always be alive now)
            first_mon = self.party[0]
            
            player_mon = self.game_manager.bag.get_first_available_monster()
            
            if not player_mon:
                return

            # DEEP COPY for battle persistence (so trainer resets on loss/exit)
            import copy
            battle_party = copy.deepcopy(self.party)
            # Find the corresponding first mon in the copied party
            copied_first_mon = next((m for m in battle_party if m['name'] == first_mon['name']), battle_party[0])

            scene_manager.change_scene(
                'battle',
                player_monster=player_mon,
                enemy_monster=copied_first_mon,
                enemy_party=battle_party, # Pass copied Party
                is_wild_encounter = False
            )

        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pg.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pg.Rect | None:
        enx = self.position.x
        eny = self.position.y
        tile_size = GameSettings.TILE_SIZE

        max_dis = (self.max_tiles or 2) * tile_size

        if self.los_direction == Direction.UP:
            return pg.Rect(
                enx, eny - max_dis,
                tile_size, max_dis
            )

        elif self.los_direction == Direction.DOWN:
            return pg.Rect(
                enx, eny + tile_size,
                tile_size, max_dis
            )
    
        elif self.los_direction == Direction.LEFT:
            return pg.Rect(
                enx - max_dis, eny,
                max_dis, tile_size
            )

        elif self.los_direction == Direction.RIGHT:
            return pg.Rect(
                enx + max_dis, eny,
                max_dis, tile_size
            )

        return None


    def _has_los_to_player(self) -> None:
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return

        player_rect = pg.Rect(
            player.position.x, player.position.y,
            GameSettings.TILE_SIZE, GameSettings.TILE_SIZE
        )

        if los_rect.colliderect(player_rect):
            self.detected = True
        else:
            self.detected = False

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
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
                # It's a list (Existing feature in JSON!)
                for m in monster_data:
                    dl.hydrate_monster(m)
                    # AUTO-FIX: If HP is 0, reset to max_hp
                    if m.get('hp', 0) <= 0:
                         m['hp'] = m.get('max_hp', 100)
                    party.append(m)
            elif isinstance(monster_data, dict):
                # Single monster (Legacy)
                dl.hydrate_monster(monster_data)
                if monster_data.get('hp', 0) <= 0:
                     monster_data['hp'] = monster_data.get('max_hp', 100)
                party.append(monster_data)

        # Legacy Monster arg is just party[0]
        first_monster = party[0] if party else None

        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            data.get("sprite", "character/ow1.png"),
            classification,
            max_tiles,
            facing,
            first_monster, # Pass for legacy
            party, # Pass new party
            data.get("defeated_at", 0) # Load defeated_at
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        base["defeated_at"] = self.defeated_at # Persist defeated_at
        
        if self.party:
            # Clean all monsters in party (Ensure HP is cleaned/reset if needed? No, deep copy handles it)
            clean_party = []
            for m in self.party:
                clean_mon = {
                    "name": m.get("name"),
                    "level": m.get("level", 1),
                    "hp": m.get("hp", 0),
                    "moves": m.get("moves", [])
                }
                if "xp" in m:
                    clean_mon["xp"] = m["xp"]
                clean_party.append(clean_mon)
            
            if len(clean_party) == 1:
                base['monster'] = clean_party[0]
            else:
                base['monster'] = clean_party
        else:
             base['monster'] = None
            
        base["sprite"] = self.sprite_path
        return base
