import pygame as pg
from src.utils import GameSettings, Logger
from src.core.services import input_manager
from src.interface.components.label import Label
from typing import Optional

class ChatOverlay:
    def __init__(self, online_manager: Optional[object]): # Type hint loose to avoid circular import issues if helpful
        self.online_manager = online_manager
        
        # State Management
        # ACTIVE: Fully visible, accepting input
        # FADING: Visible (fading out), NO input
        # INACTIVE: Hidden, NO input
        self.STATE_ACTIVE = 0
        self.STATE_FADING = 1
        self.STATE_INACTIVE = 2
        
        self.current_state = self.STATE_INACTIVE
        
        self.input_text = ""
        self.messages: list[dict] = [] # Stores dicts: {'sender': str, 'content': str}
        
        # UI Dimensions
        # 1/3 Width, 1/2 Height
        w = GameSettings.SCREEN_WIDTH // 3
        h = GameSettings.SCREEN_HEIGHT // 2
        x = 10
        y = GameSettings.SCREEN_HEIGHT - h - 10
        
        self.bg_rect = pg.Rect(x, y, w, h)
        
        # Input area at bottom of bg_rect
        input_h = 30
        self.input_rect = pg.Rect(x + 5, self.bg_rect.bottom - input_h - 5, w - 10, input_h)
        
        # History area above input
        self.history_rect = pg.Rect(x + 5, y + 5, w - 10, h - input_h - 15)
        
        # Visuals
        self.bg_surf = pg.Surface((w, h), pg.SRCALPHA)
        self.bg_surf.fill((0, 0, 0, 128)) # 50% Alpha Black
        # self.bg_surf.set_alpha(128) # Removed surface alpha to rely on per-pixel alpha
        
        # Fading
        self.fade_timer = 0.0
        self.FADE_DURATION = 0.5
        self.current_alpha = 255
        
        self.blink_timer = 0.0
        self.show_cursor = True
        self.inactivity_timer = 0.0
        self.AUTO_HIDE_TIME = 4.0
        
        # Helper label for input
        self.input_label = Label("", 0, 0, fontsize=18, color=(255, 255, 255))
        
        # Cached render surface for fading
        self.render_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)

    @property
    def active(self):
        return self.current_state != self.STATE_INACTIVE

    @property
    def is_blocking_input(self):
        # Block inputs ONLY when ACTIVE (typing). 
        # When FADING, we are passive/viewing, so unblock inputs.
        return self.current_state == self.STATE_ACTIVE

    def update(self, dt: float):
        # Fetch messages
        if self.online_manager:
            raw_msgs = self.online_manager.get_messages()
            self.messages = []
            for m in raw_msgs[-15:]:
                self.messages.append({
                    'sender': f"Player {m['sender_id']}",
                    'content': m['content']
                })
        else:
            # Single player mode: self.messages is maintained locally
            pass

        # State Machine Logic
        if self.current_state == self.STATE_ACTIVE:
            self._update_active_state(dt)
        elif self.current_state == self.STATE_FADING:
            self._update_fading_state(dt)
        elif self.current_state == self.STATE_INACTIVE:
            self._update_inactive_state(dt)

    def _update_inactive_state(self, dt: float):
        # Check for Open Command
        for event in input_manager.events_of_frame:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    self.open()
            
    def _update_active_state(self, dt: float):
        # Handle input
        key_pressed = False
        
        for event in input_manager.events_of_frame:
            if event.type == pg.KEYDOWN:
                key_pressed = True
                
                if event.key == pg.K_RETURN:
                     if self.input_text.strip():
                        self._send_message(self.input_text)
                        self.input_text = ""
                     
                     # Reset inactivity logic
                     self.inactivity_timer = 0.0
                        
                elif event.key == pg.K_ESCAPE:
                    self._start_fade_out()
                    
                else:
                    # Typing
                    self.inactivity_timer = 0.0 # Reset timer on typing
                    if event.key == pg.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        if len(self.input_text) < 50:
                            self.input_text += event.unicode
        
        # Auto-Hide Logic
        if not key_pressed:
            self.inactivity_timer += dt
        else:
             self.inactivity_timer = 0.0
        
        if self.inactivity_timer >= self.AUTO_HIDE_TIME:
            self._start_fade_out()

        # Cursor Blink
        self.blink_timer += dt
        if self.blink_timer >= 0.5:
            self.blink_timer = 0
            self.show_cursor = not self.show_cursor
                
        # Update Input Label
        cursor_char = "|" if self.show_cursor else ""
        self.input_label.set_text(self.input_text + cursor_char)
        
    def _update_fading_state(self, dt: float):
        self.fade_timer += dt
        progress = self.fade_timer / self.FADE_DURATION
        
        if progress >= 1.0:
            self.current_state = self.STATE_INACTIVE
            self.current_alpha = 0
        else:
            # Fade out alpha (255 -> 0)
            self.current_alpha = int(255 * (1.0 - progress))
            
            # NOTE: Logic to INTERRUPT fade with enter?
            # User requirement: "when pressing enter the chat would popup"
            # If FADING and user presses Enter, we should probably switch back to ACTIVE.
            if input_manager.key_pressed(pg.K_RETURN):
                 self.current_state = self.STATE_ACTIVE
                 self.current_alpha = 255
                 self.inactivity_timer = 0.0
                 self.input_text = "" # Clear input or keep it? Likely clear if we were closing.

    def open(self):
        """Called externally (e.g. from GameScene) or implicitly via Enter."""
        # Reset state to ACTIVE
        self.current_state = self.STATE_ACTIVE
        self.input_text = ""
        self.blink_timer = 0.0
        self.show_cursor = True
        self.inactivity_timer = 0.0
        self.current_alpha = 255

    def _start_fade_out(self):
        self.current_state = self.STATE_FADING
        self.fade_timer = 0.0
        self.current_alpha = 255

    def _send_message(self, text: str):
        if self.online_manager:
            self.online_manager.send_message(text)
        else:
            # Local echo
            self.messages.append({'sender': 'You', 'content': text})
            # Keep only last 15
            if len(self.messages) > 15:
                self.messages.pop(0)

    def draw(self, screen: pg.Surface):
        if self.current_state == self.STATE_INACTIVE:
            return
            
        # We draw everything to a cleared transparent surface first to apply global alpha?
        # Drawing individually with alpha might be cheaper than blitting full screen surface.
        # But text alpha is handled by Render.
        # Let's draw to screen directly but modify component alpha if possible?
        # Text doesn't support easy alpha mod after render without `set_alpha`.
        # Blitting a surface is cleanest for fade.
        
        self.render_surf.fill((0,0,0,0)) # Clear
        
        # 1. Background
        # Re-apply alpha to bg_surf based on current_alpha??
        # bg_surf already has 180 alpha.
        # If we want to fade it, we need to scale that.
        # Combined Alpha = (180/255) * (current_alpha/255)
        # Easiest: Draw normally to render_surf, then blit render_surf with current_alpha.
        
        self.render_surf.blit(self.bg_surf, self.bg_rect)
        
        # 2. Messages
        y = self.history_rect.bottom - 20
        YELLOW = (255, 255, 0)
        WHITE = (255, 255, 255)
        
        for msg in reversed(self.messages):
            sender_txt = f"{msg['sender']}: "
            content_txt = msg['content']
            
            # Simple layout: Sender Content
            # Measure sender width to place content?
            # Or just use two labels.
            
            # Label 1: Sender (Yellow)
            l1 = Label(sender_txt, self.history_rect.x, y, fontsize=18, color=YELLOW)
            l1.draw(self.render_surf)
            
            # Measure width roughly? Or accessing rect
            offset_x = l1.rect.width
            
            # Label 2: Content (White)
            l2 = Label(content_txt, self.history_rect.x + offset_x, y, fontsize=18, color=WHITE)
            l2.draw(self.render_surf)
            
            y -= 22
            if y < self.history_rect.top:
                break
                
        # 3. Input Area (Only if ACTIVE, not fading? "it disappears... fades away")
        # If fading, maybe we still show input text fading out?
        # Yes, whole thing fades.
        
        pg.draw.rect(self.render_surf, (50, 50, 50), self.input_rect)
        pg.draw.rect(self.render_surf, (100, 100, 100), self.input_rect, 1)
        
        # Draw Input Text
        self.input_label._render_text(self.input_rect.x + 5, self.input_rect.y + 4)
        self.input_label.draw(self.render_surf)

        # Apply Global Fade
        if self.current_state == self.STATE_FADING:
             self.render_surf.set_alpha(self.current_alpha)
        else:
             self.render_surf.set_alpha(255)
             
        screen.blit(self.render_surf, (0,0))
