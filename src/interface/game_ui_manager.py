import pygame as pg
from src.utils import Logger, GameSettings
from src.core.services import sound_manager
from src.utils import Logger, GameSettings
from src.core.services import sound_manager, input_manager
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent, Label, Icon, Notification
from src.interface.components.minimap import MiniMap
from src.core import GameManager
from src.core.services import scene_manager
from src.interface.components.shop_ui import ShopUI
from src.interface.components.item_obtained_overlay import ItemObtainedOverlay

class GameSceneUIManager:
    def show_notification(self, message: str, duration: float = 2.0, notification_type: str = "generic"):
        self.notification.show(message, duration, notification_type)

    def hide_notification(self, target_type: str = None):
        self.notification.hide(target_type)

    def __init__(self, game_scene):
        self.scene = game_scene
        self.game_manager: GameManager = game_scene.game_manager
        
        self.current_overlay = None
        self._last_volume = 0.5
        
        # Overlay for Item Get
        self.item_overlay = ItemObtainedOverlay(close_callback=self._on_item_overlay_close)
        self.item_queue = [] # tuple of (name, count)
        
        # State for item usage
        self.selected_item_for_use: dict | None = None

        self.waiting_for_pokemon_selection: bool = False
        
        # Evolution State
        self.evolving_monster: dict | None = None
        self.evolution_sprite_current: pg.Surface | None = None
        self.evolution_sprite_next: pg.Surface | None = None
        self.anim_timer = 0.0
        self.is_evolving = False
        self.evo_flash_alpha = 0
        
        self.is_offering = False
        self.offering_timer = 0.0
        
        self.confirm_popup: Popup | None = None
        self.confirm_yes_btn: Button | None = None
        self.confirm_cancel_btn: Button | None = None
        
        # Snow Effect
        self.is_snowing = False
        self.snow_particles: list[dict] = []
        
        # Particles
        self.particles: list[dict] = []
        self.star_image: pg.Surface | None = None
        
        # Notification System
        self.notification = Notification()

        # UI Components
        self.setting_popup: Popup = None
        self.bag_popup: Popup = None
        self.evo_popup: Popup = None # New popup
        self.setting_button: Button = None
        self.bag_button: Button = None
        self.save_button: Button = None
        self.load_button: Button = None
        self.use_item_btn: Button = None # New "USE" button
        self.volume_slider: Slider = None
        self.hitbox_checkbox: Checkbox = None
        self.mute_check: Checkbox = None
        self.monster_list: MonsterListComponent = None
        self.item_list: ItemListComponent = None

        # MiniMap
        self.minimap: MiniMap = None
        
        # Big Map Popup
        self.big_map_popup: Popup = None
        self.big_minimap: MiniMap = None
        
        self.shop_ui = ShopUI(self)

        # Initialize everything
        self._init_popups()
        self._init_overlay_buttons()
        self._init_setting_components()
        self._init_bag_components()
        self._init_offering_components()
        self._init_big_map_components()

        

        
        self.minimap = MiniMap(self.scene, x=10, y=10)
        
        # Invisible button to handle clicks on the minimap
        self.minimap_btn = Button(
             None, None, # No image
             self.minimap.rect.x, self.minimap.rect.y,
             self.minimap.rect.width, self.minimap.rect.height,
             on_click=lambda: self.toggle_overlay("big_map")
        )
        
        self.shop_ui = ShopUI(self)

    def _init_popups(self) -> None:
        """Create setting and bag popup windows."""
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(self.current_overlay)
        
        #popups for when pushing buttons
        self.setting_popup = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.bag_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)
        self.nav_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)
        
        # Evolution Popup (Standard Size)
        # We pass screen_size so Popup centers itself automatically - User requested half size but centered
        self.evo_popup = Popup("UI/raw/UI_Flat_Frame02a.png", (screen_size[0] // 2, screen_size[1] // 2), close_callback)
        self.evo_popup.interactive_components = []

        
        # Big Map Popup (Almost full screen)
        # self.nav_popup was the old one, we replace/augment it.
        # Let's clean up nav_popup usage if we are fully replacing it.
        # But for safety, I will keep nav_popup as is for now in case of regression, but use big_map_popup for the new feature.
        
        big_w = int(screen_size[0] * 0.9)
        big_h = int(screen_size[1] * 0.9)
        self.big_map_popup = Popup("UI/raw/UI_Flat_Frame01a.png", (big_w, big_h), close_callback)
        self.big_map_popup.interactive_components = []
        self.big_map_popup.frame_rect.center = (screen_size[0] // 2, screen_size[1] // 2)

        
        # FIX: Manual Recenter to Screen Center
        # Popup defaults to centering on the 'size' passed (which is half screen, so it ends up at 1/4)
        self.evo_popup.frame_rect.center = (GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2)
        
        self._init_nav_components()
        self._init_evolution_components()
        
    def _init_big_map_components(self):
        """Init components for the Big Map (Expanded Minimap + Navigation)."""
        frame = self.big_map_popup.frame_rect
        padding = 30
        
        # 1. Big Minimap on the LEFT
        # Calculate size: fill left 60-70% of the popup?
        # Let's make it square if possible, or rectangular if supported. MiniMap is inherently square currently (rect).
        # We might need to update MiniMap to support non-square if we want full left pane.
        # For now, let's keep it square, maximizing height.
        
        map_size = frame.height - (padding * 2)
        map_x = frame.x + padding
        map_y = frame.y + padding
        
        # Use a smaller zoom scale (zoomed out) -> larger value shows more map? 
        # Wait, ZOOM_SCALE = 0.18. Smaller variable = smaller sprites (zoomed out).
        # We want to see MORE of the map, so we want smaller tiles?
        # If ZOOM_SCALE. 1.0 = 1:1. 0.1 = 1/10th size.
        # The current MiniMap.ZOOM_SCALE is 0.18.
        # If we use 0.18 in a BIGGER window, we see MORE world area.
        # So we can keep the same scale or slightlyadjust. 
        # Let's try 0.25 for a slightly "bigger" view of tiles, or keep existing.
        # Actually user wants "bigger version of the minimap".
        # Let's just create it with a large size.
        
        self.big_minimap = MiniMap(self.scene, x=map_x, y=map_y, size=map_size, auto_zoom=True)
        # We do NOT append MiniMap to interactive_components because we draw it manually or need custom update?
        # MiniMap IS a UIComponent. 
        # But self.big_map_popup calls draw() on its components.
        # self.minimap.draw() takes 'screen'. 
        # So yes, we can add it, BUT we need to make sure BigMap popup handles it correctly.
        # Actually, self.minimap implementation handles its own background and drawing logic.
        # So it's safe to add. 
        # However, standard popup usage might overlay things.
        # Let's store it separately to update it specifically if needed, or just append it.
        # Ideally, we want to click it to teleport? (Feature for later maybe).
        
        # Add to components list so it gets drawn/updated automatically by Popup?
        # Wait, Popup.draw loops interactive_components.
        # MiniMap.draw is standard.
        # So yes.
        self.big_map_popup.interactive_components.append(self.big_minimap)
        
        # 2. Navigation Panel on the RIGHT
        # Just a label for now, buttons generated dynamically
        label_x = map_x + map_size + padding
        label_y = map_y
        
        nav_label = Label("Navigation", label_x, label_y, fontsize=40, fontfam=1, color=(19, 53, 133))
        self.big_map_popup.interactive_components.append(nav_label)
        
        # Store start position for nav buttons
        self.big_map_nav_start_x = label_x
        self.big_map_nav_start_y = label_y + 60

    def _init_nav_components(self):
        """Init components for navigation popup."""
        nav_frame_x = self.nav_popup.frame_rect.x
        nav_frame_y = self.nav_popup.frame_rect.y
        
        # Add Label
        self.nav_popup.interactive_components.append(
            Label("Navigation", nav_frame_x + 30, nav_frame_y + 35, fontsize=40, fontfam=1, color=(19, 53, 133))
        )
        
        # Dynamic button generation based on navigation points
        # We need to access map. But map changes. So we should probably regenerate this when opening the popup.
        pass

    def _init_overlay_buttons(self) -> None:
        """Create overlay buttons and save/load buttons."""
        # Top-right overlay toggle buttons
        self.setting_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 70, 10, 
            60,
            60,
            on_click=lambda : self.toggle_overlay("setting")
        )

        self.bag_button = Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 140, 10,
            60,
            60,
            on_click=lambda : self.toggle_overlay("bag")
        )

        self.nav_button = Button(
            "UI/button_play.png",
            "UI/button_play_hover.png",
            GameSettings.SCREEN_WIDTH - 210, 10,
            60,
            60,
            on_click=lambda : self.toggle_overlay("big_map")
        )
        # Save/Load buttons inside setting popup
        JASON = "saves/game0.json"
        self.save_button = Button(
            "UI/button_save.png",
            "UI/button_save_hover.png",
            self.setting_popup.frame_rect.left + 30,
            self.setting_popup.frame_rect.top + 30,
            80,
            80,
            on_click=lambda: self.game_manager.save(JASON)
        )
        self.setting_popup.interactive_components.append(self.save_button)

        self.load_button = Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            self.setting_popup.frame_rect.left + 120,
            self.setting_popup.frame_rect.top + 30,
            80,
            80,
            on_click=lambda: self.scene.load_game_action(JASON)
        )
        self.setting_popup.interactive_components.append(self.load_button)
    def _init_overlay_text(self) -> None:
        pass

    def _init_setting_components(self) -> None:
        """Create sliders and checkboxes for the settings popup."""
        setting_frame_x = self.setting_popup.frame_rect.x
        setting_frame_y = self.setting_popup.frame_rect.y
        setting_frame_width = self.setting_popup.frame_rect.width
        
        # Volume slider
        slider_width = 300
        slider_height = 40
        slider_x = setting_frame_x + (setting_frame_width // 2) - (slider_width // 2)
        slider_y = setting_frame_y + 150

        self.volume_slider = Slider(
            x=slider_x, y=slider_y,
            width=slider_width, height=slider_height,
            min_val=0.0, max_val=100.0,
            initial_val=sound_manager.get_volume() * 100,
            val_change=lambda v: sound_manager.set_volume(v/100),
            bar_path="UI/raw/UI_Flat_Bar05a.png",
            handle_path="UI/raw/UI_Flat_Button01a_3.png",
            label= "Master Volume"
        )
        self.setting_popup.interactive_components.append(self.volume_slider)

        # Checkboxes
        cb_size = 50
        cb_x = setting_frame_x + 140
        cb_y = slider_y + slider_height + 50

        self.hitbox_checkbox = Checkbox(
            x=cb_x, y=cb_y,
            size=cb_size,
            initial_checked=GameSettings.DRAW_HITBOXES,
            on_toggle=lambda checked: (
                setattr(GameSettings, "DRAW_HITBOXES", checked),
                Logger.info(f"Hitboxes has been set to :{checked}")
            ),
            label="Hitbox",
            unchecked_path="UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='UI/raw/UI_Flat_ToggleOn01a.png',
        )
        self.setting_popup.interactive_components.append(self.hitbox_checkbox)

        self.mute_check = Checkbox(
            x=cb_x, y=cb_y + 75,
            size=cb_size, 
            initial_checked= (sound_manager.get_volume() == 0), 
            on_toggle=self.toggle_mute, 
            label="Mute Audio",
            unchecked_path="UI/raw/UI_Flat_ToggleOff01a.png", 
            checked_path='UI/raw/UI_Flat_ToggleOn01a.png',
        )
        self.setting_popup.interactive_components.append(self.mute_check)

        # Buttons
        self.menuscene_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.setting_popup.frame_rect.right,
            self.setting_popup.frame_rect.bottom,
            80,
            80,
            on_click=lambda: scene_manager.change_scene("menu")
        )

        self.setting_popup.interactive_components.append(self.menuscene_button)

    def _init_bag_components(self) -> None:
        """Create monster and item list components for the bag popup."""
        bag_frame_x = self.bag_popup.frame_rect.x
        bag_frame_y = self.bag_popup.frame_rect.y
        bag_frame_width = self.bag_popup.frame_rect.width
        bag_frame_height = self.bag_popup.frame_rect.height

        list_width = (bag_frame_width // 2) - 40
        list_height = bag_frame_height - 100

        self.monster_list = MonsterListComponent(
            x=bag_frame_x + 20, y=bag_frame_y + 80,
            width=list_width,height=list_height,
            monster_list=self.game_manager.bag._monsters_data,
            on_click=self.on_bag_monster_click
        )
        self.bag_popup.interactive_components.append(self.monster_list)

        # Add "Bag" Label
        bag_label = Label(
            "Bag", 
            x=bag_frame_x + 30, 
            y=bag_frame_y + 35, 
            fontsize=40, fontfam=1,
            color=(19, 53, 133)
        )
        self.bag_popup.interactive_components.append(bag_label)

        self.item_list = ItemListComponent(
            x=bag_frame_x + list_width + 30, y=bag_frame_y + 80,
            width=list_width,height=list_height,
            item_list=self.game_manager.bag._items_data,
            on_click=self.on_bag_item_click
        )
        self.bag_popup.interactive_components.append(self.item_list)
        
        # Initialize Use Button (Hidden by default)
        self.use_item_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            self.bag_popup.frame_rect.right - 150, 
            self.bag_popup.frame_rect.bottom - 80,
            120, 50,
            text="USE",
            on_click=self.on_use_button_click
        )
        # Do not append to interactive_components yet, only when needed

        # Initialize Options Buttons (Extract / Cancel)
        # Initialize Options Buttons (Extract / Cancel / Evolve) - Horizontal Layout
        # Order from Right to Left: Cancel <- Extract <- Evolve
        # Base Y
        base_y = self.bag_popup.frame_rect.bottom - 80
        btn_width = 120
        spacing = 10
        
        # 1. Cancel (Rightmost)
        cancel_x = self.bag_popup.frame_rect.right - 150
        self.cancel_opts_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            cancel_x, 
            base_y,
            btn_width, 50,
            text="CANCEL",
            on_click=self._hide_monster_options
        )
        
        # 2. Extract (Left of Cancel)
        extract_x = cancel_x - btn_width - spacing
        self.extract_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            extract_x, 
            base_y,
            btn_width, 50,
            text="EXTRACT",
            on_click=self._on_extract_click
        )

        # 3. Evolve (Left of Extract)
        evolve_x = extract_x - btn_width - spacing
        self.evolve_option_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            evolve_x, 
            base_y,
            btn_width, 50,
            text="EVOLVE",
            on_click=self._on_evolve_option_click
        )

    def toggle_overlay(self, overlay_name) -> None:
        # Always reset selection state when toggling overlays
        self.selected_item_for_use = None
        self.waiting_for_pokemon_selection = False
        if self.use_item_btn in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.remove(self.use_item_btn)
            
        if overlay_name is None:
            self.current_overlay = None
            Logger.info("Overlay closed.")
        elif self.current_overlay == overlay_name:
            self.current_overlay = None
            Logger.info(f"Overlay {overlay_name} toggled OFF.")
        else:
            self.current_overlay = overlay_name
            Logger.info(f"Overlay switched to {overlay_name}.")
            # If opening bag, sort items
            if self.current_overlay == "bag":
                if self.game_manager and self.game_manager.bag:
                    self.game_manager.bag.sort_items()
                    # Refresh Lists
                    self.monster_list.set_monsters(self.game_manager.bag.monsters)
                    self.item_list.set_items(self.game_manager.bag._items_data)
            
            if self.current_overlay == "nav":
                self._regenerate_nav_buttons()

            if self.current_overlay == "big_map":
                self._regenerate_big_map_nav_buttons()
                
    def _init_evolution_components(self):
        """Init components for evolution confirmation."""
        # Frame relative coordinates
        frame = self.evo_popup.frame_rect
        cw, ch = frame.width, frame.height
        
        button_w, button_h = 150, 60
        spacing = 40
        total_btns_w = (button_w * 2) + spacing
        
        # Relative to frame top-left
        btn_start_x = frame.x + (cw - total_btns_w) // 2
        # Center buttons vertically in the bottom half?
        btn_y = frame.centery + 50
        
        # Label
        self.evo_label = Label("Evolve this Pokemon?", frame.centerx, frame.centery - 50, fontsize=30, color=(19, 53, 133), align="center")
        self.evo_popup.interactive_components.append(self.evo_label)

        # Buttons - Callbacks will need to access current context
        self.evo_yes_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            btn_start_x, btn_y, button_w, button_h, text="EVOLVE",
            on_click=self._on_evo_yes_click
        )
        self.evo_popup.interactive_components.append(self.evo_yes_btn)
        
        self.evo_no_btn = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            btn_start_x + button_w + spacing, btn_y, button_w, button_h, text="CANCEL",
            on_click=lambda: self.toggle_overlay(None)
        )
        self.evo_popup.interactive_components.append(self.evo_no_btn)

    def _on_evo_yes_click(self):
        # We need the monster. stored in waiting_for_pokemon_selection? No, different flow.
        # on_bag_monster_click triggers this.
        # We need to store the candidate.
        if hasattr(self, 'evolution_candidate'):
             self._start_evolution(self.evolution_candidate)
        self.toggle_overlay(None)

    def _regenerate_big_map_nav_buttons(self):
        """Populate the right side of the Big Map with nav buttons."""
        # Clean up old buttons first
        # We need to distinguish buttons from static labels/minimap.
        # Best way: Keep static components in a separate list or rebuild interactive_components
        # But we added big_minimap and label to interactive_components.
        # Let's just remove Button instances that are NOT the close button (internal_buttons[0]).
        
        # Reset to base components: internal closing button (built-in in Popup), big_minimap, nav_label
        # Note: Popup.__init__ adds internal close button to self.internal_buttons AND self.interactive_components
        # So we should be careful.
        
        # Safe approach: Filter out old generated buttons.
        # We can just keep the first 3 components? (Close Btn, MiniMap, Label).
        # DEPENDENCY: Order of initialization in _init_big_map_components matters.
        # self.big_map_popup initialized -> adds Close Button (index 0).
        # _init_big_map_components -> adds MiniMap (index 1), Label (index 2).
        # So we keep [:3].
        
        if len(self.big_map_popup.interactive_components) > 3:
             self.big_map_popup.interactive_components = self.big_map_popup.interactive_components[:3]
             
        if not self.scene.navigation_manager:
            return
            
        points = self.scene.navigation_manager.get_navigation_points(self.game_manager.current_map)
        
        x = self.big_map_nav_start_x
        y = self.big_map_nav_start_y
        
        for i, pt in enumerate(points):
            # Strip extensions and common prefixes
            name = pt['name'].replace('.tmx', '').replace('.json', '').replace('Teleport to ', '')
            pos = pt['position']
            
            # Note for user: Add icon_path="assets/gui/icon_name.png" here to show icons
            btn = Button(
                "UI/raw/UI_Flat_Button01a_2.png",
                "UI/raw/UI_Flat_Button01a_1.png",
                x,
                y + i * 60,
                200, 50,
                text=name,
                on_click=lambda p=pos: self._on_nav_point_click(p),
                icon_path="nav/arrow_path.png", # USER: REPLACE WITH ICON PATH LATER
                icon_size=(32, 24)
            )
            self.big_map_popup.interactive_components.append(btn)

    def _regenerate_nav_buttons(self):
        """Regenerate navigation buttons based on current map points."""
        # Clear existing buttons (except maybe label)
        # Keep first item if it's label
        self.nav_popup.interactive_components = [self.nav_popup.interactive_components[0]] 
        
        if not self.scene.navigation_manager:
            return

        points = self.scene.navigation_manager.get_navigation_points(self.game_manager.current_map)
        
        start_x = self.nav_popup.frame_rect.x + 50
        start_y = self.nav_popup.frame_rect.y + 100
        
        for i, pt in enumerate(points):
            name = pt['name'].replace('.tmx', '').replace('.json', '').replace('Teleport to ', '')
            pos = pt['position']
            
            btn = Button(
                "UI/raw/UI_Flat_Button01a_2.png",
                "UI/raw/UI_Flat_Button01a_1.png",
                start_x,
                start_y + i * 60,
                200, 50,
                text=name,
                on_click=lambda p=pos: self._on_nav_point_click(p),
                icon_path=None, # USER: REPLACE WITH ICON PATH LATER
                icon_size=(32, 32)
            )
            self.nav_popup.interactive_components.append(btn)

    def _on_nav_point_click(self, target_pos):
        Logger.info(f"Navigating to {target_pos}...")
        can_surf = self.game_manager.player.is_surfing
        path = self.scene.navigation_manager.find_path(
            self.game_manager.player.position,
            target_pos,
            self.game_manager.current_map,
            can_surf=can_surf
        )
        if path:
            self.game_manager.player.path = path
            self.toggle_overlay(None) # Close menu
        else:
            Logger.warning("No path found!")

    def toggle_mute(self, is_muted: bool) -> None:
        if is_muted:
            self._last_volume = sound_manager.get_volume()
            sound_manager.set_volume(0.0) 
        else:
            restore_volume = getattr(self, '_last_volume', 0.5)
            sound_manager.set_volume(restore_volume)

    def show_item_obtained(self, item_name: str, count: int):
        self.item_queue.append((item_name, count))
        if not self.item_overlay.active:
            self._process_item_queue()

    def _process_item_queue(self):
        if not self.item_queue:
            return
            
        next_item = self.item_queue.pop(0)
        self.item_overlay.show(next_item[0], next_item[1])
        # Pause game logic while showing? Maybe not strictly required but good for polish.
        # self.scene.pause() # If we had one

    def _on_item_overlay_close(self):
        # Check if more items
        if self.item_queue:
            self._process_item_queue()
        else:
            Logger.info("All item animations finished.")

    def update(self, dt: float) -> None:
        # Notification
        self.notification.update(dt)

        if self.item_overlay.active:
            self.item_overlay.update(dt)
            # existing update logic might still run, but we blocked player movement in GameScene
            
        # Update overlay buttons only if no overlay is active AND not chatting
        is_chatting = False
        if hasattr(self.scene, 'chat_overlay') and self.scene.chat_overlay:
            is_chatting = getattr(self.scene.chat_overlay, 'is_blocking_input', False)

        if self.current_overlay is None and not is_chatting:
            self.setting_button.update(dt) 
            self.bag_button.update(dt) 
            # self.nav_button.update(dt)

            self.minimap_btn.update(dt)
        
        if self.current_overlay == "setting":
            self.setting_popup.update(dt)
        
        if self.current_overlay == "bag":
            self.bag_popup.update(dt)
            # If manually drawing button on top, we still need to update it
            # It's in interactive_components so popup updates it, but if we remove it?
            # It IS in interactive_components during selection phase (added in on_bag_item_click)
            pass

        if self.current_overlay == "nav":
            self.nav_popup.update(dt)
            
        if self.current_overlay == "shop":
            self.shop_ui.update(dt)
            
        if self.current_overlay == "evolution":
            self.evo_popup.update(dt)

        if self.current_overlay == "big_map":
            self.big_map_popup.update(dt)

        if self.current_overlay == "offering":
            self.offering_popup.update(dt)

        # Standard minimap update (background)
        self.minimap.update(dt) 
        
        # Input Handling for Big Map
        # Toggle with 'M'
        is_chatting = False
        if hasattr(self.scene, 'chat_overlay') and self.scene.chat_overlay:
            is_chatting = getattr(self.scene.chat_overlay, 'is_blocking_input', False)

        if not is_chatting and input_manager.key_pressed(pg.K_m):
            if self.current_overlay == "big_map":
                self.toggle_overlay(None)
            elif self.current_overlay is None:
                self.toggle_overlay("big_map")

        # Update Evolution Animation
        if self.is_evolving:
            self._update_evolution_animation(dt)
            return # Block other inputs during evolution
            
        if self.is_offering:
            self._update_offering_animation(dt)
            return

        if self.is_snowing:
            self._update_snow_effect(dt)

        # Removed ad-hoc confirm_popup update block since it's now an overlay

 

        # Check for ESC to Cancel Selection or Close Overlay
        if input_manager.key_pressed(pg.K_ESCAPE):
            if self.waiting_for_pokemon_selection:
                self._cancel_selection()
            elif self.current_overlay is not None:
                self.toggle_overlay(None)

    def draw(self, screen: pg.Surface) -> None:
        # Draw overlay background if active
        if self.current_overlay is not None:
            darken = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
            )
            darken.set_alpha(128) # 50% alpha background
            darken.fill((0,0,0))
            screen.blit(darken, (0, 0))  

            if self.current_overlay == "setting":
                self.setting_popup.draw(screen)
            elif self.current_overlay == "bag":
                self.bag_popup.draw(screen)
            elif self.current_overlay == "nav":
                self.nav_popup.draw(screen)
            elif self.current_overlay == "big_map":
                self.big_map_popup.draw(screen)
            elif self.current_overlay == "offering":
                self.offering_popup.draw(screen)
            elif self.current_overlay == "evolution":
                self.evo_popup.draw(screen)
            elif self.current_overlay == "shop":
                self.shop_ui.draw(screen)

        # Draw bottom buttons only if no overlay is active
        if self.current_overlay is None:
            self.setting_button.draw(screen)
            self.bag_button.draw(screen)
            # self.nav_button.draw(screen)

        # Draw Spotlight Overlay for Item Selection
        if self.waiting_for_pokemon_selection:
             # 1. Darken everything
             spotlight_dim = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
             spotlight_dim.set_alpha(100) # Lightened from 180 to 100
             spotlight_dim.fill((0, 0, 0))
             screen.blit(spotlight_dim, (0, 0))
             
             # 2. Draw Text Prompt
             Label.from_center("Select a Pokemon...", offset_y=-250, color=(255, 255, 255)).draw(screen)
             
             # 3. Redraw Monster List on top
             if self.monster_list:
                 self.monster_list.draw(screen)
                 
             # 4. Redraw Cancel/Use Button on top
             if self.use_item_btn:
                 self.use_item_btn.draw(screen)

        if self.current_overlay is None and not self.is_evolving and not self.is_offering:
            self.minimap.draw(screen)

        # Removed offering particle drawing from here (moved to background)
        
        # Removed ad-hoc confirm_popup draw block

        # Draw Evolution Animation
        if self.is_evolving and self.evolution_sprite_current:
             # Full Dim
             bg = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
             bg.set_alpha(200) # Dim instead of black
             bg.fill((0,0,0))
             screen.blit(bg, (0,0))
             
             # Draw Sprite Center
             cx, cy = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2
             rect = self.evolution_sprite_current.get_rect(center=(cx, cy))
             
             # Draw Particles BEHIND sprite? User said "particle like a start from the assets this one in the background"
             # So draw particles first
             for p in self.particles:
                 if self.star_image:
                     # Scale based on life?
                     scale = p['life'] 
                     if scale > 0:
                         img = pg.transform.scale(self.star_image, (int(30*scale), int(30*scale)))
                         screen.blit(img, (p['x'], p['y']))
             
             screen.blit(self.evolution_sprite_current, rect)
             
             # Draw White Flash Overlay
             if self.evo_flash_alpha > 0:
                 flash_surf = self.evolution_sprite_current.copy()
                 # Fill with white using BLEND_RGBA_MULT (keep alpha) or LOCK?
                 # Easiest way to make a white silhouette:
                 mask = pg.mask.from_surface(self.evolution_sprite_current)
                 white_surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0,0,0,0))
                 white_surf.set_alpha(self.evo_flash_alpha)
                 screen.blit(white_surf, rect)

             # Draw Text logic if needed (e.g. "What? X is evolving!")
             if self.anim_timer < 2.0:
                 Label.from_center(f"What? {self.evolving_monster['name']} is evolving!", offset_y=200, color=(255, 255, 255)).draw(screen)
             elif self.anim_timer > 4.0:
                 # It has evolved
                 Label.from_center(f"Congratulations! Your Pokemon evolved!", offset_y=200, color=(255, 255, 255)).draw(screen)
                 
                 # Ensure stats and next evo status are correct
                 # But we only do this ONCE.
                 if not getattr(self, '_post_evo_hydrated', False):
                     from src.core.data_loader import DataLoader
                     DataLoader.instance().hydrate_monster(self.evolving_monster)
                     self._post_evo_hydrated = True

        if self.item_overlay.active:
            self.item_overlay.draw(screen)

        if self.is_snowing:
            self.draw_snow_overlay(screen)

        # Draw Notification (Always on top)
        self.notification.draw(screen)

    def on_bag_item_click(self, item_dict):
        from src.core.data_loader import DataLoader
        item_name = item_dict.get('name')
        full_data = DataLoader.instance().get_item_data(item_name)
        
        if full_data.get('usable_in_bag', False):
             Logger.info(f"Selected {item_name}. Click USE to confirm.")
             self.selected_item_for_use = item_dict
             self.selected_item_for_use = item_dict
             self.waiting_for_pokemon_selection = False # Reset this if they switch item
             
             if self.confirm_popup: # Close confirm if switching item
                 self.confirm_popup = None
             
             # Show Use Button (Reset to USE)
             if self.use_item_btn not in self.bag_popup.interactive_components:
                 self.bag_popup.interactive_components.append(self.use_item_btn)
             
             self.use_item_btn.text = "USE" # Reset text
             if self.use_item_btn.button_label:
                 self.use_item_btn.button_label.set_text("USE")
        else:
             Logger.info(f"{item_name} cannot be used here.")
             self.selected_item_for_use = None
             if self.use_item_btn in self.bag_popup.interactive_components:
                 self.bag_popup.interactive_components.remove(self.use_item_btn)

    def on_use_button_click(self):
        if self.selected_item_for_use:
            if not self.waiting_for_pokemon_selection:
                # START SELECTION
                Logger.info(f"Select a Pokemon to use {self.selected_item_for_use.get('name')} on.")
                self.waiting_for_pokemon_selection = True
                
                # Change Button to Cancel
                self.use_item_btn.text = "CANCEL"
                if self.use_item_btn.button_label:
                    self.use_item_btn.button_label.set_text("CANCEL")
            else:
                # CANCEL SELECTION
                self._cancel_selection()

    def _cancel_selection(self):
        self.waiting_for_pokemon_selection = False
        Logger.info("Selection cancelled.")
        
        # Reset Button to USE
        self.use_item_btn.text = "USE"
        if self.use_item_btn.button_label:
            self.use_item_btn.button_label.set_text("USE")
            
    def on_bag_monster_click(self, monster_dict):
        if self.waiting_for_pokemon_selection and self.selected_item_for_use:
             item_name = self.selected_item_for_use.get('name')
             # Apply Item Logic (Replicating BattleManager usage loosely)
             from src.core.data_loader import DataLoader
             full_data = DataLoader.instance().get_item_data(item_name)
             
             effect = full_data.get('effect')
             val = full_data.get('value', 0)
             
             success = False
             
             if effect == 'heal_hp':
                 max_hp = monster_dict.get('max_hp', 1)
                 current_hp = monster_dict.get('hp', 0)
                 
                 if current_hp >= max_hp:
                     Logger.info("HP is already full!")
                 else:
                     new_hp = min(max_hp, current_hp + val)
                     monster_dict['hp'] = new_hp
                     Logger.info(f"Used {item_name}! Recovered HP. ({current_hp} -> {new_hp})")
                     self.show_notification(f"Used [YELLOW]{item_name}[WHITE]!")
                     success = True
            
             elif effect == 'level_up':
                 current_level = monster_dict.get('level', 1)
                 new_level = current_level + int(val)
                 monster_dict['level'] = new_level
                 new_level = current_level + int(val)
                 monster_dict['level'] = new_level
                 Logger.info(f"{monster_dict['name']} leveled up to {new_level}!")
                 
                 # Recalculate Stats and Evolution Status
                 DataLoader.instance().hydrate_monster(monster_dict)
                 Logger.info(f"Stats updated. Can Evolve: {monster_dict.get('can_evolve')}")
                 
                 # Evolution Logic
                 species_data = DataLoader.instance().get_monster_species_data(monster_dict.get('name'))
                 evo_data = species_data.get('evolution')
                 if evo_data and new_level >= evo_data.get('level', 100):
                     # old_name = monster_dict.get('name')
                     # new_name = evo_data.get('to')
                     # monster_dict['name'] = new_name
                     
                     # Update sprite path if available?
                     # hydrate_monster usually sets 'menu_sprite_path' based on name
                     # So we just rely on hydrate logic
                     # Logger.info(f"What? {old_name} is evolving into {new_name}!")
                     Logger.info(f"{monster_dict['name']} is ready to evolve!")
                     monster_dict['can_evolve'] = True
                 
                 # Reframe stats (HP max, atk, etc)
                 DataLoader.instance().hydrate_monster(monster_dict)
                 
                 # Check Learnset
                 species_data = DataLoader.instance().get_monster_species_data(monster_dict.get('name'))
                 learnset = species_data.get('learnset', {})
                 lvl_str = str(monster_dict['level'])
                 
                 if lvl_str in learnset:
                     new_move = learnset[lvl_str]
                     current_moves = monster_dict.get('moves', [])
                     
                     if new_move not in current_moves:
                         Logger.info(f"{monster_dict['name']} is trying to learn {new_move}!")
                         if len(current_moves) < 4:
                             current_moves.append(new_move)
                             Logger.info(f"Learned {new_move}!")
                         else:
                             forgotten = current_moves[0]
                             current_moves[0] = new_move
                             Logger.info(f"Forgot {forgotten} and learned {new_move}!")
                         monster_dict['moves'] = current_moves
                 
                 success = True



             if success:
                 # CONSUME ITEM
                 self.game_manager.bag.remove_item(item_name)
                 
                 # RESET STATE
                 self.selected_item_for_use = None
                 self._cancel_selection() # Handles bool and button text
                 if self.use_item_btn in self.bag_popup.interactive_components:
                    self.bag_popup.interactive_components.remove(self.use_item_btn)
                 
                 # Force Save?
                 self.game_manager.auto_save()
        else:
             # Just clicking pokemon normally
             # Show options instead of just evolving
             self._show_monster_options(monster_dict)

    def _show_monster_options(self, monster_dict):
        self.target_monster_for_extraction = monster_dict
        
        # Add buttons if not present
        if self.extract_btn not in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.append(self.extract_btn)
        
        if self.cancel_opts_btn not in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.append(self.cancel_opts_btn)
            
        if monster_dict.get('can_evolve') and self.evolve_option_btn not in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.append(self.evolve_option_btn)
            
        # Hide Use button if present
        if self.use_item_btn in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.remove(self.use_item_btn)
            
    def _hide_monster_options(self):
        self.target_monster_for_extraction = None
        if self.extract_btn in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.remove(self.extract_btn)
        if self.cancel_opts_btn in self.bag_popup.interactive_components:
             self.bag_popup.interactive_components.remove(self.cancel_opts_btn)
        if self.evolve_option_btn in self.bag_popup.interactive_components:
             self.bag_popup.interactive_components.remove(self.evolve_option_btn)

    def _on_evolve_option_click(self):
        if self.target_monster_for_extraction:
            self._trigger_evolution_confirmation(self.target_monster_for_extraction)
        self._hide_monster_options()

    def _on_extract_click(self):
        if not hasattr(self, 'target_monster_for_extraction') or not self.target_monster_for_extraction:
            return
            
        mon = self.target_monster_for_extraction
        name = mon.get('name', 'Unknown')
        level = mon.get('level', 1)
        
        # Calculate Souls: Level // 10, rounded up or down randomly
        base_souls = level / 10.0
        import random
        import math
        
        if random.random() < (base_souls % 1):
            souls_gained = math.ceil(base_souls)
        else:
            souls_gained = math.floor(base_souls)
            
        souls_gained = max(1, int(souls_gained)) # Minimum 1? Or 0? User said "rounded up or down is random". 
        
        # Remove Monster
        if self.game_manager.bag.remove_monster(mon):
            self.game_manager.bag.add_item("Souls", souls_gained)
            Logger.info(f"Extracted {souls_gained} Souls from {name} (Lv.{level}).")
            
            self.show_notification(f"[CYAN]{name}[WHITE] have been sacrificed, obtained [YELLOW]{souls_gained} souls")
            
            # Refresh List
            self.monster_list.set_monsters(self.game_manager.bag.monsters)
        else:
            Logger.error("Failed to remove monster.")
            
        self._hide_monster_options()

    def open_shop_menu(self):
        self.toggle_overlay("shop")

    def _trigger_evolution_confirmation(self, monster_dict):
        """Opens a confirmation popup for evolution."""
        # Prevent double-trigger
        if self.current_overlay == "evolution":
            return

        Logger.info(f"Triggering evolution check for {monster_dict['name']}")
        
        self.evolution_candidate = monster_dict
        self.toggle_overlay("evolution")

    def _start_evolution(self, monster_dict):
        # self.confirm_popup = None (Handled by toggle overlay)
        self.evolving_monster = monster_dict
        self.is_evolving = True
        self.anim_timer = 0.0
        self.evo_flash_alpha = 0
        self.evo_flash_alpha = 0
        self.particles = []
        self._post_evo_hydrated = False # Reset flag
        
        Logger.info("Starting Evolution Animation...")
        
        # Load Sprites
        from src.core.services import resource_manager
        from src.core.data_loader import DataLoader
        
        # Load Star Particle
        if not self.star_image:
            self.star_image = resource_manager.get_image("ingame_ui/baricon4.png")
        
        # Helper to slice left half
        def load_left_half(path):
            full = resource_manager.get_image(path)
            w, h = full.get_size()
            # If width is conspicuously wide (sprite sheet), slice half
            # Standard sprite sheets here seem to be 2 frames (left/right or something)
            # User said: "use the left side of the sprites to be the main sprite"
            # BattleSprite logic does: w // 2.
            # Assuming all monster sprites follow this rules?
            # Safe check: if width > height * 1.5? Or just always slice if it looks like a sheet?
            # Let's assume standard format for now.
            left_half = full.subsurface(pg.Rect(0, 0, w // 2, h))
            return pg.transform.scale(left_half, (300, 300))

        # Current Sprite
        curr_path = monster_dict.get('battle_sprite_path', monster_dict.get('menu_sprite_path'))
        self.evolution_sprite_current = load_left_half(curr_path)
        
        # Next Sprite
        species_data = DataLoader.instance().get_monster_species_data(monster_dict.get('name'))
        evo_data = species_data.get('evolution', {})
        next_name = evo_data.get('to')
        
        next_species_data = DataLoader.instance().get_monster_species_data(next_name)
        next_path = next_species_data.get('battle_sprite_path', 'sprites/pokemon/Bulbasaur.png')
        
        self.evolution_sprite_next = load_left_half(next_path)
        
        # Close Bag
        self.toggle_overlay(None)

    def _update_evolution_animation(self, dt):
        self.anim_timer += dt
        
        # Phase 1: Wait (0 - 1.5s)
        if self.anim_timer < 2.0:
            pass 
            
        # Phase 2: Flash (2.0 - 4.0s)
        elif self.anim_timer < 4.0:
            # flash oscillating
            val = (self.anim_timer - 2.0) * 5 
            import math
            self.evo_flash_alpha = int(abs(math.sin(val)) * 255)
            
            # Swap at peak (white out) ?
            if self.anim_timer > 3.0 and self.evolution_sprite_current != self.evolution_sprite_next:
                self.evolution_sprite_current = self.evolution_sprite_next
                
                # EXPLOSION OF PARTICLES!
                if not self.particles:
                    import random
                    cx, cy = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2
                    for _ in range(20):
                        self.particles.append({
                            'x': cx, 'y': cy,
                            'vx': random.uniform(-200, 200),
                            'vy': random.uniform(-200, 200),
                            'life': 1.0
                        })
                
        # Phase 3: Done
        elif self.anim_timer > 5.5:
             self._finalize_evolution()
             
        # Update particles
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt

    def _update_offering_animation(self, dt):
        self.offering_timer += dt
        
        # Update particles
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
            
        # Finalize after 2 seconds
        if self.offering_timer >= 2.0:
            self.is_offering = False
            self.offering_timer = 0.0
            
            # Perform Healing
            if hasattr(self, 'monsters_to_heal'):
                for mon in self.monsters_to_heal:
                    mon['hp'] = mon.get('max_hp', mon.get('hp', 1))
                Logger.info(f"Healed {len(self.monsters_to_heal)} pokemon.")
                self.monsters_to_heal = []
            
            self.particles = []

    def draw_background_particles(self, screen: pg.Surface):
        """Draw particles BEHIND entities/hitboxes."""
        if self.is_offering:
            # Cyan square particles
            for p in self.particles:
                # Fully solid particles
                alpha = 255 
                if p['life'] > 0:
                    # Smaller particles (base size reduced to 5)
                    size = int(5 * (p['life'] / 2.0) + 3) 
                    s = pg.Surface((size, size))
                    s.set_alpha(alpha)
                    s.fill((0, 255, 255)) # Cyan
                    screen.blit(s, (p['x'], p['y']))

    def _update_snow_effect(self, dt: float):
        import random
        # Spawn new particles
        if len(self.snow_particles) < 100:
            for _ in range(2):
                self.snow_particles.append({
                    'x': random.uniform(0, GameSettings.SCREEN_WIDTH),
                    'y': -10,
                    'vx': random.uniform(-20, 20),
                    'vy': random.uniform(50, 150),
                    'size': random.uniform(2, 5),
                    'alpha': random.randint(100, 200)
                })
        
        # Update existing particles
        for p in self.snow_particles[:]:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            if p['y'] > GameSettings.SCREEN_HEIGHT:
                self.snow_particles.remove(p)

    def draw_snow_overlay(self, screen: pg.Surface):
        # 1. Light blue / white overlay tint
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        overlay.set_alpha(40) # Subtle tint
        overlay.fill((200, 230, 255)) # Light blue-ish white
        screen.blit(overlay, (0, 0))

        # 2. Falling translucent particles
        for p in self.snow_particles:
            snow_surf = pg.Surface((int(p['size']), int(p['size'])))
            snow_surf.set_alpha(p['alpha'])
            snow_surf.fill((255, 255, 255))
            screen.blit(snow_surf, (p['x'], p['y']))


    def _finalize_evolution(self):
        self.is_evolving = False
        from src.core.data_loader import DataLoader
        
        # Apply Evolution Logic
        monster_dict = self.evolving_monster
        species_data = DataLoader.instance().get_monster_species_data(monster_dict.get('name'))
        evo_data = species_data.get('evolution')
        
        if evo_data:
             old_name = monster_dict['name']
             new_name = evo_data.get('to')
             monster_dict['name'] = new_name
             monster_dict['can_evolve'] = False # consume flag
             
             DataLoader.instance().hydrate_monster(monster_dict)
             Logger.info(f"Evolution Complete: {old_name} -> {new_name}")
             
             self.scene.game_manager.auto_save()
             
             # Re-open Bag to show result?
             self.toggle_overlay("bag")
    def _init_offering_components(self):
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        # Reuse evolution popup style or generic popup
        self.offering_popup = Popup("UI/raw/UI_Flat_Frame02a.png", (400, 300), lambda: self.toggle_overlay(None))
        self.offering_popup.interactive_components = []
        
        # Center the popup frame
        self.offering_popup.frame_rect.center = (screen_size[0] // 2, screen_size[1] // 2)
        frame = self.offering_popup.frame_rect

        # Ok Button (Previously Heal)
        self.offering_heal_btn = Button("UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
                          frame.centerx - 110,
                          frame.top + 150,
                          100, 40, "Ok",
                          on_click=self._on_offering_heal_click)
        self.offering_popup.interactive_components.append(self.offering_heal_btn)

        # Cancel Button
        cancel_btn = Button("UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
                          frame.centerx + 10,
                          frame.top + 150,
                          100, 40, "Cancel",
                          on_click=lambda: self.toggle_overlay(None))
        self.offering_popup.interactive_components.append(cancel_btn)

        # Title Label
        title = Label("Offering Pillar", frame.centerx, frame.top + 40,
                      align="center", fontsize=24)
        self.offering_popup.interactive_components.append(title)

        # Dynamic Message Placeholder
        self.offering_cost_label = Label("consume 0", frame.centerx - 20, frame.top + 90,
                                        align="center", fontsize=20)
        self.offering_popup.interactive_components.append(self.offering_cost_label)

        # Soul Icon Placeholder
        self.offering_soul_icon = Icon("ingame_ui/poke_soul.png", frame.centerx + 40, frame.top + 78, (24, 24))
        self.offering_popup.interactive_components.append(self.offering_soul_icon)
        
    def open_offering_menu(self):
        # Calculate cost based on missing HP? (User didn't specify formula, let's use a fixed one for now or total HP)
        # Assuming cost = sum of missing HP // 10
        total_missing = 0
        for m in self.scene.game_manager.bag.monsters:
            total_missing += m.get('max_hp', 0) - m.get('hp', 0)
        
        cost = max(1, total_missing // 10) # Minimum 1 soul
        self.current_offering_cost = cost
        
        self.offering_cost_label.set_text(f"consume {cost}")
        
        # Adjust icon position based on text width
        text_width = self.offering_cost_label.rect.width
        center_x = self.offering_popup.frame_rect.centerx
        self.offering_cost_label.rect.centerx = center_x - 12 # Nudge text left to make room for icon
        self.offering_soul_icon.set_position(self.offering_cost_label.rect.right + 5, self.offering_cost_label.rect.top - 2)
        
        self.toggle_overlay("offering")
        
    def _on_offering_heal_click(self):
        # Use the cost calculated when the menu was opened
        cost = getattr(self, 'current_offering_cost', 0)
        
        if cost == 0:
             Logger.info("All pokemon are already healthy.")
             self.toggle_overlay(None)
             return

        souls = self.game_manager.bag.get_item("Souls")
        count = souls['count'] if souls else 0
        
        if count >= cost:
            self.game_manager.bag.remove_item("Souls", cost)
            
            # Start Animation
            self.is_offering = True
            self.offering_timer = 0.0
            # Identify damaged pokemon to heal
            party = self.game_manager.bag.monsters
            self.monsters_to_heal = [m for m in party if m.get('hp', 0) < m.get('max_hp', 1)]
            self.particles = []
            
            # Load Star Particle if not loaded
            if not self.star_image:
                from src.core.services import resource_manager
                self.star_image = resource_manager.get_image("ingame_ui/baricon4.png")
            
            # Spawn initial blooming particles
            import random
            cx, cy = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2
            for _ in range(15): # Fewer particles
                self.particles.append({
                    'x': cx, 'y': cy,
                    'vx': random.uniform(-100, 100), # Slower
                    'vy': random.uniform(-100, 100), # Slower
                    'life': 2.0 # Longer
                })
                
            Logger.info(f"Offering {cost} souls for healing...")
            self.show_notification("All pokemon healed")
            self.toggle_overlay(None)
        else:
            Logger.info(f"Not enough souls to heal party. Need {cost} (have {count}).")
            self.toggle_overlay(None)



    def show_map_title(self, message: str) -> None:
        """Shows a large map title notification."""
        self.notification.show_map_title(message)
