from __future__ import annotations
import pygame

from abc import ABC, abstractmethod
from typing import Optional, Callable, Concatenate, TypeVar, ParamSpec, Literal, Any, Iterable

from customtypes import *
from customtypes import Coordinate


_T = TypeVar("_T")
_P = ParamSpec("_P")

# ----------------------------------------------------------------
# The Base Class
class SurfaceBase(ABC):
    CURSOR: int = pygame.SYSTEM_CURSOR_ARROW # The cursor to be displayed when hovering this surface
    BG_COLOR: pygame.Color = pygame.Color(0, 0, 0, 0)

    def __init__(self, rect: pygame.Rect):
        self.rect: pygame.Rect = rect
        self.surface: pygame.Surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._subsurfaces: list[Surface] = []
        self._parent = None
    
    def update(self) -> None:
        """Updates the surface and all subsurfaces"""
        self.surface.fill(self.BG_COLOR)
        self.render()
        for surface in self.subsurfaces:
            surface.update()
            self.surface.blit(surface.surface, surface.rect)
        pygame.draw.rect(self.surface, (255, 0, 0), (0, 0, self.width, self.height), 2)
    
    def render(self) -> None:...
    
    def pass_function(self, func: Callable[Concatenate[Surface, int, int, _P], _T], x: int, y: int, *args: _P.args, **kwargs: _P.kwargs) -> tuple[Literal[True], _T] | tuple[Literal[False], None]:
        """Passes a function to a subsurface
        
        Args:
            func: the function to call
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

        return 0 <= moved_x <= self.width and 0 <= moved_y <= self.height 
    
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
    
    @property
    def width(self) -> int:
        return self.rect.width
    
    @width.setter
    def width(self, value: int):
        self.rect.width = value
    
    @property
    def height(self) -> int:
        return self.rect.height
    
    @height.setter
    def height(self, value: int):
        self.rect.height = value

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height
    
    @size.setter
    def size(self, value: tuple[int, int]):
        self.width, self.height = value
    
    @property
    @abstractmethod
    def app(self) -> Optional[App]:...

# ----------------------------------------------------------------
# The Base Class for general subsurfaces
class Surface(SurfaceBase):
    """A general surface"""

    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None):
        super().__init__(rect)
        self._parent: Optional[SurfaceBase] = None
        self.parent = parent

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
        return self.parent.y + self.rect.y if self.parent else self.rect.y
    
    @y.setter
    def y(self, value: int):
        self.rect.y = value - self.parent.y if self.parent else value
    
    @property
    def app(self) -> Optional[App]:
        if not self.parent:
            return None
        return self.parent.app

# ----------------------------------------------------------------
# The base class for screens
# A screen if a fullscreen surface.
class Screen(SurfaceBase):
    """A Screen"""

    def __init__(self, rect: pygame.Rect, app: App):
        super().__init__(rect)
        self._app: App = app

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
            elif event.type == pygame.QUIT:
                self.app.quit()
            elif event.type == pygame.VIDEORESIZE and isinstance(self.app, ResizeableApp):
                self.app.onResize(event.size, event.w, event.h)
    
    def handle_keypress(self, key: int) -> None:
        """Handles all keypresses"""
    
    @property
    def app(self) -> App:
        return self._app
    
# ----------------------------------------------------------------
# The base class for any any app using this library
class App(ABC):
    WINDOW_FLAGS = 0

    def __init__(self, window_size: Coordinate) -> None:
        self.surface: pygame.Surface = pygame.display.set_mode(window_size, self.WINDOW_FLAGS)

    @abstractmethod
    def quit(self) -> None:
        """Runs when the app is closed"""


class ResizeableApp(App):
    WINDOW_FLAGS = pygame.RESIZABLE

    def onResize(self, size: Coordinate, width: int, height: int) -> None:
        self.surface = pygame.display.set_mode(size, self.WINDOW_FLAGS)

# ----------------------------------------------------------------
# Other useful surfaces
class Text(Surface):
    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None, text: str = "", color: Optional[Color] = None, font: Optional[pygame.font.Font] = None):
        super().__init__(rect, parent)
        self._redraw = True
        self._text: str = text
        self._color: Color = color or (0, 0, 0)
        self._font = font or pygame.font.SysFont("calibri", 300)

    def update(self) -> None:
        if not self._redraw:
            return
        self._redraw = False
        super().update()
        if self.text:
            rendered_text = self.font.render(self.text, True, self.color)
            width, height = rendered_text.get_size()
            scale_factor = min(self.rect.width/width, self.rect.height/height)
            scaled_text = pygame.transform.smoothscale_by(rendered_text, scale_factor)
            self.surface.blit(scaled_text, (self.width/2-scaled_text.get_width()/2, self.height/2-scaled_text.get_height()/2))

    @property
    def text(self) -> str:
        return self._text
    
    @text.setter
    def text(self, value: str):
        self._text = value
        self._redraw = True

    @property
    def color(self) -> Color:
        return self._color
    
    @color.setter
    def color(self, value: Color):
        self._color = value
        self._redraw = True
    
    @property
    def font(self) -> pygame.font.Font:
        return self._font
    
    @font.setter
    def font(self, value: pygame.font.Font):
        self._font = value
        self._redraw = True
    
    @property
    def width(self) -> int:
        return super().width
    
    @width.setter
    def width(self, value: int):
        super().width = value
        self._redraw = True
    
    @property
    def height(self) -> int:
        return super().height
    
    @height.setter
    def height(self, value: int):
        super().height = value
        self._redraw = True


class ButtonBase(Surface):
    CURSOR = pygame.SYSTEM_CURSOR_HAND
    CURSOR_DISABLED = pygame.SYSTEM_CURSOR_NO
    SUBSURFACE_SCALE = 1

    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None, color: Optional[Color] = None, *, subsurface: type[Surface], subsurface_args: Optional[Iterable[Any]] = None, subsurface_kwargs: Optional[dict[str, Any]] = None):
        super().__init__(rect, parent)
        self.color: Color = color or (127, 127, 127)
        self.enabled = True

        subsurface_rect = pygame.Rect(0, 0, self.width*self.SUBSURFACE_SCALE, self.height*self.SUBSURFACE_SCALE)
        subsurface_rect.x = self.width//2 - subsurface_rect.centerx
        subsurface_rect.y = self.height//2 - subsurface_rect.centery
        self._subsurface = subsurface(subsurface_rect, self, *(subsurface_args or []), **(subsurface_kwargs or {}))

    def render(self):
        pygame.draw.rect(self.surface, self.color, (0, 0, self.width, self.height), border_radius=self.height//2)

    def handle_click(self, x: int, y: int) -> None:
        self.onClick()
    
    def set_cursor(self, x: int, y: int) -> None:
        pygame.mouse.set_cursor(self.CURSOR if self.enabled else self.CURSOR_DISABLED)

    @abstractmethod
    def onClick(self) -> None:...
    
    @property
    def width(self) -> int:
        return super().width
    
    @width.setter
    def width(self, value: int):
        super().width = value
        self.subsurface.width = int(value*self.SUBSURFACE_SCALE)
        self.subsurface.rect.x = value//2-self.subsurface.width//2

    @property
    def height(self) -> int:
        return super().height
    
    @height.setter
    def height(self, value: int):
        super().height = value
        self.subsurface.height = int(value*self.SUBSURFACE_SCALE)
        self.subsurface.rect.y = value//-self.subsurface.height//2
    
    @property
    def subsurface(self) -> Surface:
        return self._subsurface
    
    @subsurface.setter
    def subsurface(self, value: Surface):
        value.size = self.subsurface.size
        value.rect.topleft = self.subsurface.rect.topleft
        self.subsurface.parent = None
        value.parent = self
        self._subsurface = value

class TextButton(ButtonBase):
    SUBSURFACE_SCALE = 0.63

    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None, color: Optional[Color] = None, text: str = "", text_color: Optional[Color] = None, font: Optional[pygame.font.Font] = None):
        super().__init__(rect, parent, color, subsurface=Text, subsurface_args=(text, text_color, font))

    @property
    def text(self) -> Text:
        if not isinstance(self.subsurface, Text):
            raise ValueError
        return self.subsurface

    @text.setter
    def text(self, value: Text):
        self.subsurface = value

class ImageButton(ButtonBase):
    SUBSURFACE_SCALE = 0.5

    def __init__(self, rect: pygame.Rect, parent: Optional[SurfaceBase] = None, color: Optional[Color] = None, image: Optional[Surface] = None):
        super().__init__(rect, parent, color, subsurface=Surface)
        self.subsurface = image or Surface(pygame.Rect(0, 0, 0, 0), self)

if __name__ == "__main__":
    class ExampleApp(ResizeableApp):
        running = True
        def __init__(self, window_size: tuple[int, int]) -> None:
            pygame.font.init()
            super().__init__(window_size)
            self.screen = Screen(self.surface.get_rect(), self)
            self.btn = QuitButton(pygame.Rect(100, 100, 500, 200), self.screen, text="Quit")

        def quit(self) -> None:
            self.running = False
    
        def loop(self):
            while self.running:
                self.screen.process_events()
                self.screen.update()
                self.screen.set_cursor(*pygame.mouse.get_pos())
                self.screen.draw(self.surface)
                pygame.display.flip()
    
    class QuitButton(TextButton):
        def onClick(self) -> None:
            if self.app:
                self.app.quit()
    
    app = ExampleApp((800, 800))
    app.loop()
