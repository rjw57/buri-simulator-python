import urwid

HORIZ_BAR = '\N{BOX DRAWINGS LIGHT HORIZONTAL}'
VERT_BAR = '\N{BOX DRAWINGS LIGHT VERTICAL}'
CROSS_BAR = '\N{BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL}'

class HexMemoryView(urwid.WidgetWrap):
    _sizing = frozenset(['fixed'])

    def __init__(self, sim, page=0):
        self.sim = sim
        self._page = page
        self._txt = urwid.Text('')
        urwid.WidgetWrap.__init__(self, urwid.Pile([
            ('pack', urwid.Columns([self._txt]))
        ]))
        self.tick()

    def pack(self, size, focus=False):
        ideal = (3*16, 16)
        if size == ():
            return size
        return ideal[:len(size)]

    def tick(self):
        addr = self._page * 0x100

        rows = []
        mem = self.sim.mpu.memory
        for high_nybble in range(0x10):
            row_addr = addr + high_nybble * 0x10
            rows.append(''.join([
                ' '.join(
                    '{:02X}'.format(mem[row_addr + v])
                    for v in range(0x8)
                ), '  ',
                ' '.join(
                    '{:02X}'.format(mem[row_addr + v])
                    for v in range(0x8, 0x10)
                ),
            ]))
        self._txt.set_text(('memory hex', '\n'.join(rows)))

class ASCIIMemoryView(urwid.WidgetWrap):
    _sizing = frozenset(['fixed'])

    def __init__(self, sim, page=0):
        self.sim = sim
        self._page = page
        self._txt = urwid.Text('')
        urwid.WidgetWrap.__init__(self, urwid.Pile([
            ('pack', urwid.Columns([self._txt]))
        ]))
        self.tick()

    def pack(self, size, focus=False):
        ideal = (16, 16)
        if size == ():
            return size
        return ideal[:len(size)]

    def tick(self):
        def is_print(b):
            return b >= 32 and b < 127

        addr = self._page * 0x100
        rows = []
        mem = self.sim.mpu.memory
        for high_nybble in range(0x10):
            row_addr = addr + high_nybble * 0x10
            row_bytes = mem[row_addr:row_addr+0x10]
            rows.extend([
                ('memory ascii', chr(b)) if is_print(b) else ('memory replace', '.')
                for b in row_bytes
            ])
            if high_nybble != 0xf:
                rows.append('\n')
        self._txt.set_text(rows)

class PageView(urwid.WidgetWrap):
    def __init__(self, sim, page=0):
        self.sim = sim
        self._page = page
        self._txt = urwid.Text('')
        urwid.WidgetWrap.__init__(self, urwid.Pile([
            ('pack', urwid.Columns([self._txt]))
        ]))
        self.tick()

    def tick(self):
        rows = []
        addr = self._page * 0x100
        for high_nybble in range(0x10):
            hex_row, ascii_row = [], []
            row_addr = addr + high_nybble * 0x10
            row_text = ['{:04X} '.format(row_addr), VERT_BAR, ' ']
            for low_nybble in range(0x10):
                v = self.sim.mpu.memory[row_addr + low_nybble]
                hex_row.append('{:02X} '.format(v))
                if low_nybble == 0x7:
                    hex_row.append(' ')
                if v >= 0x20 and v < 127:
                    ascii_row.append(chr(v))
                else:
                    ascii_row.append('.')
            rows.append('{}|{}|'.format(
                ''.join(hex_row), ''.join(ascii_row))
            )
        self._txt.set_text('\n'.join(rows))

