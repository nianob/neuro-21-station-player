import pygame
import pygame_widgets

from utils import color

from pygame_widgets.widget import WidgetBase
from pygame_widgets.textbox import TextBox
from pygame_widgets.mouse import Mouse, MouseState

class ColorPicker(WidgetBase):
    def __init__(self, win, x, y, width, height, default_color: color.Color, isSubWidget=False):
        super().__init__(win, x, y, width, height, isSubWidget)
        self._active = False
        self.color = default_color
        self._textbox = TextBox(win, width, 0, width*4, height, True, onTextChanged=self._onTextboxTextChanged)
        self._textbox.setText(color.toHex(default_color))
        self._rect = pygame.Rect(self._x, self._y, self._width, self._height)
    
    def listen(self, events):
        mouseState = Mouse.getMouseState()
        x, y = Mouse.getMousePos()

        if not self._active and mouseState == MouseState.CLICK and self._rect.collidepoint(x, y):
            self._active = True
        
        if self._active:
            self._textbox.listen(events)
    
    def draw(self):
        if self._active:
            pygame.draw.rect(self.win, self.color, self._rect, border_top_left_radius=int(self._height*0.25))
            self._textbox.draw()
        else:
            pygame.draw.rect(self.win, self.color, self._rect, border_radius=int(self._height*0.25))

    def _onTextboxTextChanged(self):
        try:
            self.color = color.fromHex(self._textbox.getText())
            self._textbox.textColour = color.BLACK
        except ValueError:
            self._textbox.textColour = color.RED

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    colorpicker = ColorPicker(screen, 0, 0, 40, 40, color.BLACK)
    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        
        screen.fill(color.WHITE)
        pygame_widgets.update(events)
        pygame.display.flip()
        
    