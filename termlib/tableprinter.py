from collections import namedtuple

from . import textattr

Align=textattr.Pad

class Column:
    def __init__(self, title, width, align=Align.LEFT, attr=None, pad_ch=' '):
        self.title = title
        self.width = width
        self.align = align
        self.attr = attr
        self.pad_ch = pad_ch

ColumnInfo = namedtuple('ColumnInfo', ['x', 'width'])
ColData = namedtuple('Column', ['ncol', 'attr', 'val'], defaults=(1, None, ()))

class TablePrinter:
    def __init__(self, out, attr, columns, colsep=' '):
        self.out = out
        self.attr = attr
        self.columns = columns
        self.colsep = colsep

    def format_row(self, recs):
        '''
        Format a row. Supports values spanning multiple columns.
        '''
        out = []
        icol = 0
        for ncol, entry_attr, entry_val in recs:
            # use default attributes from first column
            main_col = self.columns[icol]
            # compute width to use
            width = -1
            for col in self.columns[icol:icol+ncol]:
                if col.width is None: # Unlimited width
                    width = None
                    break
                width += col.width + 1

            # first apply global table attribute, then per-column attribute, then passed-in column attribute
            out.append(textattr.render(
                entry_val,
                attr=self.attr.clone().apply(main_col.attr).apply(entry_attr),
                width=width,
                pad=main_col.align,
                pad_ch=main_col.pad_ch))

            icol += ncol

        return textattr.render(self.colsep).join(out)

    def print_row(self, rec):
        self.out.write(f'{self.format_row(rec)}\n')

    def print_header(self, hdr_attr=textattr.TextAttr()):
        titles = [(1, hdr_attr, t.title) for t in self.columns]
        self.out.write(f'{self.format_row(titles)}\n')

    def column_info(self, idx):
        x = 0
        for i in range(0, idx):
            x += self.columns[i].width + 1
        return ColumnInfo(x=x, width=self.columns[idx].width)

    @property
    def total_width(self):
        return sum(col.width for col in self.columns) + len(self.columns) - 1
