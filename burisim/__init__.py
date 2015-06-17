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

import logging
import signal
import sys
import time

from docopt import docopt
from PySide import QtCore

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

def main():
    app = QtCore.QCoreApplication(sys.argv)

    # Create the sim UI
    ui = SimulatorUI()

    # Wire up Ctrl-C to quit app.
    def interrupt(*args):
        print('received interrupt signal, exitting...')
        app.quit()
    signal.signal(signal.SIGINT, interrupt)

    # Start the application
    rv = app.exec_()
    sys.exit(rv)

if __name__ == '__main__':
    main()
