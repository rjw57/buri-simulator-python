"""
Simulate the buri microcomputer.

Usage:
    burisim (-h | --help)
    burisim [options] [--serial URL] [--load FILE] <rom>

Options:
    -h, --help          Show a brief usage summary.
    -q, --quiet         Decrease verbosity.

    --trace             Trace CPU execution.

Hardware options:
    --serial URL        Connect ACIA1 to this serial port. [default: loop://]
    --load FILE         Pre-load FILE at location 0x5000 in RAM.

    See http://pyserial.sourceforge.net/pyserial_api.html#urls for a discussion
    of possible serial connection URLs.

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

_LOGGER = logging.getLogger(__name__)

def create_sim():
    opts = docopt(__doc__)
    logging.basicConfig(
        level=logging.WARN if opts['--quiet'] else logging.INFO,
        stream=sys.stderr, format='%(name)s: %(message)s'
    )

    # Create simulator
    sim = BuriSim()
    sim.tracing = opts['--trace']

    # Create serial port
    sim.acia1.connect_to_file(opts['--serial'])

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    # Reset the simulator
    sim.reset()

    return sim

class MemoryView(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(MemoryView, self).__init__(*args, **kwargs)
        self.simulator = None
        self.page = 0
        self._init_ui()

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
            start = 0x100 + self.page
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
            return '{0:04X}  {1:48}  |{2:16}|'.format(offset, hexrepr, asciirepr)

        dump = ''.join((
            '      {0}  {1}\n'.format(
                ' '.join('{0:02X}'.format(x) for x in range(0, 8)),
                ' '.join('{0:02X}'.format(x) for x in range(8, 16)),
            ),
            '\n'.join(render_line(o, c) for o, c in mem_contents()),
        ))
        self._te.setHtml('<pre><code>' + cgi.escape(dump) + '</code></pre>')
        self.adjustSize()

class SimulatorUI(object):
    def __init__(self):
        # Retrieve the application instance
        app = QtCore.QCoreApplication.instance()
        assert app is not None

        # Create the main simulator and attach it to application quit events.
        self.sim = create_sim()

        # Start simulating once event loop is running
        QtCore.QTimer.singleShot(0, self.sim.start)

        # Stop simulating when app is quitting
        app.aboutToQuit.connect(self.sim.stop)

        # Create memory view
        self._mv = MemoryView()
        self._mv.simulator = self.sim
        self._mv.adjustSize()
        self._mv.show()

def main():
    app = QtGui.QApplication(sys.argv)

    # Create the sim UI
    ui = SimulatorUI()

    # Wire up Ctrl-C to quit app.
    def interrupt(*args):
        print('received interrupt signal, exitting...')
        app.quit()
    signal.signal(signal.SIGINT, interrupt)

    # Start the application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
