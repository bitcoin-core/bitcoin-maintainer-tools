from collections import namedtuple
import enum
import unicodedata

class Align(enum.Enum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2

# from https://bugs.python.org/msg145523
W = {
'F': 2,  # full-width, width 2, compatibility character for a narrow char
'H': 1,  # half-width, width 1, compatibility character for a narrow char
'W': 2,  # wide, width 2
'Na': 1, # narrow, width 1
'A': 1,  # ambiguous; width 2 in Asian context, width 1 in non-Asian context
'N': 1,  #neutral; not used in Asian text, so has no width. Practically, width can be considered as 1
}

def get_width(s):
    # TODO:
    # - Handle embedded attributes
    return sum(W[unicodedata.east_asian_width(ch)] for ch in s)

def crop(s, width):
    '''Crop a string to a certain visual length.'''
    # TODO:
    # - Handle embedded attributes
    # - Ellipsis … ?
    o = 0
    l = 0
    for ch in s:
        w = W[unicodedata.east_asian_width(ch)]
        if l + w > width:
            break
        l += w
        o += 1

    return (s[0:o], l)

def pad(s, width, align):
    # TODO:
    # - Handle embedded attributes
    s, swidth = crop(s, width)
    padding = width - swidth
    if align == Align.LEFT:
        return s + (' ' * padding)
    elif align == Align.RIGHT:
        return (' ' * padding) + s
    elif align == Align.CENTER:
        return (' ' * (padding // 2)) + s + (' ' * ((padding + 1) // 2))

class Column:
    def __init__(self, title, width, align=Align.LEFT):
        self.title = title
        self.width = width
        self.align = align

ColumnInfo = namedtuple('ColumnInfo', ['x', 'width'])

class TablePrinter:
    def __init__(self, out, attr, columns):
        self.out = out
        self.attr = attr
        self.columns = columns

    def format_row(self, rec):
        return ' '.join((entry[0] + pad(str(entry[1]), col.width, col.align) + self.attr.close(entry[0]) for entry, col in zip(rec, self.columns)))

    def print_row(self, rec):
        self.out.write(f'{self.format_row(rec)}\n')

    def print_header(self, hdr_attr):
        titles = [(hdr_attr, t.title) for t in self.columns]
        self.out.write(f'{self.format_row(titles)}\n')

    def column_info(self, idx):
        x = 0
        for i in range(0, idx):
            x += self.columns[i].width + 1
        return ColumnInfo(x=x, width=self.columns[idx].width)
