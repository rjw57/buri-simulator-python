"""
Simulate the buri microcomputer.

Usage:
    burisim (-h | --help)
    burisim [options] [--serial URL] [--load FILE] <rom>

Options:
    -h, --help          Show a brief usage summary.
    -q, --quiet         Decrease verbosity.

    --no-gui            Don't create GUI.

Hardware options:
    --serial URL        Connect ACIA1 to this serial port. [default: loop://]
    --load FILE         Pre-load FILE at location 0x5000 in RAM.

"""
# Make py2 like py3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip
)
from past.builtins import basestring # pylint: disable=redefined-builtin

import cgi
import logging
import signal
import sys
import time

from docopt import docopt
from PySide import QtCore, QtGui

from burisim.sim import BuriSim
from burisim.hw.hd44780 import HD44780View

_LOGGER = logging.getLogger(__name__)

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

    def _init_ui(self):
        l = QtGui.QVBoxLayout()
        self.setLayout(l)
        l.setContentsMargins(0,0,0,0)

        te = QtGui.QTextEdit()
        te.setReadOnly(True)
        te.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        te.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        te.setFrameStyle(QtGui.QFrame.NoFrame)
        l.addWidget(te)
        self._te = te

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_mem)
        self._refresh_timer.start(66) # run at approx ~15Hz

    def sizeHint(self):
        return self._te.document().size().toSize()

    def _refresh_mem(self):
        if self.simulator is None:
            return

        def mem_contents():
            m = self.simulator.memory
            start = 0x100 + self._page*0x100
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
            return '{0:04X}  {1:48}  |{2:16}|'.format(
                self._page*0x100 + offset, hexrepr, asciirepr
            )

        dump = ''.join((
            '      {0}  {1}\n'.format(
                ' '.join('{0:02X}'.format(x) for x in range(0, 8)),
                ' '.join('{0:02X}'.format(x) for x in range(8, 16)),
            ),
            '\n'.join(render_line(o, c) for o, c in mem_contents()),
        ))
        self._te.setHtml('<pre><code>' + cgi.escape(dump) + '</code></pre>')

class SimulatorUI(object):
    def __init__(self, sim):
        # Assign simulator
        self.sim = sim

        # Create memory view
        self._mv = QtGui.QWidget()
        l = QtGui.QVBoxLayout()
        self._mv.setLayout(l)

        mv = MemoryView()
        mv.simulator = self.sim
        l.addWidget(mv)

        sp = QtGui.QSpinBox()
        sp.setMinimum(0)
        sp.setMaximum(0xff)
        sp.valueChanged.connect(lambda v: mv.setPage(v))
        l.addWidget(sp)

        self._mv.adjustSize()
        self._mv.show()
        self._mv.setWindowTitle("Memory")

        # Create lcd view
        self._lcd = HD44780View()
        self._lcd.display = self.sim.display
        self._lcd.show()
        self._lcd.setWindowTitle("Display")

def create_sim(opts):
    # Create simulator
    sim = BuriSim()

    # Create serial port
    sim.acia1.connect_to_file(opts['--serial'])

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    # Reset the simulator
    sim.reset()

    return sim

def main():
    opts = docopt(__doc__)
    logging.basicConfig(
        level=logging.WARN if opts['--quiet'] else logging.INFO,
        stream=sys.stderr, format='%(name)s: %(message)s'
    )

    # Create GUI or non-GUI application as appropriate
    if opts['--no-gui']:
        app = QtCore.QCoreApplication(sys.argv)
    else:
        app = QtGui.QApplication(sys.argv)

    # Wire up Ctrl-C to quit app.
    def interrupt(*args):
        print('received interrupt signal, exitting...')
        app.quit()
    signal.signal(signal.SIGINT, interrupt)

    # Create the main simulator and attach it to application quit events.
    sim = create_sim(opts)

    # Start simulating once event loop is running
    QtCore.QTimer.singleShot(0, sim.start)

    # Stop simulating when app is quitting
    app.aboutToQuit.connect(sim.stop)

    # Create the sim UI if requested
    if not opts['--no-gui']:
        ui = SimulatorUI(sim)

    # Start the application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
