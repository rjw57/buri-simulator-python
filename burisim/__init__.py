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

from docopt import docopt
from PySide import QtCore, QtGui

from burisim.sim import BuriSim
from burisim.ui import create_ui

_LOGGER = logging.getLogger(__name__)

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
        ui = create_ui(sim)

    # Start the application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
