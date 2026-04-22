__all__ = ["Coordinate", "Color", "Colors"]

type percent = float # from 0 to 1
type Byte = int # from 0 to 255
type Color = tuple[Byte, Byte, Byte] # A pygame color
type Colora = tuple[Byte, Byte, Byte, Byte] # A pygame color with alpha
type percent_vector = tuple[percent, percent] # A Vecor defining a size or position
type Coordinate = tuple[int, int] # A coordinate defining a size or position

class Colors:
    BLACK: Color = (0, 0, 0)
    BLUE: Color = (0, 0, 255)
    GREEN: Color = (0, 255, 0)
    CYAN: Color = (0, 255, 255)
    RED: Color = (255, 0, 0)
    PINK: Color = (255, 0, 255)
    YELLOW: Color = (255, 255, 0)
    WHITE: Color = (255, 255, 255)