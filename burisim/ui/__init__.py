# Make py2 like py3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip
)

import cgi

from PySide import QtCore, QtGui

from .display import HD44780View, TerminalView

class HexSpinBox(QtGui.QSpinBox):
    def __init__(self, *args, **kwargs):
        super(HexSpinBox, self).__init__(*args, **kwargs)
        self._padding = None

    def padding(self):
        return self._padding

    def setPadding(self, p):
        self._padding = int(p)

    def textFromValue(self, v):
        if self._padding is not None and self._padding > 0:
            f = '{0:0' + str(self._padding) + 'X}'
            return f.format(v)
        return ('{0:X}').format(v)

    def valueFromText(self, t):
        return int(t, 16)

    def validate(self, t, pos):
        if t.startswith(self.prefix()):
            t = t[len(self.prefix()):]
        if t.endswith(self.suffix()) and len(self.suffix()) > 0:
            t = t[:-len(self.suffix())]
        if t == '':
            return QtGui.QValidator.Intermediate
        try:
            int(t, 16)
            return QtGui.QValidator.Acceptable
        except ValueError:
            return QtGui.QValidator.Invalid

class MemoryView(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(MemoryView, self).__init__(*args, **kwargs)
        self.simulator = None
        self._page = 0
        self._init_ui()

    def page(self):
        return self._page

    def setPage(self, v):
        self._page = v
        self._refresh_mem()

    @QtCore.Slot(int)
    def _spinValueChanged(self, v):
        self.setPage(v)

    def _init_ui(self):
        l = QtGui.QVBoxLayout()
        self.setLayout(l)
        l.setSpacing(5)
        l.setContentsMargins(0, 0, 0, 0)

        te = QtGui.QTextEdit()
        te.setReadOnly(True)
        te.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        te.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        te.setFrameStyle(QtGui.QFrame.NoFrame)
        l.addWidget(te)
        self._te = te

        h = QtGui.QHBoxLayout()
        h.setSpacing(5)
        h.addWidget(QtGui.QLabel("Page:"))
        sb = HexSpinBox()
        sb.setPrefix('0x')
        sb.setPadding(2)
        sb.setRange(0, 0xff)
        sb.setSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding,
            QtGui.QSizePolicy.Preferred,
        )
        sb.valueChanged.connect(self._spinValueChanged)
        h.addWidget(sb)
        l.addLayout(h)

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_mem)
        self._refresh_timer.start(66) # run at approx ~15Hz

    def _refresh_mem(self):
        if self.simulator is None:
            return

        def mem_contents():
            m = self.simulator.memory
            start = 0x100 * self._page
            for line_offset in range(0x000, 0x100, 0x010):
                contents = m[start + line_offset:start + line_offset+0x010]
                yield line_offset, contents
            raise StopIteration()

        def render_line(offset, contents):
            hexrepr = '  '.join(
                ' '.join('{0:02X}'.format(b) for b in contents[o:o+8])
                for o in range(0, len(contents), 8)
            )
            asciirepr = ''.join(chr(b) if b>=32 and b<127 else '.' for b  in contents)
            return '<strong><code>{0:04X}</code></strong><code>  {1:48}  |{2:16}|</code>'.format(
                self._page*0x100 + offset, hexrepr, cgi.escape(asciirepr)
            )

        self._te.setHtml(''.join((
            '<pre>',
            ''.join((
                '<strong><code>',
                '      {0}  {1}\n'.format(
                    ' '.join('{0:02X}'.format(x) for x in range(0, 8)),
                    ' '.join('{0:02X}'.format(x) for x in range(8, 16)),
                ),
                '</code></strong>',
            )),
            '\n'.join(render_line(o, c) for o, c in mem_contents()),
            '</pre>',
        )))

        self._te.setMinimumSize(self._te.document().size().toSize())

def create_ui(sim):
    mw = QtGui.QMainWindow()

    tb = mw.addToolBar("Simulator")

    a = QtGui.QAction("Reset", mw)
    a.triggered.connect(sim.reset)
    tb.addAction(a)

    v = MemoryView()
    v.simulator = sim
    dw = QtGui.QDockWidget("Memory monitor")
    dw.setWidget(v)
    mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw)

    v = HD44780View()
    v.display = sim.display
    dw = QtGui.QDockWidget("Display")
    dw.setWidget(v)
    mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dw)

    v = TerminalView()
    sim.acia1.register_listener(v.receiveByte)
    dw = QtGui.QDockWidget("Serial console")
    dw.setWidget(v)
    mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dw)

    mw.show()
    return mw

