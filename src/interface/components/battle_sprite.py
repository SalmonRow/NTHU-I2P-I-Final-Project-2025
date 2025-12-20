import pygame as pg
from src.utils import load_img, Logger, GameSettings

class BattleSprite:
    def __init__(self, base_path: str, is_player: bool, scale: float = 3.5):
        self.is_player = is_player
        self.state = "idle" # idle, attack
        
        # Determine paths
        # base_path example: "sprites/sprite1.png" -> split to name
        # We assume assets have _idle.png and _attack.png suffixes in the same folder
        # But wait, original code loaded "base_path".
        # If base_path is "sprites/sprite1.png", we need "sprites/sprite1_idle.png"
        
        dot_idx = base_path.rfind('.')
        base_no_ext = base_path[:dot_idx] if dot_idx != -1 else base_path
        
        self.idle_frames = self._load_and_split(f"{base_no_ext}_idle.png", is_player, scale)
        self.attack_frames = self._load_and_split(f"{base_no_ext}_attack.png", is_player, scale)
        
        # Fallback if attack missing? Use idle
        if not self.attack_frames:
            self.attack_frames = self.idle_frames
            
        self.current_frames = self.idle_frames
        self.frame_idx = 0.0
        self.anim_speed = 1.5 # frames per second (Slower bob)
        self.loop = True
        
        # Position
        self.rect = pg.Rect(0, 0, 0, 0)
        if self.current_frames:
             self.rect = self.current_frames[0].get_rect()
             
        # Set Default Position logic (External code usually sets this, but defaults here)
        if is_player:
            self.rect.bottomleft = (5, GameSettings.SCREEN_HEIGHT)
        else:
            self.rect.topleft = (GameSettings.SCREEN_WIDTH - self.rect.width - 80, 60)

    def _load_and_split(self, path: str, is_player: bool, scale: float) -> list[pg.Surface]:
        try:
            full_sheet = load_img(path)
            if not full_sheet:
                 Logger.error(f"Could not load sprite sheet: {path}")
                 return []
            
            # Sheet Dimensions
            sw, sh = full_sheet.get_size()
            
            # LOGIC:
            # Sheet contains Front View (Left Half) and Back View (Right Half)?? 
            # Or usually: 
            # If 4 frames total strip: 
            # Player (Back View) is usually the Right Half? 
            # Enemy (Front View) is usually the Left Half?
            # Let's verify with the "original manual subsurface" logic:
            # Player: subsurface(Rect(w // 2, 0, w // 2, h)) -> Right Half
            # Enemy: subsurface(Rect(0, 0, w // 2, h)) -> Left Half
            
            half_w = sw // 2
            
            if is_player:
                # Use Right Half (Back View)
                view_surface = full_sheet.subsurface(pg.Rect(half_w, 0, half_w, sh))
            else:
                 # Use Left Half (Front View)
                view_surface = full_sheet.subsurface(pg.Rect(0, 0, half_w, sh))
                
            # Now split into frames. 
            # Assuming 2 frames per view? 
            # If the half width is divisible by 2?
            # Or is it a vertical strip? 
            # Visual check said: Idle 384x96. Original 192x96.
            # 384 / 2 = 192 (Half).
            # 192 Height 96.
            # If it has animation, maybe 2 frames horizontally?
            # 192 / 96 = 2. So 2 frames.
            
            FRAMES_COUNT = 2
            frame_w = view_surface.get_width() // FRAMES_COUNT
            frame_h = view_surface.get_height()
            
            frames = []
            for i in range(FRAMES_COUNT):
                frame = view_surface.subsurface(
                    pg.Rect(i * frame_w, 0, frame_w, frame_h)
                )
                # Scale
                w, h = frame.get_size()
                frame = pg.transform.scale(frame, (int(w * scale), int(h * scale)))
                
                frames.append(frame)
                
            return frames
            
        except Exception as e:
            Logger.error(f"Error loading sprite frames {path}: {e}")
            return []

    def play_attack(self):
        if self.state == "attack":
            return
        self.state = "attack"
        self.current_frames = self.attack_frames
        self.frame_idx = 0.0
        self.loop = False # Play once

    def play_idle(self):
        self.state = "idle"
        self.current_frames = self.idle_frames
        self.frame_idx = 0.0
        self.loop = True

    def update(self, dt: float):
        if not self.current_frames:
            return

        self.frame_idx += self.anim_speed * dt
        
        if self.frame_idx >= len(self.current_frames):
            if self.loop:
                self.frame_idx %= len(self.current_frames)
            else:
                # If non-looping (Attack), return to idle
                self.frame_idx = 0 # reset?
                self.play_idle()
                
    def draw(self, screen: pg.Surface):
        if not self.current_frames:
            return
            
        idx = int(self.frame_idx) 
        if idx >= len(self.current_frames):
             idx = len(self.current_frames) - 1
             
        img = self.current_frames[idx]
        screen.blit(img, self.rect)

    def get_current_image(self) -> pg.Surface | None:
        if not self.current_frames:
            return None
        idx = int(self.frame_idx)
        if idx >= len(self.current_frames):
             idx = len(self.current_frames) - 1
        return self.current_frames[idx]
