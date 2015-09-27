import urwid

HORIZ_BAR = '\N{BOX DRAWINGS LIGHT HORIZONTAL}'
VERT_BAR = '\N{BOX DRAWINGS LIGHT VERTICAL}'
CROSS_BAR = '\N{BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL}'

class _MemoryViewMixin(object):
    def __init__(self, sim, page=0):
        self.sim = sim
        self._page = page
        self._cached_mem = self._read_mem()

    def _read_mem(self, page=None):
        page = page if page is not None else self._page
        addr = page * 0x100
        return bytearray(self.sim.mpu.memory[addr:addr+0x100])

    def get_page(self):
        return self._page

    def set_page(self, pg):
        if pg == self._page:
            return
        self._page = pg
        self.tick()

    def tick(self):
        new_mem = self._read_mem()
        if new_mem == self._cached_mem:#
            return
        self._cached_mem = new_mem
        self._mem_changed(self._cached_mem)

    def _mem_changed(self, mem):
        raise NotImplementedError()

class HexMemoryView(urwid.WidgetWrap, _MemoryViewMixin):
    _sizing = frozenset(['fixed'])

    def __init__(self, sim, page=0):
        _MemoryViewMixin.__init__(self, sim, page)
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

    def _mem_changed(self, mem):
        rows = []
        for high_nybble in range(0x10):
            row_addr = high_nybble * 0x10
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

class ASCIIMemoryView(urwid.WidgetWrap, _MemoryViewMixin):
    _sizing = frozenset(['fixed'])

    def __init__(self, sim, page=0):
        _MemoryViewMixin.__init__(self, sim, page)
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

    def _mem_changed(self, mem):
        def is_print(b):
            return b >= 32 and b < 127

        rows = []
        for high_nybble in range(0x10):
            row_addr = high_nybble * 0x10
            row_bytes = mem[row_addr:row_addr+0x10]
            rows.extend([
                ('memory ascii', chr(b)) \
                    if is_print(b) else ('memory replace', '.')
                for b in row_bytes
            ])
            if high_nybble != 0xf:
                rows.append('\n')
        self._txt.set_text(rows)

class MemoryExplorer(urwid.WidgetWrap, _MemoryViewMixin):
    def __init__(self, sim):
        _MemoryViewMixin.__init__(self, sim, 0)
        self._hmv = HexMemoryView(self.sim)
        self._amv = ASCIIMemoryView(self.sim)
        self._left_heading = urwid.Text('')

        self.set_page(0)

        pg = self.get_page()
        self._pg_edit = urwid.Edit(
            caption='Page: 0x', edit_text='{0:02X}'.format(pg)
        )
        self._bk_edit = urwid.Edit(
            caption='Bank: 0x', edit_text='00', align='right'
        )

        w = urwid.Pile([
            ('pack', urwid.Columns([
                ('weight', 1, self._pg_edit),
                ('weight', 1, self._bk_edit),
            ], dividechars=1)),
            ('pack', urwid.Columns([
                ('pack', urwid.Text([
                    '    ',
                    ('memory divider', VERT_BAR),
                    (
                        'memory header',
                        ' '.join('{:02X}'.format(v) for v in range(0x8))
                    ),
                    '  ',
                    (
                        'memory header',
                        ' '.join('{:02X}'.format(v) for v in range(0x8, 0x10))
                    ),
                ])),
                (19, urwid.Divider(div_char=' ')),
            ])),
            ('pack', urwid.Columns([
                (4, urwid.AttrMap(
                    urwid.Divider(div_char=HORIZ_BAR),
                    'memory divider'
                )),
                (1, urwid.AttrMap(urwid.Text(CROSS_BAR), 'memory divider')),
                (16*4 + 3, urwid.AttrMap(
                    urwid.Divider(div_char=HORIZ_BAR),
                    'memory divider'
                )),
            ])),
            ('pack', urwid.Columns([
                (4, urwid.AttrMap(self._left_heading, 'memory header')),
                (1, urwid.AttrMap(urwid.SolidFill(VERT_BAR), 'memory divider')),
                ('pack', self._hmv),
                (1, urwid.SolidFill(' ')),
                (1, urwid.AttrMap(urwid.SolidFill(VERT_BAR), 'memory sep')),
                ('pack', self._amv),
                (1, urwid.AttrMap(urwid.SolidFill(VERT_BAR), 'memory sep')),
            ], box_columns=[1, 3, 4, 6])),
        ])

        w = urwid.AttrMap(w, 'memory')

        w = urwid.Padding(w, align='center', width=16*4 + 3 + 5)

        urwid.WidgetWrap.__init__(self, w)

        urwid.connect_signal(self._pg_edit, 'change', self._pg_edit_change)

    def _pg_edit_change(self, _, txt):
        try:
            pg = int(txt, 16)
        except ValueError:
            # ignore invalid values
            return

        # ignore out of range values
        if pg < 0 or pg >= 0x100:
            return

        new_text = '{0:02X}'.format(pg)
        if txt != new_text:
            self._pg_edit.set_edit_text(new_text)
        self.set_page(pg)

    def set_page(self, pg):
        super(MemoryExplorer, self).set_page(pg)
        self._update_left_heading()
        for w in (self._hmv, self._amv):
            w.set_page(pg)

    def _update_left_heading(self):
        p = self.get_page()
        self._left_heading.set_text('\n'.join(
            '{0:04X}'.format(v) for v in range(p*0x100, (p+1)*0x100, 0x10)
        ))

    def tick(self):
        super(MemoryExplorer, self).tick()
        for w in (self._hmv, self._amv):
            w.tick()

    def _mem_changed(self, mem):
        pass
