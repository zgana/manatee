# tablegen.py


from __future__ import print_function

__doc__ = """Generate text tables in various formats."""

from itertools import izip
import numpy as np


class Column (object):

    """Specify a Table column."""

    def __init__ (self, heading='', align='right', fmt='', header=False):
        """Construct a Column.
        
        `heading`: the heading of the column.
        `align`: "left", "center", or "right" (or "l", "c" or "r").
        `fmt`: the string conversion format to use.
        `header`: whether this is a header column
        """
        self.heading = heading
        assert align in ('left', 'center', 'right', 'l', 'c', 'r')
        self.align = align
        self.fmt = fmt
        self.header = header

class Row (object):

    """Specify row data for a Table."""

    def __init__ (self, *contents, **kwargs):
        """Contruct a Row.
        
        `contents`: the row content data.  Can be one list, one numpy array, or
        any number of individual objects.

        Keyword arguments:
        `span`: if an alignment is specified (see Column.__init__), this row
        contains one cell that spans the table width.
        """
        if isinstance (contents[0], list):
            self.contents = contents[0][:]
        elif isinstance (contents[0], np.ndarray):
            self.contents = list (contents[0])
        else:
            self.contents = contents[:]
        self.span = kwargs.get ('span', '')

class Table (object):

    """Generate a table."""

    span_marker = '!@#SPAN'

    def __init__ (self, *columns):
        self.columns = columns[:]
        self.rows = []

    def __str__ (self):
        """Return a string with the ASCII version of the table."""
        return self.to_string ('ascii')

    def add_row (self, *args, **kwargs):
        """Add a row to the table.
        
        `args`: if a Row object, add the row.  If not, construct a row from the
        args and kwargs.
        """
        if isinstance (args[0], Row):
            row = args[0]
        else:
            row = Row (*args, **kwargs)
        self.rows.append (row)

    def to_string (self, mode='ascii', **kwargs):
        """Return a string representation of the table according to `mode`.

        `mode`: 'ascii' or 'latex'.

        'ascii' keyword arguments:
            `width`: the width of the table (output will be centered).
        """
        if mode == 'ascii':
            return self.to_string_ascii (**kwargs)
        elif mode == 'latex':
            return self.to_string_latex (**kwargs)
        elif mode == 'html':
            return self.to_string_html (**kwargs)
        else:
            raise ValueError ('mode "{0}" is not implemented'.format (mode))

    def to_string_ascii (self, width=None):
        """Return an ASCII representation of the table."""
        all_cells = self._get_all_cells ()
        column_widths = []
        for j, column in enumerate (self.columns):
            column_cells = all_cells[:,j]
            span_idx = np.array (map (self.is_span, column_cells))
            column_widths.append (np.max (map (len, column_cells[~span_idx])))
        table_width = np.sum (column_widths) + 2 * (len (column_widths) - 1)
        lines = []
        for row in all_cells:
            if row[0][:len (self.span_marker)] == self.span_marker:
                cell_text = row[0][len (self.span_marker):].center (table_width)
            else:
                cells = []
                for content, w, column \
                        in izip (row, column_widths, self.columns):
                    if column.align[0] == 'l':
                        cells.append (content.ljust (w))
                    elif column.align[0] == 'c':
                        cells.append (content.center (w))
                    elif column.align[0] == 'r':
                        cells.append (content.rjust (w))
                cell_text = '  '.join (cells)
            if width:
                lines.append (cell_text.center (width))
            else:
                lines.append (cell_text)
        out = '\n'.join (lines)
        return out

    def to_string_html (self):
        """Return html code for the table."""
        all_cells = self._get_all_cells ()
        lines = []
        def addline (line):
            def is_opener (line):
                openers = [
                        '<table',
                        '<tr',
                        ]
                for opener in openers:
                    if line.startswith (opener):
                        return True
                return False

            if line.startswith ('</'):
                addline.indent -= 2
            lines.append ((' ' * addline.indent) + line)
            if is_opener (line):
                addline.indent += 2
        
        addline.indent = 0
        addline ('<table>')
        addline ('<tr>')
        for cell in all_cells[0]:
            addline ('<th>{0}</th>'.format (cell))
        addline ('</tr>')
        for row_cells in all_cells[1:]:
            addline ('<tr>')
            for column, cell in izip (self.columns, row_cells):
                tag = 'th' if column.header else 'td'
                addline ('<{0}>{1}</{0}>'.format (tag, cell))
            addline ('</tr>')
        addline ('</table>')
        return '\n'.join (lines)

    def to_string_latex (self):
        """Return LaTeX code for the table."""
        all_cells = self._get_all_cells ()
        lines = []
        def addline (line):
            if line.startswith (r'\end'):
                addline.indent -= 2
            lines.append ((' ' * addline.indent) + line)
            if line.startswith (r'\begin'):
                addline.indent += 2

        addline.indent = 0
        addline (r'\begin{table}')
        addline (r'\begin{center}')
        colspec = ''.join (['{']
                + [' {0}'.format (column.align[0]) for column in self.columns]
                + [' }'])
        addline (r'\begin{tabular}' + colspec)
        addline (r'\toprule')
        addline (' & '.join (all_cells[0]) + r' \\')
        addline (r'\midrule')
        for row in all_cells[1:]:
            addline (' & '.join (row) + r' \\')
        addline (r'\bottomrule')
        addline (r'\end{tabular}')
        addline (r'\end{center}')
        addline (r'\end{table}')
        return '\n'.join (lines)

    def _get_all_cells (self):
        all_cells = []
        header_cells = []
        for column in self.columns:
            header_cells.append (column.heading)
        all_cells.append (header_cells)
        for row in self.rows:
            row_cells = []
            if row.span:
                row_cells.append ('{0}{1}'.format (
                    self.span_marker, ''.join (row.contents)))
                for column in self.columns[1:]:
                    row_cells.append ('')
            else:
                for i, column in enumerate (self.columns):
                    if i < len (row.contents):
                        contents = row.contents[i]
                    else:
                        contents = None
                    if contents is None:
                        row_cells.append ('-')
                    else:
                        row_cells.append (format (contents, column.fmt))
            all_cells.append (row_cells)
        all_cells = np.array (all_cells)
        return all_cells

    @staticmethod
    def is_span (cell):
        return cell[:len (Table.span_marker)] == Table.span_marker

def test_table ():
    test_data = np.array ([np.random.rand (5) for i in xrange (4)])
    test_table = Table (Column ('1'),
            Column ('2'),
            Column ('3'),
            Column ('4'),
            Column ('5') )
    for nums in test_data:
        test_table.add_row (*nums)
    return test_table
