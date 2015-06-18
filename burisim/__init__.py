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
    --serial URL        Connect ACIA1 to this serial port.
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
import struct
import sys

from docopt import docopt
from PySide import QtCore, QtGui

from burisim.sim import BuriSim
from burisim.ui import create_ui

_LOGGER = logging.getLogger(__name__)

def create_sim(opts):
    # Create simulator
    sim = BuriSim()

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    if opts['--serial'] is not None:
        attach_file_to_acia(sim.acia1, opts['--serial'])

    # Reset the simulator
    sim.reset()

    return sim

def attach_file_to_acia(acia, filename):
    sp = QtCore.QFile(filename)
    ok = sp.open(QtCore.QIODevice.ReadWrite | QtCore.QIODevice.Unbuffered)
    if not ok:
        raise ValueError('failed to open %s' % filename)

    def have_input():
        bs = sp.read(1)
        acia.receiveByte(struct.unpack('B', bs[0])[0])
    sn = QtCore.QSocketNotifier(sp.handle(), QtCore.QSocketNotifier.Read)
    sn.activated.connect(have_input)

    @QtCore.Slot(int)
    def have_output(v):
        sp.putChar(v)
    acia.transmitByte.connect(have_output)

    # HACK: stop sp and sn being garbage collected
    acia._stashed_notifier = (sp, sn)

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
        ui = create_ui(sim)

    # Start the application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
