from src.utils import GameSettings
from src.interface.components.label import Label
import pygame as pg

class Notification:
    def __init__(self):
        self.message = ""
        self.duration = 2.0
        self.timer = 0.0
        self.alpha = 255
        self.surface = None
        self.rect = None
        self.mode = "standard" # standard, map_title
        self.fade_in_duration = 0.0
        self.max_duration = 0.0
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.YELLOW = (255, 255, 0)
        self.CYAN = (0, 255, 255)
        self.GREY = (100, 100, 100)
        self.BLACK = (0, 0, 0)

        self.notification_type = "generic"

    def show(self, message: str, duration: float = 2.0, notification_type: str = "generic"):
        # Optimization: If message is same and still active, just keep it alive
        if self.mode == "standard" and self.message == message and self.surface:
            self.timer = duration
            self.max_duration = duration
            self.alpha = 255
            self.notification_type = notification_type
            return

        self.mode = "standard"
        self.message = message
        self.max_duration = duration
        self.timer = duration
        self.fade_in_duration = 0.0
        self.alpha = 255
        self.notification_type = notification_type
        self._render_message()

    def hide(self, target_type: str = None):
        """Hide notification instantly. If target_type is provided, only hide if current type matches."""
        if target_type and self.notification_type != target_type:
            return
        
        self.timer = 0
        self.alpha = 0
        self.surface = None

    def show_map_title(self, message: str):
        self.mode = "map_title"
        self.message = message
        self.max_duration = 4.0 # 1s in, 2s hold, 1s out
        self.timer = 4.0
        self.fade_in_duration = 1.0
        self.alpha = 0
        self.notification_type = "map_title"
        self._render_message()

    def update(self, dt: float):
        if self.timer > 0:
            self.timer -= dt
            
            # Fade Logic
            if self.mode == "map_title":
                passed = self.max_duration - self.timer
                if passed < self.fade_in_duration:
                    # Fade In
                    self.alpha = int(255 * (passed / self.fade_in_duration))
                elif self.timer < 1.0:
                    # Fade Out
                    self.alpha = int(255 * (self.timer / 1.0))
                else:
                    self.alpha = 255
            else:
                # Standard Fade Out
                if self.timer < 0.5:
                    self.alpha = int(255 * (self.timer / 0.5))
                else:
                    self.alpha = 255
            
            self.alpha = max(0, min(255, self.alpha))
        else:
            self.surface = None

    def draw(self, screen: pg.Surface):
        if self.surface and self.timer > 0:
            # Apply alpha to the whole surface if possible, or blit with special flags
            # Since the surface already has per-pixel alpha (background), strict alpha global might be tricky.
            # But the background is semi-transparent black.
            # Easiest way to handle fade out is to set alpha on the final surface.
            self.surface.set_alpha(self.alpha)
            screen.blit(self.surface, self.rect)

    def _render_message(self):
        screen_w = GameSettings.SCREEN_WIDTH
        screen_h = GameSettings.SCREEN_HEIGHT
        
        if self.mode == "map_title":
            # HUGE Text, Centered, Grey Border
            fontsize = 60
            text = self.message
            
            # Render Border (4 offsets)
            # Create labels for border
            border_labels = []
            offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
            
            for ox, oy in offsets:
                # We use Label just to get the surface
                lbl = Label(text, 0, 0, color=self.GREY, fontsize=fontsize, fontfam=1)
                border_labels.append(lbl)
                
            # Render Main Text
            main_lbl = Label(text, 0, 0, color=self.WHITE, fontsize=fontsize, fontfam=1)
            
            w = main_lbl.surface.get_width() + 10 # padding for offsets
            h = main_lbl.surface.get_height() + 10
            
            self.surface = pg.Surface((w, h), pg.SRCALPHA)
            
            # Center on new surface
            cx, cy = w // 2, h // 2
            
            # Blit Borders
            for i, lbl in enumerate(border_labels):
                 ox, oy = offsets[i]
                 # center of lbl rect should be cx+ox, cy+oy
                 rect = lbl.surface.get_rect(center=(cx+ox, cy+oy))
                 self.surface.blit(lbl.surface, rect)
                 
            # Blit Main
            rect = main_lbl.surface.get_rect(center=(cx, cy))
            self.surface.blit(main_lbl.surface, rect)
            
            self.rect = self.surface.get_rect(center=(screen_w // 2, screen_h // 2))
            
        else:
            # Standard Notification logic
            # Handle Multi-line splits first
            lines = self.message.split('\n')
            
            all_line_labels = []
            max_width = 0
            total_height = 0
            
            fontsize = 20
            
            for line in lines:
                # 1. Parse chunks for this line
                chunks = self._parse_colored_text(line)
                
                # 2. Create Labels for this line
                line_labels = []
                line_width = 0
                line_height = 0
                
                for text, color in chunks:
                    lbl = Label(text, 0, 0, color=color, fontsize=fontsize, fontfam=1)
                    line_labels.append(lbl)
                    line_width += lbl.surface.get_width()
                    line_height = max(line_height, lbl.surface.get_height())
                
                all_line_labels.append({'labels': line_labels, 'width': line_width, 'height': line_height})
                max_width = max(max_width, line_width)
                total_height += line_height
            
            # Add spacing between lines
            line_spacing = 5
            total_height += (len(lines) - 1) * line_spacing
                
            # 3. Create Background Surface
            padding_x = 20
            padding_y = 10
            bg_width = max_width + padding_x * 2
            bg_height = total_height + padding_y * 2
            
            self.surface = pg.Surface((bg_width, bg_height), pg.SRCALPHA)
            
            # Draw semi-transparent background (Black with 50% alpha = 128)
            self.surface.fill((0, 0, 0, 128)) 
            
            # 4. Blit Text onto Surface
            current_y = padding_y
            
            for line_data in all_line_labels:
                # Center each line horizontally within the background?
                # Or left align? User said "below that". Center looks better.
                line_w = line_data['width']
                line_h = line_data['height']
                
                current_x = padding_x + (max_width - line_w) // 2
                
                for lbl in line_data['labels']:
                    self.surface.blit(lbl.surface, (current_x, current_y))
                    current_x += lbl.surface.get_width()
                
                current_y += line_h + line_spacing
                
            # 5. Position at Bottom Center of Screen
            self.rect = self.surface.get_rect(centerx=screen_w // 2, bottom=screen_h - 50)

    def _parse_colored_text(self, text: str) -> list[tuple[str, tuple[int, int, int]]]:
        """
        Parses "[CYAN]Name[WHITE] used [YELLOW]Item" into 
        [('Name', CYAN), (' used ', WHITE), ('Item', YELLOW)]
        """
        chunks = []
        parts = text.split('[')
        
        current_color = self.WHITE
        
        for i, part in enumerate(parts):
            if i == 0 and not text.startswith('['):
                # First part before any tag
                if part:
                    chunks.append((part, current_color))
                continue
                
            if ']' in part:
                tag, content = part.split(']', 1)
                
                if tag == "YELLOW":
                    current_color = self.YELLOW
                elif tag == "CYAN":
                    current_color = self.CYAN
                elif tag == "WHITE":
                    current_color = self.WHITE
                
                if content:
                    chunks.append((content, current_color))
            else:
                # Malformed tag or just text? Treat as text if no closing bracket
                # But due to split, it means a [ was here.
                # Simplification: just append with current color
                if part:
                    chunks.append(('[' + part, current_color))
                    
        return chunks
