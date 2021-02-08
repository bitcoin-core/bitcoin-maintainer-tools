class Attr:
    '''
    Terminal output attributes.
    '''
    def fg(r, g, b):
        return f'\x1b[38;2;{r};{g};{b}m'

    def bg(r, g, b):
        return f'\x1b[48;2;{r};{g};{b}m'

    def fg_hex(color):
        if color[0] == '#':
            color = color[1:]
        assert(len(color) == 6)
        return Attr.fg(int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))

    def bg_hex(color):
        if color[0] == '#':
            color = color[1:]
        assert(len(color) == 6)
        return Attr.bg(int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))

    def close(attr):
        # Close an attribute (restore terminal to "neutral")
        return Attr.RESET

    RESET = '\x1b[0m'
    BOLD = '\033[1m'
    CLEAR = '\x1b[H\x1b[J\x1b[3J'
    UNDERLINE = '\x1b[4m'
    REVERSE = '\033[7m'
