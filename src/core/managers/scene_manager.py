import pygame as pg

from src.scenes.scene import Scene
from src.utils import Logger

class SceneManager:
    
    _scenes: dict[str, Scene]
    _current_scene: Scene | None = None
    _next_scene: str | None = None
    _next_scene_kwargs: dict ={}
    
    _fade_alpha: float = 0.0
    _fade_speed: float = 300.0 # Alpha points per second
    _fading_in: bool = False
    
    def __init__(self):
        Logger.info("Initializing SceneManager")
        self._scenes = {}
        
    def register_scene(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene
        
    def change_scene(self, scene_name: str, **kwargs) -> None:
        if scene_name in self._scenes:
            Logger.info(f"Changing scene to '{scene_name}'")
            self._next_scene = scene_name
            self._next_scene_kwargs = kwargs
            
            # Start Fade sequence? 
            # We fade IN the new scene, but maybe we should fade OUT the current one?
            # User said "add a fade in effect when ever changing scenes". 
            # Usually that means fading FROM black TO the new scene.
        else:
            raise ValueError(f"Scene '{scene_name}' not found")
            
    def update(self, dt: float) -> None:
        # Handle scene transition
        if self._next_scene is not None:
            self._perform_scene_switch()
            
        # Update current scene
        if self._current_scene:
            self._current_scene.update(dt)
            
        # Update fade-in alpha
        if self._fading_in:
            self._fade_alpha -= self._fade_speed * dt
            if self._fade_alpha <= 0:
                self._fade_alpha = 0
                self._fading_in = False
            
    def draw(self, screen: pg.Surface) -> None:
        if self._current_scene:
            self._current_scene.draw(screen)
            
        # Draw Fade Overlay
        if self._fade_alpha > 0:
            from src.utils import GameSettings
            fade_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            fade_surf.set_alpha(int(self._fade_alpha))
            fade_surf.fill((0, 0, 0)) # Fading from black
            screen.blit(fade_surf, (0, 0))
            
    def _perform_scene_switch(self) -> None:
        if self._next_scene is None:
            return
            
        # Exit current scene
        if self._current_scene:
            self._current_scene.exit()
        
        self._current_scene = self._scenes[self._next_scene]
        
        # Enter new scene
        if self._current_scene:
            Logger.info(f"Entering {self._next_scene} scene")
            self._current_scene.enter(**self._next_scene_kwargs)
            
        # Trigger fade-in
        self._fade_alpha = 255.0
        self._fading_in = True
            
        # Clear the transition request
        self._next_scene = None
        self._next_scene_kwargs = {}

        