import math
import pygame as pg

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.services import sound_manager, input_manager
from src.sprites import Sprite
from typing import override
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent
from src.interface.game_ui_manager import GameSceneUIManager

from src.entities.enemy_trainer import EnemyTrainer   # Existing trainer import
from src.entities.bush import BushEncounter
from src.entities.shop_keeper import ShopKeeper
from src.core.managers.navigation_manager import NavigationManager
from src.entities.offering_pillar import OfferingPillar

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    ui_manager: GameSceneUIManager

    #stuff in the bags
    wild_encounters: list['BushEncounter']
    shop_keepers: list['ShopKeeper']
    
    MAP_DISPLAY_NAMES = {
        "snow.tmx": "Frozen GPA Wasteland",
        "map.tmx": "I2P Town",
        "beach.tmx": "Sea of Tears",
        "gym.tmx": "Fire Gym",
        "water_gym.tmx": "Water Gym",
        "grass_gym.tmx": "Grass Gym"
    }
    
    def __init__(self):
        super().__init__()
        self._init_managers()
        self._init_state()
        
        # Initialize UI Manager
        self.ui_manager = GameSceneUIManager(self)

    def _init_managers(self) -> None:
        # Load game manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        
        # Setup online manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None
        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        self.online_entities = {}
        
        from src.interface.components.chat_overlay import ChatOverlay
        # Always create chat overlay, passing online_manager (which might be None)
        self.chat_overlay = ChatOverlay(self.online_manager)

    def _init_state(self) -> None:
        """Initialize scene state variables."""
        self.wild_encounters = []
        self.shop_keepers = []
        self.wild_encounters = []
        self.shop_keepers = []
        self.navigation_manager = NavigationManager()
        self.closest_enemy = None
        self.current_map_name = self.game_manager.current_map_key
        
        # Cache and scale navigation arrow
        try:
            raw_arrow = pg.image.load("assets/nav/nav_dot_red.png").convert_alpha()
            self.arrow_img = pg.transform.scale(raw_arrow, (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        except Exception as e:
            Logger.error(f"Failed to load navigation arrow: {e}")
            self.arrow_img = None


    def load_map_entities(self):
        self.wild_encounters = []
        self.offering_pillars = []
        
        # Spawn Offering Pillar on map.tmx
        if "map.tmx" in self.game_manager.current_map.path_name:
             self.offering_pillars.append(OfferingPillar(32, 24, self))

        current_map_data = self.game_manager.current_map.to_dict()
        if current_map_data is None:
            return

        wild_monster_pool = current_map_data.get("wild_mon", [])

        if wild_monster_pool: 
            bush_rects = self.game_manager.current_map._bushmap
            
            for rect in bush_rects:
                grid_x = rect.x // GameSettings.TILE_SIZE
                grid_y = rect.y // GameSettings.TILE_SIZE
                
                bush_data = {"x": grid_x, "y": grid_y}
                
                bush = BushEncounter.from_dict(bush_data, self.game_manager, wild_monster_pool)
                self.wild_encounters.append(bush)

                bush = BushEncounter.from_dict(bush_data, self.game_manager, wild_monster_pool)
                self.wild_encounters.append(bush)

        # Spawn ShopKeeper
        self.shop_keepers = self.game_manager.current_sellers

    def load_game_action(self, path: str):
        Logger.info(f"Attempting to load game from :{path}...")
        new_manager = GameManager.load(path)


        if new_manager is not None:
            self.exit()
            self.game_manager = new_manager
            self.enter()
            self.current_overlay = None
            Logger.info(f"Game Loaded successfully")
        else:
            Logger.info(f"Unsuccessful. File not found or corrupt")

    def _handle_battle_win(self):
        Logger.info("Player victory! Awarding rewards...")
        
        # 1. Award Souls for any trainer defeat
        if self.game_manager.current_battle_en:
            en = self.game_manager.current_battle_en
            from src.entities.enemy_trainer import EnemyTrainer
            from src.entities.gym_leader import GymLeader
            
            Logger.info(f"DEBUG: Battle Won against {type(en)}")
            Logger.info(f"DEBUG: Is EnemyTrainer? {isinstance(en, EnemyTrainer)}")
            Logger.info(f"DEBUG: Is GymLeader? {isinstance(en, GymLeader)}")
            
            if isinstance(en, EnemyTrainer):
                self.game_manager.bag.add_item("Souls", 1)
                
                # Reward Logic
                # 1. Calculate Base Rewards
                reward_level = 1
                if en.monster:
                    reward_level = en.monster.get('level', 1)
                elif en.party:
                    # Average level? Or Max? Let's use Max.
                    reward_level = max([m.get('level', 1) for m in en.party])
                
                xp_gain = reward_level * 10
                coin_gain = reward_level * 20
                
                is_gym = isinstance(en, GymLeader)
                if is_gym:
                    xp_gain *= 2
                    coin_gain *= 2
                
                # 2. Apply Rewards
                self.game_manager.bag.add_coins(coin_gain)
                
                # Distribute XP to all party members
                for mon in self.game_manager.bag.monsters:
                    mon['xp'] = mon.get('xp', 0) + xp_gain
                    
                # 3. Construct Notification
                msg = f"Trainer Defeated!\n"
                msg += f"Gained [YELLOW]{xp_gain} XP[WHITE] and [YELLOW]{coin_gain} Coins[WHITE].\n"
                msg += "[YELLOW]1 Soul[WHITE] obtained."
                
                # Set Cooldown (Real time)
                import time
                en.defeated_at = time.time()
            
                # 2. Award Gym Gem if it's a Gym Leader
                if is_gym:
                    gem_name = en.gym_reward
                    self.game_manager.bag.add_item(gem_name, 1)
                    msg += f"\nObtained [YELLOW]{gem_name}[WHITE]!"
                    Logger.info(f"Earned {gem_name}!")
                
                self.ui_manager.show_notification(msg)
            else:
                # Wild Encounter Win (Defeated, not caught)
                # Just show XP gained?
                # "Gained 50 XP"
                # For now, generic win message
                self.ui_manager.show_notification("Wild Pokemon Defeated!\nGained [YELLOW]XP[WHITE] and [YELLOW]Coins[WHITE]")

        self.game_manager.auto_save()

        self.game_manager.auto_save()

    def _handle_battle_lose(self):
        Logger.warning("Player loss! State saved without auto-heal or position reset.")
        self.game_manager.auto_save()
        
    def _handle_battle_run(self):
        Logger.info("Player ran from battle! State saved without auto-heal.")
        self.game_manager.auto_save()

    
    @override
    def enter(self) -> None:
        Logger.info(f'Entering Game...')
        sound_manager.play_bgm("imported/Ambient Music.wav")

        battle_result = self.game_manager.get_and_clear_battle_result() 
        
        if battle_result:
            Logger.info(f"Post-battle state received: {battle_result.upper()}. State is now clear.")
            
            res_lower = battle_result.lower()
            if res_lower == "win" or res_lower == "victory":
                self._handle_battle_win() 
            elif res_lower == "lose" or res_lower == "defeat":
                self._handle_battle_lose()
            elif res_lower == "run":
                self._handle_battle_run()
            elif res_lower == "caught":
                 # Handle Caught Pokemon
                 # Retrieve the last caught monster name if possible?
                 # Or just generic "Caught a Pokemon!"
                 # Ideally we pass data back from BattleScene but simple string result limits us.
                 # Assuming BattleScene put it in bag.
                 # We can check the last monster in bag?
                 
                 last_mon = self.game_manager.bag.monsters[-1] if self.game_manager.bag.monsters else None
                 name = last_mon['name'] if last_mon else "Pokemon"
                 
                 msg = f"Caught [CYAN]{name}[WHITE]!\nGained [YELLOW]XP[WHITE] and [YELLOW]Coins[WHITE]"
                 self.ui_manager.show_notification(msg)
                 self.game_manager.auto_save()
            
            # Clear battle entity so it doesn't linger
            self.game_manager.current_battle_en = None

        self.load_map_entities()
        self.current_map_name = self.game_manager.current_map_key
        if self.online_manager:
            self.online_manager.enter()
        
        # Initial snow map check
        is_snow_map = "snow.tmx" in self.game_manager.current_map.path_name
        self.ui_manager.is_snowing = is_snow_map
        
    @override
    def exit(self) -> None:
        # Don't stop online manager on scene switch to prevent blocking lag
        # and to keep connection alive during battles.
        # if self.online_manager:
        #    self.online_manager.exit()
        
        # Close any open popups/overlays
        if self.ui_manager:
            self.ui_manager.toggle_overlay(None)
        pass
        
    @override
    def update(self, dt: float):
        # Check if there is assigned next scene
        self.game_manager.try_switch_map()
        
        # Check if map changed
        if self.current_map_name != self.game_manager.current_map_key:
            Logger.info(f"Map switch detected: {self.current_map_name} -> {self.game_manager.current_map_key}")
            self.current_map_name = self.game_manager.current_map_key
            self.load_map_entities()
            self.ui_manager.toggle_overlay(None)
            
            # Show Map Title with friendly name
            map_filename = self.current_map_name
            if map_filename in self.MAP_DISPLAY_NAMES:
                friendly_name = self.MAP_DISPLAY_NAMES[map_filename]
                self.ui_manager.show_map_title(friendly_name)
            
            # Snow overlay effect trigger
            is_snow_map = "snow.tmx" in self.game_manager.current_map.path_name
            self.ui_manager.is_snowing = is_snow_map
            if is_snow_map:
                Logger.info("Snowing effect enabled for snow.tmx")
        
        # Update player and other data
        # Only update player movement if chat is NOT active
        
        # Update player and other data
        # Only update player movement if chat/item overlay is NOT active
        is_chatting = False
        if hasattr(self, 'chat_overlay') and self.chat_overlay:
             # Use is_blocking_input if available (handles fade out), else fallback to active
             is_chatting = getattr(self.chat_overlay, 'is_blocking_input', self.chat_overlay.active)
             
        is_item_getting = self.ui_manager.item_overlay.active
        
        if self.game_manager.player:
            if not is_chatting and not is_item_getting:
                self.game_manager.player.update(dt)
            elif is_chatting:
                # Update visuals/particles even if chatting
                self.game_manager.player.update_particles(dt)
        
        self.closest_enemy = None
        min_distance = float('inf')
        MAX_CHALLANGE_DIS = GameSettings.TILE_SIZE * 2
        any_interaction = False
        
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)

            if enemy._has_los_to_player() and enemy._distance_to_player() < min_distance:
                min_distance = enemy._distance_to_player()
                self.closest_enemy = enemy 
            
            if enemy.detected:
                 self.ui_manager.show_notification("Press [YELLOW]F[WHITE] to Battle", duration=0.6, notification_type="interaction")
                 any_interaction = True
                 
        if not is_chatting and not is_item_getting:
            for bush in self.wild_encounters:
                bush.update(dt)

            for keeper in self.shop_keepers:
                keeper.update(dt)
                if keeper.detected:
                     self.ui_manager.show_notification("Press [YELLOW]F[WHITE] to Shop", duration=0.6, notification_type="interaction")
                     any_interaction = True
                     
                if keeper.detected and input_manager.key_pressed(pg.K_f):
                     self.ui_manager.open_shop_menu()
                     
            for pillar in self.offering_pillars:
                pillar.update(dt)
                if hasattr(pillar, 'should_show_indicator') and pillar.should_show_indicator:
                     # Pillar handles its own notification call usually, but we should standardize
                     # Pillar.update calls show_notification? Let's check Pillar.update
                     # Pillar.update logic was: self.scene.ui_manager.show_notification("Press [YELLOW]F[WHITE] to Offer")
                     # We should probably let it participate in this "any_interaction" flag logic OR just tag it "interaction"
                     # Since Pillar is updated here, let's assume it also uses "interaction" type if I update it.
                     any_interaction = True

        # If no interaction is active this frame, hide any "interaction" type notification
        if not any_interaction:
            self.ui_manager.hide_notification("interaction")

        # Update GameManager (Shop logic)
        self.game_manager.update(dt)

        if not is_item_getting and not is_chatting and self.closest_enemy and min_distance <= MAX_CHALLANGE_DIS and input_manager.key_pressed(pg.K_f):
            self.trigger_battle(self.closest_enemy)
            return
        
        self.game_manager.bag.update(dt)

        if self.game_manager.player is not None and self.online_manager is not None:
             dir_str = self.game_manager.player.direction.name.lower()
             moving = self.game_manager.player.is_moving
             _ = self.online_manager.update(
                 self.game_manager.player.position.x, 
                 self.game_manager.player.position.y,
                 self.game_manager.current_map.path_name,
                 dir_str,
                 moving
             )
             
             # Sync online entities
             online_data = self.online_manager.get_list_players()
             # Logger.info(f"Online Data: {len(online_data)} players") # DEBUG
             
             current_ids = set()
             
             from src.entities.entity import Entity
             from src.utils import Direction
             
             for p_data in online_data:
                 pid = p_data["id"]
                 current_ids.add(pid)
                 
                 # Only render if on same map
                 # Logger.info(f"P{pid} Map: {p_data['map']} vs Current: {self.game_manager.current_map.path_name}") # DEBUG
                 
                 if p_data["map"] != self.game_manager.current_map.path_name:
                     # print(f"Skipping P{pid} on map {p_data['map']}")
                     continue
                 
                 # print(f"Processing P{pid} at {p_data['x']},{p_data['y']}")
                     
                 if pid not in self.online_entities:
                     # Create new entity for validation
                     # Default to ow1.png for now
                     ent = Entity(p_data["x"], p_data["y"], self.game_manager, "character/ow1.png")
                     self.online_entities[pid] = ent
                 
                 ent = self.online_entities[pid]
                 # Lerp or snap? Lerp for smoothness
                 target_x = p_data["x"]
                 target_y = p_data["y"]
                 
                 # Simple lerp with speed factor
                 lerp_speed = 10.0 * dt
                 ent.position.x += (target_x - ent.position.x) * lerp_speed
                 ent.position.y += (target_y - ent.position.y) * lerp_speed
                 
                 # If very close, snap
                 if abs(ent.position.x - target_x) < 2: ent.position.x = target_x
                 if abs(ent.position.y - target_y) < 2: ent.position.y = target_y
                 
                 # Update direction
                 d_str = p_data.get("direction", "down")
                 if d_str == "up": d = Direction.UP
                 elif d_str == "down": d = Direction.DOWN
                 elif d_str == "left": d = Direction.LEFT
                 elif d_str == "right": d = Direction.RIGHT
                 else: d = Direction.DOWN
                 
                 if ent.direction != d:
                     ent.direction = d
                     ent.animation.switch(d_str)
                     
                 # Update moving state
                 is_moving = p_data.get("moving", False)
                 
                 if is_moving:
                     ent.update(dt)
                 else:
                     ent.update(0)
                     ent.animation.accumulator = 0
            
             # Remove disconnected or different map players
             # Note: logic above doesn't remove players who switched map, so we need to filter better or remove
             # For simplicity, remove any ID not in current payload or not on current map
             
             keys_to_remove = []
             for pid in self.online_entities:
                 # Check if still in data
                 found = False
                 for p in online_data:
                     if p["id"] == pid and p["map"] == self.game_manager.current_map.path_name:
                         found = True
                         break
                 if not found:
                     keys_to_remove.append(pid)
            
             for k in keys_to_remove:
                 del self.online_entities[k]

        # Update UI
        self.ui_manager.update(dt)
        if self.chat_overlay:
            self.chat_overlay.update(dt)
        
    def trigger_battle(self, enemy_trainer: 'EnemyTrainer'):
        from src.core.services import scene_manager
        if self.game_manager.current_battle_en is not None:
            return 
        
        Logger.info(f"Battle triggered with {enemy_trainer.monster['name']}!")

        self.game_manager.current_battle_en = enemy_trainer
        player_mon = self.game_manager.bag.get_first_available_monster()
        if not player_mon:
             Logger.warning("No healthy pokemon to start battle!")
             self.game_manager.current_battle_en = None
             return

        # Use Deep Copy to prevent permanent HP loss in original trainer party
        import copy
        battle_party = copy.deepcopy(enemy_trainer.party)
        enemy_mon = next((m for m in battle_party if m['name'] == enemy_trainer.monster['name']), battle_party[0])

        scene_manager.change_scene(
            'battle',
            player_monster=player_mon, 
            enemy_monster=enemy_mon,
            enemy_party=battle_party,
            is_wild_encounter=False
        )


    @override
    def draw(self, screen: pg.Surface):        
        # 1. Determine Draw Mode (Normal vs Auto-Zoom)
        map_surf = self.game_manager.current_map._surface
        map_w = map_surf.get_width()
        map_h = map_surf.get_height()
        screen_w = GameSettings.SCREEN_WIDTH
        screen_h = GameSettings.SCREEN_HEIGHT

        # Check if map is smaller than screen in EITHER dimension
        is_small_map = map_w < screen_w or map_h < screen_h

        if is_small_map:
             # AUTO ZOOM MODE
             # 1. Calculate Scale to fill screen (Cover strategy to minimize black bars)
             scale_x = screen_w / map_w
             scale_y = screen_h / map_h
             # Use max to cover both dimensions (zooms in until borders are hit/exceeded)
             # User said "until it hits the border of the map and it would stop... auto zoom in"
             # If we use MIN, we fit the map inside screen (black bars present).
             # If we use MAX, we zoom in so the "smaller" dimension fits the screen, potentially cropping the other.
             # User said "show the least of the black parts".
             # Actually, if we just want to fill the screen, we need to cover.
             zoom_scale = max(scale_x, scale_y)
             
             # 2. Render World at 1:1 to a temp surface
             # Size of temp surface? 
             # It needs to be the whole map, because we are scaling the whole map.
             # If we only render a part, we might miss things when scaled.
             # Since map is small, rendering full map is cheap.
             world_surf = pg.Surface((map_w, map_h))
             
             # Camera at 0,0 relative to map
             fixed_cam = PositionCamera(0, 0)
             
             # Draw Map
             self.game_manager.current_map.draw(world_surf, fixed_cam)
             
             # Draw Arrows
             if self.arrow_img and hasattr(self.game_manager.player, 'path') and self.game_manager.player.path:
                 # Logic copied from below, adapted for world_surf
                 try:
                    path = self.game_manager.player.path
                    if len(path) > 0:
                        for i in range(len(path)):
                            pos = path[i]
                            angle = 0
                            if i < len(path) - 1:
                                next_pos = path[i+1]
                                dx = next_pos.x - pos.x
                                dy = next_pos.y - pos.y
                                angle = -math.degrees(math.atan2(dy, dx))
                            rotated_arrow = pg.transform.rotate(self.arrow_img, angle)
                            offset = GameSettings.TILE_SIZE // 2
                            rect = rotated_arrow.get_rect(center=(pos.x + offset, pos.y + offset))
                            world_surf.blit(rotated_arrow, fixed_cam.transform_rect(rect))
                 except Exception: pass
             
             # Draw Entities
             renderables = []
             if self.game_manager.player: renderables.append(self.game_manager.player)
             renderables.extend(self.game_manager.current_enemy_trainers)
             renderables.extend(self.wild_encounters)
             renderables.extend(self.shop_keepers)
             renderables.extend(self.offering_pillars)
             if self.online_entities: renderables.extend(self.online_entities.values())
             
             def get_sort_key(entity):
                if hasattr(entity, 'sort_y'): return entity.sort_y
                if hasattr(entity, 'hitbox'): return entity.hitbox.bottom
                if hasattr(entity, 'position'): return entity.position.y + GameSettings.TILE_SIZE
                return 0
             renderables.sort(key=get_sort_key)
             
             for entity in renderables:
                 entity.draw(world_surf, fixed_cam)
                 
             # 3. Scale Up
             target_w = int(map_w * zoom_scale)
             target_h = int(map_h * zoom_scale)
             scaled_surf = pg.transform.scale(world_surf, (target_w, target_h))
             
             # 4. Center on Screen
             # Since we zoomed to cover, the surface is >= screen size.
             # We need to center the camera on the player relative to this scaled surface.
             
             # Where is the player on the SCALED surface?
             # Player world pos (px, py) -> Scaled pos (px*zoom, py*zoom)
             if self.game_manager.player:
                 px = (self.game_manager.player.position.x + GameSettings.TILE_SIZE/2) * zoom_scale
                 py = (self.game_manager.player.position.y + GameSettings.TILE_SIZE/2) * zoom_scale
             else:
                 px, py = target_w/2, target_h/2
             
             # We want (px, py) to be at screen center (sw/2, sh/2)
             # So we default offset: dest_x = sw/2 - px
             dest_x = screen_w/2 - px
             dest_y = screen_h/2 - py
             
             # Clamp destination so we don't show empty space?
             # Surface is larger than screen (Cover strategy).
             # We can clamp dest_x between (screen_w - target_w) and 0.
             # If we clamp, it acts like the normal camera logic!
             
             min_x = screen_w - target_w
             min_y = screen_h - target_h
             
             dest_x = max(min_x, min(dest_x, 0))
             dest_y = max(min_y, min(dest_y, 0))
             
             screen.blit(scaled_surf, (dest_x, dest_y))
             
        else:
            # NORMAL DRAW MODE
            camera = PositionCamera(0, 0)
            if self.game_manager.player:
                camera = self.game_manager.player.camera
            
            # 1. Draw Map (Background)
            self.game_manager.current_map.draw(screen, camera)

            # Draw Navigation Path Arrows (Under entities)
            if self.arrow_img and hasattr(self.game_manager.player, 'path') and self.game_manager.player.path:
                try:
                    path = self.game_manager.player.path
                    if len(path) > 0:
                        for i in range(len(path)):
                            pos = path[i]
                            # Determine rotation
                            angle = 0
                            if i < len(path) - 1:
                                next_pos = path[i+1]
                                dx = next_pos.x - pos.x
                                dy = next_pos.y - pos.y
                                angle = -math.degrees(math.atan2(dy, dx))
                            
                            rotated_arrow = pg.transform.rotate(self.arrow_img, angle)
                            # Center on tile: pos.x/y is topleft of tile
                            offset = GameSettings.TILE_SIZE // 2
                            rect = rotated_arrow.get_rect(center=(pos.x + offset, pos.y + offset))
                            
                            # Transform to camera view
                            screen.blit(rotated_arrow, camera.transform_rect(rect))
                except Exception as e:
                    Logger.error(f"Error drawing path: {e}")

            # 2. Collect all renderable entities
            renderables = []

            # Player
            if self.game_manager.player:
                renderables.append(self.game_manager.player)
            
            # Enemy Trainers
            renderables.extend(self.game_manager.current_enemy_trainers)
            renderables.extend(self.wild_encounters)
            renderables.extend(self.shop_keepers)
            renderables.extend(self.offering_pillars)

            # Online Players
            if self.online_entities:
                renderables.extend(self.online_entities.values())


            def get_sort_key(entity):
                 # Online players have .sort_y
                if hasattr(entity, 'sort_y'):
                    return entity.sort_y
                
                # Entities usually have a hitbox
                if hasattr(entity, 'hitbox'):
                    return entity.hitbox.bottom
                
                # Fallback to position
                if hasattr(entity, 'position'):
                    return entity.position.y + GameSettings.TILE_SIZE
                
                return 0

            renderables.sort(key=get_sort_key)
            
            # 4a. Draw Background Particles (e.g. Offering)
            self.ui_manager.draw_background_particles(screen)

            # 4b. Draw Sorted Entities
            for entity in renderables:
                entity.draw(screen, camera)

        # 5. Draw UI (Always on top)
        self.game_manager.bag.draw(screen)
        self.ui_manager.draw(screen)
        if self.chat_overlay:
            self.chat_overlay.draw(screen)