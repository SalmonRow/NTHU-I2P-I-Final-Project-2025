import pygame as pg
from typing import List, Any
from src.interface.components.popup import Popup
from src.interface.components.button import Button
from src.interface.components.label import Label
from src.interface.components.item import ItemListComponent
from src.utils import GameSettings, Logger
from src.core.data_loader import DataLoader

class ShopListComponent(ItemListComponent):
    """Extended ItemList to display Price and Quantity for Shop Items."""
    def draw(self, screen: pg.Surface):
        SPRITE_OFFSET_x = 5
        TEXT_OFFSET_X = self.SPRITE_SIZE + SPRITE_OFFSET_x + 5
        
        y_pos = self.rect.top + 5 + self.scroll_offset

        for i, item in enumerate(self.items):
            if y_pos > self.rect.bottom:
                break
                
            # Draw Selection/Hover Background
            if i == self.hovered_index:
                highlight_rect = pg.Rect(self.rect.left, y_pos, self.rect.width, self.line_height)
                pg.draw.rect(screen, self.HOVER_BORDER_COLOR, highlight_rect, self.HOVER_Border_WIDTH)

            # Sprite
            sprite_path = item.get('sprite_path', 'items/unknown.png') # Fallback?
            sprite = self._get_item_sprites(sprite_path)
            sprite_x = self.rect.left + SPRITE_OFFSET_x
            sprite_y = y_pos + (self.line_height - sprite.get_height()) // 2
            screen.blit(sprite, (sprite_x, sprite_y))

            # Name
            name_label = Label(
                item['name'], 
                x=self.rect.left + TEXT_OFFSET_X,
                y=y_pos + (self.line_height // 2) - 10 
            )
            name_label.draw(screen)

            # Price & Quantity
            # If item has 'price', it's a shop item.
            if 'price' in item:
                info_text = f"${item['price']} | x{item['quantity']}"
                if item['quantity'] == 0:
                    info_text = "SOLD OUT"
            else:
                # Bag item (selling)
                # Estimate sell price
                dl = DataLoader.instance()
                data = dl.get_item_data(item['name'])
                base = data.get('base_cost', 10)
                val = max(1, base // 2)
                info_text = f"x{item.get('count', 0)} | Sell: ${val}"

            info_label = Label(
                info_text,
                x=self.rect.right - 150, # Rough positioning
                y=y_pos + (self.line_height // 2) - 10,
                fontsize=20
            )
            info_label.draw(screen)

            y_pos += self.line_height

class ShopUI:
    def __init__(self, game_ui_manager):
        self.manager = game_ui_manager
        self.game_manager = game_ui_manager.game_manager
        self.shop_manager = self.game_manager.shop_manager
        
        self.popup = Popup("UI/raw/UI_Flat_Frame01a.png", (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), self.close)
        
        # State
        self.mode = "buy" # buy or sell
        
        # Components
        self._init_components()
        
    def _init_components(self):
        screen_w, screen_h = GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT
        frame = self.popup.frame_rect
        
        # Title
        self.title_label = Label("SHOP", frame.centerx - 50, frame.top + 40, fontsize=40, color=(19, 53, 133))
        self.popup.interactive_components.append(self.title_label)
        
        # Timer Label
        self.timer_label = Label("Refresh: 00:00", frame.right - 200, frame.top + 50, fontsize=20, color=(50, 50, 50))
        self.popup.interactive_components.append(self.timer_label)

        # Tabs
        self.btn_buy = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            frame.left + 50, frame.top + 100, 150, 50, text="BUY",
            on_click=lambda: self.set_mode("buy")
        )
        self.btn_sell = Button(
            "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
            frame.left + 220, frame.top + 100, 150, 50, text="SELL",
            on_click=lambda: self.set_mode("sell")
        )
        self.popup.interactive_components.extend([self.btn_buy, self.btn_sell])
        
        # Lists
        self.buy_list = ShopListComponent(
            frame.left + 50, frame.top + 170, frame.width - 100, frame.height - 250,
            [], on_click=self.on_buy_click
        )
        self.sell_list = ShopListComponent(
            frame.left + 50, frame.top + 170, frame.width - 100, frame.height - 250,
            [], on_click=self.on_sell_click
        )
        # We don't add lists to interactive_components directly? 
        # Popup calls update/draw on interactive_components, but ItemListComponent has its own update/draw signature?
        # Popup.draw calls component.draw(screen). ItemListComponent.draw(screen) matches.
        # Popup.update calls component.update(dt). ItemListComponent.update(dt) matches.
        # So yes, we can add them. But we only add the *active* one.
        
        self.update_list_visibility()
        
        # Footer
        self.coins_label = Label("Coins: 0", frame.left + 50, frame.bottom - 60, fontsize=30, color=(255, 215, 0))
        self.popup.interactive_components.append(self.coins_label)
        
        self.refresh_btn = Button(
             "UI/raw/UI_Flat_Button01a_2.png", "UI/raw/UI_Flat_Button01a_1.png",
             frame.right - 200, frame.bottom - 70, 150, 50, text="Refresh",
             on_click=self.on_refresh_click
        )
        self.popup.interactive_components.append(self.refresh_btn)

    def set_mode(self, mode):
        self.mode = mode
        self.update_list_visibility()
    
    def update_list_visibility(self):
        # Remove both first
        if self.buy_list in self.popup.interactive_components:
            self.popup.interactive_components.remove(self.buy_list)
        if self.sell_list in self.popup.interactive_components:
            self.popup.interactive_components.remove(self.sell_list)
            
        if self.mode == "buy":
            # Refresh buy list data
            self.buy_list.items = self.shop_manager.current_stock
            self.popup.interactive_components.append(self.buy_list)
        else:
            # Refresh sell list data (filter out coins/key items?)
            # For now show everything from bag
            self.sell_list.items = self.game_manager.bag._items_data
            self.popup.interactive_components.append(self.sell_list)

    def update(self, dt):
        # Specific updates
        self.timer_label.set_text(f"Refresh: {self.shop_manager.get_time_until_refresh()}")
        
        current_coins = 0
        coin_item = self.game_manager.bag.get_item("Coins")
        if coin_item:
            current_coins = coin_item.get('count', 0)
        self.coins_label.set_text(f"Coins: {current_coins}")
        
        refresh_left = self.shop_manager.MAX_MANUAL_REFRESHES - self.shop_manager.manual_refresh_count
        self.refresh_btn.text = f"Refresh ({refresh_left})"
        if self.refresh_btn.button_label:
             self.refresh_btn.button_label.set_text(f"Refresh ({refresh_left})")
        
        # Update popup (which updates components)
        self.popup.update(dt)

    def draw(self, screen):
        self.popup.draw(screen)

    def close(self):
        self.manager.toggle_overlay(None)

    def on_buy_click(self, item):
        # Find index in stock
        # List items refer to the same objects in shop_manager.current_stock
        try:
            index = self.shop_manager.current_stock.index(item)
            success = self.shop_manager.buy_item(index)
            if success:
                # Sound?
                pass
        except ValueError:
            pass

    def on_sell_click(self, item):
        success = self.shop_manager.sell_item(item['name'])
        if success:
            pass
            
    def on_refresh_click(self):
        if self.shop_manager.try_manual_refresh():
            self.update_list_visibility() # Refresh list 

