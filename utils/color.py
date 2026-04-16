type Color = tuple[int, int, int] | tuple[int, int, int, int]

BLACK: Color = (0, 0, 0)
BLUE: Color = (0, 0, 255)
GREEN: Color = (0, 255, 0)
CYAN: Color = (0, 255, 255)
RED: Color = (255, 0, 0)
PINK: Color = (255, 0, 255)
YELLOW: Color = (255, 255, 0)
WHITE: Color = (255, 255, 255)

def toHex(color: Color) -> str:
    def convertByte(num: int) -> str:
        lo = num&0x0f
        hi = (num&0xf0)>>4
        return convertNibble(hi)+convertNibble(lo)

    def convertNibble(num: int) -> str:
        if 0<=num<=9:return str(num)
        match num:
            case 10:return "A"
            case 11:return "B"
            case 12:return "C"
            case 13:return "D"
            case 14:return "E"
            case 15:return "F"
            case _:raise ValueError("num must be between 0 and 15")

    r = color[0]
    g = color[1]
    b = color[2]
    a = color[3] if len(color) >= 4 else None

    r_str = convertByte(r)
    g_str = convertByte(g)
    b_str = convertByte(b)
    a_str = convertByte(a) if not a is None else ""

    return "#" + r_str + g_str + b_str+a_str

def fromHex(color: str) -> Color:
    def convertChr(chr: str) -> int:
        match chr.lower():
            case "0":return 0
            case "1":return 1
            case "2":return 2
            case "3":return 3
            case "4":return 4
            case "5":return 5
            case "6":return 6
            case "7":return 7
            case "8":return 8
            case "9":return 9
            case "a":return 10
            case "b":return 11
            case "c":return 12
            case "d":return 13
            case "e":return 14
            case "f":return 15
            case _:
                raise ValueError("Invalid Char")
    
    def convertByte(color: str) -> int:
        lo = convertChr(color[1])
        hi = convertChr(color[0])
        return lo+(hi<<4)

    if not color or color[0] != "#":
        raise ValueError("Invalid Color Given")
    match len(color):
        case 7:
            r = color[1:3]
            g = color[3:5]
            b = color[5:7]
            a = None
        case 9:
            r = color[1:3]
            g = color[3:5]
            b = color[5:7]
            a = color[7:9]
        case _:
            raise ValueError("Invalid Color Given")

    r_int = convertByte(r)
    g_int = convertByte(g)
    b_int = convertByte(b)
    a_int = convertByte(a) if a else None

    rgb = (r_int, g_int, b_int)
    rgba = (*rgb, a_int) if not a_int is None else None

    return rgba or rgb

if __name__ == "__main__":
    print(toHex((12, 34, 56)))
    print(toHex((12, 34, 56, 78)))
    print(fromHex("#0C2238"))
    print(fromHex("#0C22384E"))