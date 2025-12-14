import pygame as pg
from src.utils import Logger, GameSettings
from src.core.services import sound_manager
from src.utils import Logger, GameSettings
from src.core.services import sound_manager, input_manager
from src.interface.components import Button, Popup, Checkbox, Slider, MonsterListComponent, ItemListComponent, Label
from src.core import GameManager
from src.core.services import scene_manager

class GameSceneUIManager:
    def __init__(self, game_scene):
        self.scene = game_scene
        self.game_manager: GameManager = game_scene.game_manager
        
        self.current_overlay = None
        self._last_volume = 0.5
        
        # State for item usage
        self.selected_item_for_use: dict | None = None
        self.waiting_for_pokemon_selection: bool = False

        # UI Components
        self.setting_popup: Popup = None
        self.bag_popup: Popup = None
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

        # Initialize everything
        self._init_popups()
        self._init_overlay_buttons()
        self._init_setting_components()
        self._init_bag_components()

    def _init_popups(self) -> None:
        """Create setting and bag popup windows."""
        screen_size = (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        close_callback = lambda: self.toggle_overlay(self.current_overlay)
        
        #popups for when pushing buttons
        self.setting_popup = Popup('UI/raw/UI_Flat_Frame03a.png', screen_size, close_callback)
        self.bag_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)
        self.nav_popup = Popup("UI/raw/UI_Flat_Frame02a.png", screen_size, close_callback)

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
            on_click=lambda : self.toggle_overlay("nav")
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

    def toggle_overlay(self, overlay_name) -> None:
        # Always reset selection state when toggling overlays
        self.selected_item_for_use = None
        self.waiting_for_pokemon_selection = False
        if self.use_item_btn in self.bag_popup.interactive_components:
            self.bag_popup.interactive_components.remove(self.use_item_btn)
            
        if overlay_name is None:
            self.current_overlay = None
        elif self.current_overlay == overlay_name:
            self.current_overlay = None
        else:
            self.current_overlay = overlay_name
            # If opening bag, sort items
            if self.current_overlay == "bag":
                if self.game_manager and self.game_manager.bag:
                    self.game_manager.bag.sort_items()

    def toggle_mute(self, is_muted: bool) -> None:
        if is_muted:
            self._last_volume = sound_manager.get_volume()
            sound_manager.set_volume(0.0) 
        else:
            restore_volume = getattr(self, '_last_volume', 0.5)
            sound_manager.set_volume(restore_volume)

    def update(self, dt: float) -> None:
        # Update overlay buttons
        self.setting_button.update(dt) 
        self.bag_button.update(dt) 
        self.nav_button.update(dt)
        
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

        # Check for ESC to Cancel Selection
        if self.waiting_for_pokemon_selection:
            if input_manager.key_pressed(pg.K_ESCAPE):
                self._cancel_selection()

    def draw(self, screen: pg.Surface) -> None:
        # Draw overlay background if active
        if self.current_overlay is not None:
            darken = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
            )
            darken.set_alpha(128)
            darken.fill((0,0,0))
            screen.blit(darken, (0, 0))  

            if self.current_overlay == "setting":
                self.setting_popup.draw(screen)
            if self.current_overlay == "bag":
                self.bag_popup.draw(screen)
            if self.current_overlay == "nav":
                self.nav_popup.draw(screen)

        # Draw buttons
        self.setting_button.draw(screen)
        self.bag_button.draw(screen)
        self.nav_button.draw(screen)

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

    def on_bag_item_click(self, item_dict):
        from src.core.data_loader import DataLoader
        item_name = item_dict.get('name')
        full_data = DataLoader.instance().get_item_data(item_name)
        
        if full_data.get('usable_in_bag', False):
             Logger.info(f"Selected {item_name}. Click USE to confirm.")
             self.selected_item_for_use = item_dict
             self.waiting_for_pokemon_selection = False # Reset this if they switch item
             
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
                     success = True
            
             elif effect == 'level_up':
                 current_level = monster_dict.get('level', 1)
                 new_level = current_level + int(val)
                 monster_dict['level'] = new_level
                 Logger.info(f"{monster_dict['name']} leveled up to {new_level}!")
                 
                 # Evolution Logic
                 species_data = DataLoader.instance().get_monster_species_data(monster_dict.get('name'))
                 evo_data = species_data.get('evolution')
                 if evo_data and new_level >= evo_data.get('level', 100):
                     old_name = monster_dict.get('name')
                     new_name = evo_data.get('to')
                     monster_dict['name'] = new_name
                     
                     # Update sprite path if available?
                     # hydrate_monster usually sets 'menu_sprite_path' based on name
                     # So we just rely on hydrate logic
                     Logger.info(f"What? {old_name} is evolving into {new_name}!")
                 
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
             # Just clicking pokemon normally (show stats? irrelevant for now)
             pass