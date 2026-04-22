from __future__ import annotations
import pygame

from typing import Optional, Callable, Concatenate, TypeVar, ParamSpec, Literal

from customtypes import *


_T = TypeVar("_T")
_P = ParamSpec("_P")

# ----------------------------------------------------------------
# The Base Class
class SurfaceBase:
    CURSOR: int = pygame.SYSTEM_CURSOR_ARROW # The cursor to be displayed when hovering this surface
    BG_COLOR: pygame.Color = pygame.Color(0, 0, 0, 0)

    def __init__(self, rect: pygame.Rect):
        self.rect: pygame.Rect = rect
        self.surface: pygame.Surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._subsurfaces: list[Surface] = []
    
    def update(self, **kwargs) -> None:
        """Updates the surface and all subsurfaces"""
        self.surface.fill(self.BG_COLOR)
        for surface in self.subsurfaces:
            surface.update(**kwargs)
    
    def pass_function(self, func: Callable[Concatenate[Surface, int, int, _P], _T], x: int, y: int, *args: _P.args, **kwargs: _P.kwargs) -> tuple[Literal[True], _T] | tuple[Literal[False], None]:
        """Passes a function to a subsurface
        
        Args:
            x: the x position
            y: the y position
            ...: all additional arguments are passed on
        Returns:
            tuple:
                success: Wether or not the function has been passed on

                return: What the function returned, None if no function was executed
        """
        for surface in self.subsurfaces:
            if surface.collide(x, y):
                return True, func(surface, x, y, *args, **kwargs)
        return False, None
    
    def collide(self, x: int, y: int) -> bool:
        """Checks if an **absolute** position collides this surface
        
        Args:
            x: the absolute x position
            y: the absolute y position

        Returns:
            bool: Wether or not the mouse collides this surface
        """
        moved_x = x-self.x
        moved_y = y-self.y

        return self.rect.collidepoint(moved_x, moved_y)
    
    def handle_click(self, x: int, y: int) -> None:
        self.pass_function(lambda c, x, y: c.handle_click(x, y), x, y)
       
    def set_cursor(self, x: int, y: int) -> None:
        passed, _ = self.pass_function(lambda c, x, y: c.set_cursor(x, y), x, y)
        if not passed:
            pygame.mouse.set_cursor(self.CURSOR)
    
    @property
    def subsurfaces(self) -> list[Surface]:
        return self._subsurfaces

    @property
    def x(self) -> int:
        """The absolute X position"""
        return self.rect.x
    
    @x.setter
    def x(self, value: int):
        self.rect.x = value
    
    @property
    def y(self) -> int:
        """The absolute Y position"""
        return self.rect.y
    
    @y.setter
    def y(self, value: int):
        self.rect.y = value

# ----------------------------------------------------------------
# The Base Class for general subsurfaces
class Surface(SurfaceBase):
    """A general surface"""

    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None):
        super().__init__(rect)
        self._parent: Optional[SurfaceBase] = parent

    @property
    def parent(self) -> Optional[SurfaceBase]:
        return self._parent
    
    @parent.setter
    def parent(self, value: Optional[SurfaceBase]):
        if value == self._parent:
            return
        if self._parent:
            self._parent._subsurfaces.remove(self)
        if value:
            value._subsurfaces.append(self)
        self._parent = value

    @property
    def x(self) -> int:
        return self.parent.x + self.rect.x if self.parent else self.rect.x
    
    @x.setter
    def x(self, value: int):
        self.rect.x = value - self.parent.x if self.parent else value
    
    @property
    def y(self) -> int:
        return self.parent.y - self.rect.y if self.parent else self.rect.y
    
    @y.setter
    def y(self, value: int):
        self.rect.y = value - self.parent.y if self.parent else value

# ----------------------------------------------------------------
# The base class for screens
# A screen if a fullscreen surface.
class Screen(SurfaceBase):
    """A Screen"""
    def draw(self, surface: pygame.Surface) -> None:
        """Draws this screen onto a surface
        
        Args:
            surface: The surface to draw to
        """
        surface.blit(self.surface, (0, 0))
    
    def process_events(self, events: Optional[list[pygame.event.Event]] = None) -> None:
        """Processes all of the events
        
        Args:
            events: the list of events. Uses `pygame.event.get()` if undefined
        """
        if events is None:
            events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(*event.pos)
            elif event.type == pygame.KEYDOWN:
                self.handle_keypress(event.key)
    
    def handle_keypress(self, key: int) -> None:
        """Handles all keypresses"""
