import enum
# TODO:
#   - multiline support, vertical clipping? how to handle multiple spans

from .width import get_width, crop
# Attribute:
#   Style:
#      BOLD (on, off, inherit)
#      UNDERLINE (on, off, inherit)
#      REVERSE (on, off, inherit)
#   foreground color, default, or None (inherit)
#   Background color, default, or None (inherit)

class Pad(enum.Enum):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    CENTER = 3

def color_to_rgb(color):
    '''
    Parse hexadecimal RGB.
    '''
    if color[0] == '#':
        color = color[1:]
    assert(len(color) == 6)
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))

INHERIT = object() # Inherit attribute from outer scope
DEFAULT = object() # Default foreground/background

class TextAttr:
    # styles
    bold = INHERIT
    underline = INHERIT
    reverse = INHERIT
    # colors
    fg = INHERIT
    bg = INHERIT

    def __init__(self, fg=INHERIT, bg=INHERIT, bold=INHERIT, underline=INHERIT, reverse=INHERIT):
        self.bold = bold
        self.underline = underline
        self.reverse = reverse
        self.fg = fg
        self.bg = bg

    @classmethod
    def reset(cls, fg=DEFAULT, bg=DEFAULT, bold=False, underline=False, reverse=False):
        return cls(fg=fg, bg=bg, bold=bold, underline=underline, reverse=reverse)

    def clone(self):
        return TextAttr(fg=self.fg, bg=self.bg, bold=self.bold, underline=self.underline, reverse=self.reverse)

    def __eq__(self, other):
        return (self.fg == other.fg and
                self.bg == other.bg and
                self.bold == other.bold and
                self.underline == other.underline and
                self.reverse == other.reverse)

    def apply(self, other):
        '''Apply an attribute change to the current one.'''
        if other is None: # NOP
            return self
        if other.bold != INHERIT:
            self.bold = other.bold
        if other.underline != INHERIT:
            self.underline = other.underline
        if other.reverse != INHERIT:
            self.reverse = other.reverse
        if other.fg != INHERIT:
            self.fg = other.fg
        if other.bg != INHERIT:
            self.bg = other.bg
        return self

    def __repr__(self):
        tokens = []
        if self.fg != INHERIT:
            if self.fg == DEFAULT:
                tokens.append('fg=DEFAULT')
            else:
                tokens.append('fg=' + self.fg)
        if self.bg != INHERIT:
            if self.bg == DEFAULT:
                tokens.append('bg=DEFAULT')
            else:
                tokens.append('bg=' + self.fg)
        if self.bold != INHERIT:
            tokens.append('bold=' + repr(self.bold))
        if self.underline != INHERIT:
            tokens.append('underline=' + repr(self.underline))
        if self.reverse != INHERIT:
            tokens.append('reverse=' + repr(self.reverse))
        return 'TextAttr(' + (','.join(tokens)) + ')'

    def diff_str(self, prev):
        '''
        Represent a difference in attributes as ANSI string. None of the attributes can be INHERIT.
        '''
        if (self.fg == INHERIT or
            self.bg == INHERIT or
            self.bold == INHERIT or
            self.underline == INHERIT or
            self.reverse == INHERIT):
            raise ValueError('None of the attributes can be INHERIT')
        tokens = []
        if prev is None or self != prev:
            tokens.append(0) # always reset for now
            if self.bold:
                tokens.append(1)
            if self.underline:
                tokens.append(4)
            if self.reverse:
                tokens.append(7)
            if self.fg != DEFAULT:
                tokens.append(38)
                tokens.append(2)
                tokens.extend(color_to_rgb(self.fg))
            if self.bg != DEFAULT:
                tokens.append(48)
                tokens.append(2)
                tokens.extend(color_to_rgb(self.bg))
        if tokens:
            return '\x1b[' + (';'.join(str(x) for x in tokens)) + 'm'
        else:
            return ''

# State after rese (CSI 0)t.
RESET = TextAttr.reset()
# No change update.
NOP = TextAttr()

def render_inner(out, tokens, parent_attr, cur_attr, width_left):
    dest_attr = parent_attr.clone()
    for tok in tokens:
        if isinstance(tok, str):
            out.append(dest_attr.diff_str(cur_attr))
            if width_left[0] is not None:
                (s, l) = crop(tok, width_left[0])
                out.append(s)
                width_left[0] -= l
            else:
                out.append(tok)
            cur_attr.apply(dest_attr)
        elif isinstance(tok, TextAttr):
            dest_attr.apply(tok)
        elif isinstance(tok, (list, tuple)):
            render_inner(out, tok, dest_attr, cur_attr, width_left)
        else:
            raise ValueError(f"Don't know how to render {tok}")

def render(tokens, attr=RESET, width=None, pad=Pad.NONE, pad_ch=' '):
    '''Render to a string.'''
    if not isinstance(tokens, (tuple, list)):
        tokens = [tokens]
    out = []
    # Initially go from nothing to attr
    out.append(attr.diff_str(None))
    cur_attr = attr.clone()
    width_left = [width]
    render_inner(out, tokens, attr, cur_attr, width_left)
    # restore attribute to parent attr
    out.append(attr.diff_str(cur_attr))
    if width is not None and width_left[0] > 0:
        if pad == Pad.LEFT:
            out.append((pad_ch * width_left[0]))
        elif pad == Pad.RIGHT:
            out.insert(1, (pad_ch * width_left[0]))
        elif pad == Pad.CENTER:
            out.insert(1, (pad_ch * (width_left[0] // 2)))
            out.append((pad_ch * ((width_left[0] + 1) // 2)))
    out.append('\x1b[0m') # reset after
    return ''.join(out)

def width(tokens):
    '''Compute total width of formatted text.'''
    if not isinstance(tokens, (tuple, list)):
        tokens = [tokens]
    rv = 0
    for tok in tokens:
        if isinstance(tok, str):
            rv += get_width(tok)
        elif isinstance(tok, (list, tuple)):
            rv += width(tok)
    return rv

if __name__ == '__main__':
    print(TextAttr(fg='#808080'))

    print(RESET)

    cur = RESET.clone()
    new = cur.clone()
    new.apply(TextAttr(fg='#ff8080'))
    print(new.diff_str(cur) + 'hi' + cur.diff_str(new) + 'hi')

    text = [
        TextAttr(fg='#ff0000'),
        'hi',
        [ # Push new context
            TextAttr(fg='#00ff00'),
            'hi',
        ],
        'hi',
        [ # Push new context
            TextAttr(bold=True,bg='#404040'),
            'hi',
        ],
        'nonbold',
    ]

    print(render(text))
    print(render("123"))
    for w in range(0, width(text) + 1):
        print(render(text, width=w) + '|', w)
    print(render(text, width=40, pad=Pad.LEFT) + '|', 40)
    print(render(text, width=40, pad=Pad.RIGHT) + '|', 40)
    print(render(text, width=40, pad=Pad.CENTER) + '|', 40)
