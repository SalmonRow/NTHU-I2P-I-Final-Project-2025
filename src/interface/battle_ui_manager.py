import pygame as pg
from typing import Callable, Optional, Dict
from src.utils import GameSettings, load_img, Logger
from src.interface.components import Button, Popup, Label, ItemListComponent, MonsterListComponent
from src.interface.components.battle_sprite import BattleSprite

#colors
GREEN = (0, 200, 0)
RED = (200, 0, 0)
GRAY = (130, 130, 130)
D_GRAY = (128, 139, 161)
DD_GRAY = (58, 69, 81)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
SCREEN_SIZE = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)


class BattleUIManager:
    """
    Manages all UI elements for the Battle Scene.
    Handle inputs for buttons and drawing for everything.
    """
    
    # UI Components
    player_mon_pan: Popup
    enem_mon_pan: Popup
    
    atk_button: Button
    run_button: Button
    catch_button: Button
    
    turn_label: Label
    result_label: Label
    prompt_label: Label
    
    # Sprites
    player_sprite: pg.Surface | BattleSprite | None = None
    enem_sprite: BattleSprite | None = None
    player_sprite_rect: pg.Rect | None = None
    enem_sprite_rect: pg.Rect | None = None

    # Constants
    ACTION_BUTTON_SIZE = 75
    HP_BAR_WIDTH = 200
    HP_BAR_HEIGHT = 20
    STATS_PAN_SIZE = (520, 130)
    MAX_MOVES = 4

    POP_OFFSET = (1.6, 1.7)
    ACTION_BUT_PAN = (800, 360)
    LOG_PAN = (600, 270)


    def __init__(self, scene, 
                 on_attack: Callable, 
                 on_run: Callable, 
                 on_catch: Callable,
                 on_move_click: Callable[[str], None] | None = None): 
        self.scene = scene
        self.on_move_click = on_move_click
        self.showing_attack_menu = False
        self.showing_bag_menu = False
        self.showing_item_menu = False
        self.showing_attack_menu = False
        self.showing_bag_menu = False
        self.showing_item_menu = False
        self.showing_pokemon_menu = False # New state
        self.bag_items_page = 0

        
        
        # Log Logic
        # List of lists. Each inner list represents one "Line" of text, containing multiple Label objects (chunks).
        self.log_lines: list[list[Label]] = [] 
        self.log_inner_rect_offset = (20, 38) # Relative to panel

        
        # --- Panels ---
        self.player_mon_pan = Popup("UI/raw/UI_Flat_Banner03a.png", self.STATS_PAN_SIZE, close_callback=None)
        self.enem_mon_pan = Popup("UI/raw/UI_Flat_Banner04b.png", self.STATS_PAN_SIZE, close_callback=None)
        self.player_mon_pan.interactive_components = []
        self.enem_mon_pan.interactive_components = []

            #Action buttons panel
        self.battle_bg_pan = Popup(
            "UI/raw/UI_Flat_Frame01a.png", size=self.ACTION_BUT_PAN, close_callback=None
            )
        self.moves_panel = Popup(
            "UI/raw/UI_Flat_Frame01a.png", size=self.ACTION_BUT_PAN, close_callback=None
        )
        self.action_log_screen = Popup(
            "UI/raw/UI_Flat_Frame01a.png", size=self.LOG_PAN, close_callback=None
        )
        
        # --- Bag Panels ---
        self.bag_menu_panel = Popup(
            "UI/raw/UI_Flat_Frame01a.png", size=SCREEN_SIZE, close_callback=None
        )
        self.item_menu_panel = Popup(
            "UI/raw/UI_Flat_Frame01a.png", size=SCREEN_SIZE, close_callback=None
        )
        self.pokemon_menu_panel = Popup(
             "UI/raw/UI_Flat_Frame01a.png", size=SCREEN_SIZE, close_callback=None
        )

        self.battle_bg_pan.interactive_components = []
        self.action_log_screen.interactive_components = []
        self.moves_panel.interactive_components = []
        
        # --- Buttons ---
        # ghost buttons
        n_image = load_img("UI/raw/UI_Flat_Button01a_2.png")
        ghost_img = n_image.copy()
        ghost_img.fill(GRAY, special_flags=pg.BLEND_RGB_MULT)

        # Initialize Buttons at (0,0) first, updated in _setup_button_layout
        self.atk_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            0, 0,
            self.ACTION_BUTTON_SIZE * 2.5, self.ACTION_BUTTON_SIZE ,
            text="ATTACK",
            on_click=self.open_attack_menu
        )

        self.bag_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            0, 0,
            self.ACTION_BUTTON_SIZE * 2.5, self.ACTION_BUTTON_SIZE,
            text="BAG",
            on_click=self.open_bag
        )

        self.run_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            0, 0,
            self.ACTION_BUTTON_SIZE * 2.5, self.ACTION_BUTTON_SIZE,
            text="RUN",
            on_click=on_run
        )

        self.catch_button = Button(
            "UI/raw/UI_Flat_Button01a_2.png", 'UI/raw/UI_Flat_Button01a_1.png',
            0, 0,
            self.ACTION_BUTTON_SIZE * 2.5, self.ACTION_BUTTON_SIZE,
            text="CATCH",
            on_click=on_catch
        )

        # Moves button in move panel
        self.move_buttons = []
        
        # Back Button
        self.back_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            0, 0, 40, 40,
            on_click=self.close_attack_menu
        )

        for _ in range(self.MAX_MOVES):
            btn = Button(
                "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
                0, 0,
                self.ACTION_BUTTON_SIZE * 2.5, self.ACTION_BUTTON_SIZE,
                text="---"
            )
            
            # --- Capture Surfaces for Ghost Logic (Movies) ---
            btn.normal_surface = btn.img_button_default.image.copy()
            btn.hover_surface  = btn.img_button_hover.image.copy()

            btn.ghost_surface = btn.normal_surface.copy()
            btn.ghost_surface.fill(GRAY, special_flags=pg.BLEND_RGB_MULT)
            
            self.move_buttons.append(btn)
            
        # 4. Add to Panel
        self.moves_panel.interactive_components = self.move_buttons + [self.back_button]


        # --- Bag Buttons ---
        self.btn_use_item = Button(
             "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
             SCREEN_SIZE[1], 0, 300, 80, 
             text="USE ITEM",
             on_click=self.open_item_menu
        )
        self.btn_change_mon = Button(
             "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
             0, 0, 300, 80,
             text="CHANGE MONSTER",
             on_click=self.on_change_monster_click
        )
        self.btn_bag_back = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            0, 0, 40, 40,
            on_click=self.close_bag
        )
        self.btn_item_back = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            0, 0, 40, 40,
            on_click=self.close_item_menu
        )
        self.btn_pokemon_back = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            0, 0, 40, 40,
            on_click=self.close_pokemon_menu
        )
        
        # --- NEW: Use ItemListComponent instead of manual buttons ---
        self.item_list_component = None # Will init in _setup_button_layout or here? 
        # Better in init but we need rect positions. 
        # Actually components need rects. 
        # We can init it with temp rect and position it later.
        self.item_list_component = ItemListComponent(
            0, 0, 700, 400, [], on_click=self.on_bag_item_click
        )

        self.bag_menu_panel.interactive_components = [self.btn_use_item, self.btn_change_mon, self.btn_bag_back]
        self.item_menu_panel.interactive_components = [self.item_list_component, self.btn_item_back]
        
        self.monster_list_component = MonsterListComponent(
             0, 0, 700, 400, [], on_click=self.on_pokemon_selected
        )
        self.pokemon_menu_panel.interactive_components = [self.monster_list_component, self.btn_pokemon_back]
            
        # -- adding buttons to panel
        self.battle_bg_pan.interactive_components = [
            self.atk_button, self.bag_button, 
            self.run_button, self.catch_button
        ]
            
        # --- Labels ---
        self.turn_label = Label(text="Turn: PLAYER", x=75, y=50, fontsize=30)
        self.result_label = Label(text="", x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT // 2, color=RED, align='center', fontsize=50)
        self.prompt_label = Label(text="Press SPACE to exit.", x=GameSettings.SCREEN_WIDTH // 2, y=GameSettings.SCREEN_HEIGHT - 50, color=WHITE, align='center', fontsize=20)
        self.action_panel_label = Label(text="ACTIONS", x=0, y=0, fontsize=24, align="center")

        # Dim overlay
        self.dim_overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.dim_overlay.set_alpha(128)
        self.dim_overlay.fill((0, 0, 0))

        # --- NEW: Set up the fixed layout once ---
        self._setup_button_layout()


    def _setup_button_layout(self):
        """
        Calculates and sets the permanent fixed positions for all UI components.
        This runs only once in __init__ to avoid redundant calculations in draw().
        """
        x = GameSettings.SCREEN_WIDTH
        y = GameSettings.SCREEN_HEIGHT
        
        # --- 1. Set Panel Positions First ---
        # Panel X/Y Calculation
        panel_x = x // 2 + (x // 2 - (self.ACTION_BUT_PAN[0] * 0.6 + 40))
        panel_y = y // 3 * self.POP_OFFSET[1] + 40
        
        self.battle_bg_pan.set_position(panel_x, panel_y)
        self.moves_panel.set_position(panel_x, panel_y)
        
        self.player_mon_pan.set_position(80, 300)
        self.enem_mon_pan.set_position(900, 50)
        self.action_log_screen.set_position(x - x + 40, y - y + 40)
        
        # --- Bag Panels Layout ---
        self.bag_menu_panel.frame_rect.center = (x // 2, y // 2)
        self.bag_menu_panel.set_position(self.bag_menu_panel.frame_rect.x, self.bag_menu_panel.frame_rect.y)
        
        self.item_menu_panel.frame_rect.center = (x // 2, y // 2)
        self.item_menu_panel.set_position(self.item_menu_panel.frame_rect.x, self.item_menu_panel.frame_rect.y)
        
        # Bag Menu Buttons
        bx, by = self.bag_menu_panel.frame_rect.centerx, self.bag_menu_panel.frame_rect.centery
        self.btn_use_item.hitbox.center = (bx, by - 50)
        self.btn_change_mon.hitbox.center = (bx, by + 50)
        self.btn_bag_back.hitbox.topright = (self.bag_menu_panel.frame_rect.right - 20, self.bag_menu_panel.frame_rect.top + 20)
        
        # Item Menu Buttons (Grid)
        ix = self.item_menu_panel.frame_rect.left + 50
        iy = self.item_menu_panel.frame_rect.top + 50
        self.btn_item_back.hitbox.topright = (self.item_menu_panel.frame_rect.right - 20, self.item_menu_panel.frame_rect.top + 20)
        
        # Position the List Component
        # Padding: 50 from left, 50 from top, 50 from bottom/right roughly
        lx = self.item_menu_panel.frame_rect.left + 50
        ly = self.item_menu_panel.frame_rect.top + 50
        lw = self.item_menu_panel.frame_rect.width - 100
        lh = self.item_menu_panel.frame_rect.height - 100
        
        self.item_list_component.rect = pg.Rect(lx, ly, lw, lh)
        
        # --- Pokemon Menu Layout ---
        self.pokemon_menu_panel.frame_rect.center = (x // 2, y // 2)
        self.pokemon_menu_panel.set_position(self.pokemon_menu_panel.frame_rect.x, self.pokemon_menu_panel.frame_rect.y)
        self.btn_pokemon_back.hitbox.topright = (self.pokemon_menu_panel.frame_rect.right - 20, self.pokemon_menu_panel.frame_rect.top + 20)
        
        # Use same dimensions as item list for consistency
        self.monster_list_component.rect = pg.Rect(lx, ly, lw, lh)

        # --- 2. Button Positions MUST depend on Panel Rects ---
        # Get the ACTUAL rect from the panel object
        bg_rect = self.battle_bg_pan.frame_rect
        
        # Layout Utils with padding
        # We start from the panel's Top-Left corner
        px = bg_rect.left
        py = bg_rect.top
        pw = bg_rect.width
        
        top_padding = 50 
        
        # Grid Coordinates relative to the panel
        col_1_x = px + 40
        col_2_x = px + pw // 2 + 10
        row_1_y = py + top_padding + 10
        row_2_y = py + top_padding + self.ACTION_BUTTON_SIZE + 20

        # 3. Main Action Buttons
        self.atk_button.hitbox.topleft = (col_1_x, row_1_y)
        self.bag_button.hitbox.topleft = (col_2_x, row_1_y)
        self.run_button.hitbox.topleft = (col_1_x, row_2_y)
        self.catch_button.hitbox.topleft = (col_2_x, row_2_y)

        # 4. Move Buttons (Use same grid layout)
        for i, btn in enumerate(self.move_buttons):
            r = i // 2
            c = i % 2
            bx = col_1_x if c == 0 else col_2_x
            by = row_1_y if r == 0 else row_2_y
            btn.hitbox.topleft = (bx, by)

        # 5. Back Button (Top Right of Panel)
        self.back_button.hitbox.topleft = (px + pw - 60, py + 15)
        
        # 6. Panel Label (Centered at top)
        self.action_panel_label.rect.centerx = bg_rect.centerx
        self.action_panel_label.rect.top = py + 15


    # --- Attack Menu Helpers ---
    def open_attack_menu(self):
        self.showing_attack_menu = True
        self.action_panel_label.set_text("ATTACKS")

    def close_attack_menu(self):
        self.showing_attack_menu = False
        self.action_panel_label.set_text("ACTIONS")

    def add_log_message(self, message: str):
        """
        Adds a new message to the log using Label objects.
        """
        raw_lines = message.split('\n')
        
        panel_rect = self.action_log_screen.frame_rect
        inner_rect_y = panel_rect.y + self.log_inner_rect_offset[1]
        inner_rect_h = self.LOG_PAN[1] * 0.50
        bottom_limit = inner_rect_y + inner_rect_h - 10 
        top_limit = inner_rect_y
        
        base_x = panel_rect.x + self.log_inner_rect_offset[0] + 15
        line_height = 30
        
        new_lines_of_labels = []

        for line in raw_lines:
            parsed_chunks = self._parse_colored_text(line)
            
            # Create a list of Labels for this line
            line_labels = []
            current_x = base_x
            
            for text, color in parsed_chunks:
                # Create Label
                # We use the Label class to handle font and rendering
                lbl = Label(text, current_x, bottom_limit, color=color, fontsize=22, fontfam=1)
                
                # Advance X for next chunk
                # We need the width. Label calculates it in __init__ -> _render_text -> self.rect
                current_x += lbl.rect.width
                
                line_labels.append(lbl)
                
            new_lines_of_labels.append(line_labels)

        # 2. Shift existing lines UP
        shift_amount = len(new_lines_of_labels) * line_height
        
        for line_list in self.log_lines:
            for lbl in line_list:
                lbl.rect.y -= shift_amount
            
        # 3. Add new lines
        self.log_lines.extend(new_lines_of_labels)
        
        # 4. Prune invisible lines
        # Check the Y of the first label in the line (assuming all on same Y)
        self.log_lines = [
            line for line in self.log_lines 
            if line and line[0].rect.y > top_limit - line_height
        ]
        
        # Force strict positioning from bottom up to avoid drift
        current_y = bottom_limit - line_height
        for i in range(len(self.log_lines) - 1, -1, -1):
            line = self.log_lines[i]
            for lbl in line:
                lbl.rect.y = current_y
            current_y -= line_height

    def _parse_colored_text(self, text: str) -> list:
        """
        Parses string like "[CYAN]Name [WHITE]used [YELLOW]Move" into 
        [('Name', CYAN), (' used ', WHITE), ('Move', YELLOW)]
        """
        chunks = []

        current_color = WHITE
        
        parts = text.split('[')
        
        for i, part in enumerate(parts):
            if i == 0 and not text.startswith('['):
                if part:
                    chunks.append((part, current_color))
                continue
                
            if ']' in part:
                tag_content, content = part.split(']', 1)
                
                # Determine color
                if tag_content == "CYAN": current_color = CYAN
                elif tag_content == "YELLOW": current_color = YELLOW
                elif tag_content == "RED": current_color = RED
                elif tag_content == "WHITE": current_color = WHITE
                elif tag_content == "GREEN": current_color = GREEN
                
                if content:
                    chunks.append((content, current_color))
            else:
                # Malformed or just text, append with current color
                if part:
                    # It was split by [, so add it back if it wasnt a tag? 
                    # Simplicity: just treat as text
                     chunks.append(("[" + part, current_color))
                     
        return chunks


    # --- Bag stuff ----
    def open_bag(self):
        self.showing_bag_menu = True
        
    def close_bag(self):
        self.showing_bag_menu = False
        
    def open_item_menu(self):
        self.showing_item_menu = True
        
    def close_item_menu(self):
        self.showing_item_menu = False
        
    def on_change_monster_click(self):
        # Open the menu
        self.open_pokemon_menu(force_selection=False)
        
    def open_pokemon_menu(self, force_selection=False):
        self.showing_pokemon_menu = True
        self._update_pokemon_list()
        
        # Hide back button if forced
        if force_selection:
             if self.btn_pokemon_back in self.pokemon_menu_panel.interactive_components:
                 self.pokemon_menu_panel.interactive_components.remove(self.btn_pokemon_back)
        else:
             if self.btn_pokemon_back not in self.pokemon_menu_panel.interactive_components:
                 self.pokemon_menu_panel.interactive_components.append(self.btn_pokemon_back)

    def close_pokemon_menu(self):
        # Prevent closing if forced? Done by removing the button.
        self.showing_pokemon_menu = False
        
    def _update_pokemon_list(self):
         monsters = self.scene.game_manager.bag.monsters
         self.monster_list_component.monsters = monsters

    def on_pokemon_selected(self, monster):
        # Check if monster is valid (hp > 0)
        if monster['hp'] <= 0:
            self.add_log_message("That Pokemon has fainted!")
            return
            
        if monster == self.scene.battle_manager.player_mon:
             self.add_log_message("That Pokemon is already out!")
             return
             
        # Perform Switch
        success = self.scene.battle_manager.switch_pokemon(monster)
        if success:
             self.scene.queue_message(f"Go! [GREEN]{monster['name']}[WHITE]!")
             self.close_pokemon_menu()
             self.close_bag()
             
             # Reload sprites just in case
             self.load_sprites(self.scene.battle_manager.player_mon, self.scene.battle_manager.enemy_mon)
        
    def on_bag_item_click(self, item_dict):
        if not self.scene.battle_manager:
            return
            
        item_name = item_dict.get('name')

        # 1. Get full data
        from src.core.data_loader import DataLoader
        full_data = DataLoader.instance().get_item_data(item_name)
        
        if not full_data:
            self.add_log_message("Effect unknown.")
            return

        # 2. Add Name (it might be missing in json key-value pair if we just have the dict)
        full_data['name'] = item_name
            
        # 3. Use Item
        success = self.scene.battle_manager.use_item(full_data)
        
        if success:
             # Consume item
             self.scene.game_manager.bag.remove_item(item_name)
             self.scene.queue_message(f"Player used [YELLOW]{item_name}[WHITE]!")
             
             # Close menus
             self.close_item_menu()
             self.close_bag()
             
             # Auto Save?
             self.scene.game_manager.auto_save()
        else:
             self.add_log_message("It won't have any effect.")

    def _update_item_buttons_state(self):
        """
        Syncs item buttons with actual bag inventory.
        Filters for items with type='effect_item'.
        """
        bag = self.scene.game_manager.bag
        from src.core.data_loader import DataLoader
        dl = DataLoader.instance()

        # Filter items: count > 0 AND type == 'effect_item'
        display_items = []
        for i in bag._items_data:
            if i.get('count', 0) <= 0:
                continue
            
            full_data = dl.get_item_data(i.get('name'))
            if full_data.get('type') == 'effect_item':
                # Use dict directly as ItemListComponent expects dicts (legacy compatibility)
                display_items.append(i)
        
        # Update the component's list
        if self.item_list_component:
            self.item_list_component.items = display_items

    def load_sprites(self, player_mon: Dict, enem_mon: Dict):
        try:
            # PLAYER: Old Static Logic
            player_full = load_img(player_mon.get("battle_sprite_path", "sprites/pokemon/Bulbasaur.png"))
            P_SCALE = 5
            w1, h1 = player_full.get_size()
            # Right Half
            self.player_sprite = player_full.subsurface(pg.Rect(w1 // 2, 0, w1 // 2, h1))
            pw, ph = int(self.player_sprite.get_width() * P_SCALE), int(self.player_sprite.get_height() * P_SCALE)
            self.player_sprite = pg.transform.scale(self.player_sprite, (pw, ph))
            
            self.player_sprite_rect = self.player_sprite.get_rect()
            self.player_sprite_rect.bottomleft = (5, GameSettings.SCREEN_HEIGHT)

            # ENEMY: New Animated Logic
            e_path = enem_mon.get("battle_sprite_path", "sprites/pokemon/Bulbasaur.png")
            self.enem_sprite = BattleSprite(e_path, is_player=False)
            self.enem_sprite_rect = self.enem_sprite.rect
            
        except Exception as e:
            Logger.error(f"Failed to load sprites in UI Manager: {e}")

    def update(self, dt: float, current_turn: str, is_wild: bool, battle_ended: bool):
        self.turn_label.set_text(f"Turn: {current_turn.upper()}")
        
        # Handle Popups always if open (to allowing closing even if turn ends?)
        # Strictly speaking, bag should only be open during Player turn.
        
        if self.showing_item_menu:
            self._update_item_buttons_state()
            self.item_menu_panel.update(dt)
            return # Block other inputs
        
        if self.showing_pokemon_menu:
            self.pokemon_menu_panel.update(dt)
            return
            
        if self.showing_bag_menu:
            self.bag_menu_panel.update(dt)
            return # Block other inputs
        
        if not battle_ended and current_turn == 'player':
            
            if self.showing_attack_menu:
                self.moves_panel.update(dt)
            else:
                self.battle_bg_pan.update(dt)
            
            # Dynamic text for special button
            if not self.showing_attack_menu:
                if is_wild:
                    self.catch_button.text = "CATCH"
                    if self.catch_button.button_label:
                        self.catch_button.button_label.set_text("CATCH")
                else:
                    self.catch_button.text = "TALK"
                    if self.catch_button.button_label:
                        self.catch_button.button_label.set_text("TALK")

        # Update Animations
        # if self.player_sprite:
        #    self.player_sprite.update(dt)
        if self.enem_sprite:
            self.enem_sprite.update(dt)

    def draw(self, screen: pg.Surface, player_mon: Dict, enem_mon: Dict, 
             current_turn: str, is_wild: bool, battle_ended: bool, result_text: str | None):
        
        # utils
        x = GameSettings.SCREEN_WIDTH
        y = GameSettings.SCREEN_HEIGHT
        
        # 1. Labels
        self.turn_label.draw(screen)

        # 2. Action Panel (Buttons) - ONLY if Player Turn and Battle NOT ended
        if not battle_ended and current_turn == 'player':
            
            if self.showing_attack_menu:
                # --- DRAW ATTACK MENU ---
                # Panel position is already set in _setup_button_layout
                
                # Update Move Buttons Logic (Ghost/Active)
                current_moves = player_mon.get('moves', [])
                
                for i, btn in enumerate(self.move_buttons):
                    # Button position is already set in _setup_button_layout
                    
                    if i < len(current_moves):
                        # --- ACTIVE MOVE ---
                        # Restore original colored surfaces
                        btn.img_button_default.image = btn.normal_surface
                        btn.img_button_hover.image   = btn.hover_surface
                        
                        move_name = current_moves[i]
                        btn.text = move_name
                        
                        if btn.button_label:
                            btn.button_label.set_text(move_name)
                            btn.button_label.rect.center = btn.hitbox.center
                        
                        # Set Callback
                        if self.on_move_click:
                            btn.on_click = lambda m=move_name: self.on_move_click(m)
                    else:
                        # --- EMPTY SLOT (GHOST) ---
                        # Swap to gray surface for both states
                        btn.img_button_default.image = btn.ghost_surface
                        btn.img_button_hover.image   = btn.ghost_surface
                        
                        btn.text = "---"
                        if btn.button_label:
                            btn.button_label.set_text("---")
                            btn.button_label.rect.center = btn.hitbox.center
                            
                        btn.on_click = None # Disable click

                self.moves_panel.draw(screen)

            else:
                # Panel position is already set in _setup_button_layout
            
                # Sync labels (positions were set in _setup_button_layout)
                for btn in [self.atk_button, self.bag_button, self.run_button, self.catch_button]:
                    if btn.button_label:
                        btn.button_label.rect.center = btn.hitbox.center

                # Draw Panel (background and buttons)
                self.battle_bg_pan.draw(screen)
            
            # Draw Panel Label (position set in _setup_button_layout)
            self.action_panel_label.draw(screen)

        # 3. Log Screen
        # Position is set in _setup_button_layout
        self.action_log_screen.draw(screen)
        
        # Log Inner Borders
        log_pan_rect = self.action_log_screen.frame_rect
        inner_rect = pg.Rect(log_pan_rect.x + 20, log_pan_rect.y + 38, self.LOG_PAN[0]*0.60 - 43, self.LOG_PAN[1]*0.50)
        pg.draw.rect(screen, DD_GRAY, inner_rect)
        pg.draw.rect(screen, D_GRAY, inner_rect, 2)
        
        # Draw Log Text (Label based)
        panel_rect = self.action_log_screen.frame_rect
        min_y = panel_rect.y + self.log_inner_rect_offset[1]
        max_y = min_y + (self.LOG_PAN[1] * 0.50)

        for line in self.log_lines:
            # Check visibility of line (based on first chunk)
            if not line: continue
            y = line[0].rect.y
            
            if y < min_y - 10 or y > max_y:
                continue
                
            for lbl in line:
                lbl.draw(screen)



        # 4. Pokemon Status Panels (HP)
        # Positions are set in _setup_button_layout
        self.player_mon_pan.draw(screen)
        self.enem_mon_pan.draw(screen)

        # 5. Sprites
        if self.player_sprite:
             # Player is a Surface (Static)
             screen.blit(self.player_sprite, self.player_sprite_rect)
             
        if self.enem_sprite:
            # Enemy is a BattleSprite (Animated)
            self.enem_sprite.draw(screen)

        # 6. HP Bars
        player_panel = self.player_mon_pan.frame_rect
        hpx = player_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        hpy = player_panel.centery - (self.HP_BAR_HEIGHT // 2)
        self._draw_hp_bar(screen, hpx, hpy, player_mon.get('hp', 0), player_mon.get('max_hp', 100), player_mon.get('name', '???'))

        enem_panel = self.enem_mon_pan.frame_rect
        en_hpx = enem_panel.centerx - (self.HP_BAR_WIDTH // 2) + 40
        en_hpy = enem_panel.centery - (self.HP_BAR_HEIGHT // 2)
        self._draw_hp_bar(screen, en_hpx, en_hpy, enem_mon.get('hp', 0), enem_mon.get('max_hp', 100), enem_mon.get('name', '???'))

        # --- Draw Bag Overlays (on top of everything) ---
        if self.showing_bag_menu:
            # Sync labels for bag buttons
            for btn in self.bag_menu_panel.interactive_components:
                if isinstance(btn, Button) and btn.button_label:
                    btn.button_label.rect.center = btn.hitbox.center
            
            # Dim background
            screen.blit(self.dim_overlay, (0,0))
            self.bag_menu_panel.draw(screen)
            
        if self.showing_item_menu:
             # Draw Item Menu on top of Bag Menu
             self.item_menu_panel.draw(screen)

        if self.showing_pokemon_menu:
             self.pokemon_menu_panel.draw(screen)

        # Draw Result Overlay
        if battle_ended and result_text:
            screen.blit(self.dim_overlay, (0, 0)) # Dim the screen
            self.result_label.set_text(f"{result_text.upper()}!")
            self.result_label.draw(screen)
            self.prompt_label.draw(screen)
        self.turn_label.draw(screen)

    def _draw_hp_bar(self, screen: pg.Surface, x: int, y: int, current_hp: int, max_hp: int, name: str):
        hp_ratio = current_hp / max_hp if max_hp > 0 else 0
        cur_bar_wid = int(self.HP_BAR_WIDTH * hp_ratio)
        
        # Determine Color
        if hp_ratio > 0.5:
            color = GREEN
        elif hp_ratio > 0.25:
            color = (225, 225, 0) # YELLOW
        elif hp_ratio > 0.10:
            color = RED
        else:
            color = (139, 0, 0) # DARK RED

        pg.draw.rect(screen, GRAY, (x, y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, color, (x, y, cur_bar_wid, self.HP_BAR_HEIGHT))
        pg.draw.rect(screen, WHITE, (x, y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT), 2)

        name_lbl = Label(name, x, y - 5, align="midbottom", fontsize=16)
        hp_lbl = Label(f"{current_hp}/{max_hp}", x + self.HP_BAR_WIDTH // 2, y + self.HP_BAR_HEIGHT // 2, align="center", fontsize=18)
        
        name_lbl.draw(screen)
        hp_lbl.draw(screen)
