
from collections import deque
import pygame as pg
from src.utils import Position, GameSettings

class NavigationManager:
    def __init__(self):
        pass

    def find_path(self, start: Position, end: Position, map_instance, can_surf: bool = False) -> list[Position] | None:
        """
        Finds a path from start to end using BFS on the map grid.
        Returns a list of Position objects representing the path (center of tiles).
        """
        start_tile = (int(start.x // GameSettings.TILE_SIZE), int(start.y // GameSettings.TILE_SIZE))
        end_tile = (int(end.x // GameSettings.TILE_SIZE), int(end.y // GameSettings.TILE_SIZE))
        
        if start_tile == end_tile:
            return []

        width = map_instance.tmxdata.width
        height = map_instance.tmxdata.height
        
        queue = deque([start_tile])
        visited = {start_tile}
        parents = {}
        
        found = False
        
        # Identify teleporter locations to avoid
        teleporter_tiles = set()
        for tele in map_instance.teleporters:
            # Convert world position to tile coordinates
            tx = int(tele.pos.x // GameSettings.TILE_SIZE)
            ty = int(tele.pos.y // GameSettings.TILE_SIZE)
            teleporter_tiles.add((tx, ty))

        # If the destination is a teleporter, allow it
        if end_tile in teleporter_tiles:
            teleporter_tiles.remove(end_tile)

        while queue:
            curr = queue.popleft()
            
            if curr == end_tile:
                found = True
                break
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_x, next_y = curr[0] + dx, curr[1] + dy
                
                if 0 <= next_x < width and 0 <= next_y < height:
                    next_pos = (next_x, next_y)
                    
                    # Skip if it's a teleporter we should avoid
                    if next_pos in teleporter_tiles:
                        continue

                    if next_pos not in visited:
                        # Check collision
                        # We create a rect for the tile to check against map collisions
                        tile_rect = pg.Rect(
                            next_x * GameSettings.TILE_SIZE,
                            next_y * GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE
                        )
                        
                        if not map_instance.check_collision(tile_rect, include_water=not can_surf):
                            visited.add(next_pos)
                            parents[next_pos] = curr
                            queue.append(next_pos)
        
        if found:
            path = []
            curr = end_tile
            while curr != start_tile:
                # Convert tile coordinate back to world position (center of tile)
                pos = Position(
                    curr[0] * GameSettings.TILE_SIZE, # + GameSettings.TILE_SIZE / 2,
                    curr[1] * GameSettings.TILE_SIZE  # + GameSettings.TILE_SIZE / 2
                )
                path.append(pos)
                curr = parents[curr]
            path.reverse()
            return path
        
        return None

    def get_navigation_points(self, map_instance) -> list[dict]:
        """
        Returns a list of interesting points to navigate to.
        Currently returns teleporters, grouped by destination to avoid redundancy.
        """
        points = []
        
        # 1. Custom Navigation Points
        if hasattr(map_instance, 'nav_points'):
             for pt in map_instance.nav_points:
                 points.append({
                     "name": pt.get("name", "Unknown"),
                     "position": Position(
                         pt["x"] * GameSettings.TILE_SIZE, 
                         pt["y"] * GameSettings.TILE_SIZE
                     )
                 })

        # 2. Teleporters - Grouped by destination
        groups = {}
        for tele in map_instance.teleporters:
            dest = tele.destination
            if dest not in groups:
                groups[dest] = []
            groups[dest].append(tele)
            
        for dest, tele_list in groups.items():
            # If there's more than one tile for a door/teleporter, pick the middle one
            if len(tele_list) > 1:
                # Sort by coordinates to find the middle
                # Sorting by y then x ensures a consistent order for both horizontal and vertical groupings
                tele_list.sort(key=lambda t: (t.pos.y, t.pos.x))
                median_tele = tele_list[len(tele_list) // 2]
            else:
                median_tele = tele_list[0]
                
            name = f"Teleport to {dest}"
            points.append({
                "name": name,
                "position": median_tele.pos
            })
            
        return points
