import random
from src.utils import Logger
from src.core.data_loader import DataLoader

class ShopManager:
    REFRESH_INTERVAL = 300  # 5 minutes in seconds
    MAX_MANUAL_REFRESHES = 3

    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.last_refresh_time = 0.0
        self.time_accumulator = 0.0
        self.manual_refresh_count = 0
        self.current_stock = []
        
        # Initial Stock Generation
        self.refresh_stock()

    def update(self, dt: float):
        self.time_accumulator += dt
        if self.time_accumulator >= self.REFRESH_INTERVAL:
            self.auto_refresh()

    def auto_refresh(self):
        Logger.info("Shop Auto-Refine triggered.")
        self.refresh_stock()
        self.manual_refresh_count = 0
        self.time_accumulator = 0.0

    def try_manual_refresh(self) -> bool:
        if self.manual_refresh_count >= self.MAX_MANUAL_REFRESHES:
            Logger.info("Shop: Max manual refreshes reached.")
            return False
        
        self.manual_refresh_count += 1
        self.refresh_stock()
        Logger.info(f"Shop manually refreshed ({self.manual_refresh_count}/{self.MAX_MANUAL_REFRESHES})")
        return True

    def refresh_stock(self):
        """Generates new random stock with dynamic pricing."""
        self.current_stock = []
        dl = DataLoader.instance()
        all_items = dl.items
        
        # Filter out "Coins" and maybe other key items if we had tagging
        possible_items = [name for name, data in all_items.items() if data.get('type') != 'currency']
        
        # Select random subset (e.g., 3-6 items)
        num_items = random.randint(3, 6)
        selected_names = random.sample(possible_items, min(num_items, len(possible_items)))
        
        for name in selected_names:
            base_cost = all_items[name].get('base_cost', 10) # Default 10 if missing
            
            # Inflation/Randomness: 0.9 to 1.1 multiplier
            multiplier = random.uniform(0.9, 1.1)
            final_price = int(base_cost * multiplier)
            
            # Stock Quantity (e.g., 1-5)
            quantity = random.randint(1, 5)
            
            item_entry = {
                "name": name,
                "price": final_price,
                "quantity": quantity,
                "sprite_path": all_items[name].get('sprite_path')
            }
            self.current_stock.append(item_entry)
            
        Logger.info("Shop stock refreshed.")

    def buy_item(self, index: int) -> bool:
        if 0 <= index < len(self.current_stock):
            item_entry = self.current_stock[index]
            price = item_entry['price']
            quantity = item_entry['quantity']
            
            if quantity <= 0:
                Logger.info("Shop: Item sold out.")
                return False
                
            # Check Funds
            bag = self.game_manager.bag
            if not bag.has_item("Coins") or bag.get_item("Coins")['count'] < price:
                Logger.info("Shop: Insufficient funds.")
                from src.interface.components.label import Label # Optional: trigger UI feedback
                return False
                
            # Transaction
            bag.remove_item("Coins", price)
            bag.add_item(item_entry['name'], 1)
            item_entry['quantity'] -= 1
            
            Logger.info(f"Bought {item_entry['name']} for {price} coins.")
            return True
        return False

    def sell_item(self, item_name: str) -> bool:
        bag = self.game_manager.bag
        if not bag.has_item(item_name):
            return False
            
        dl = DataLoader.instance()
        item_data = dl.get_item_data(item_name)
        base_cost = item_data.get('base_cost', 10)
        
        # Sell Price = Base Cost / 2 (Simple economy)
        sell_price = max(1, base_cost // 2)
        
        bag.remove_item(item_name, 1)
        bag.add_item("Coins", sell_price)
        
        Logger.info(f"Sold {item_name} for {sell_price} coins.")
        return True

    def get_time_until_refresh(self):
        remaining = max(0, self.REFRESH_INTERVAL - self.time_accumulator)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return f"{minutes:02}:{seconds:02}"
