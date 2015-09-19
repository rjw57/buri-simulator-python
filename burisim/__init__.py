"""
Simulate the buri microcomputer.

Usage:
    burisim (-h | --help)
    burisim [options] [--serial URL] [--load FILE] <rom>

Options:
    -h, --help          Show a brief usage summary.
    -q, --quiet         Decrease verbosity.

    --ui=UI             Select UI. One of qt, tui. [default: tui]

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

from burisim.sim import BuriSim
from burisim.tui import MainLoop as TuiMainLoop
from burisim.qt import MainLoop as QtMainLoop

_LOGGER = logging.getLogger(__name__)

def create_sim(opts):
    # Create simulator
    sim = BuriSim()

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

    # Create the main simulator
    sim = create_sim(opts)

    # Create main loop
    if opts['--ui'] == 'tui':
        loop = TuiMainLoop(sim)
    elif opts['--ui'] == 'qt':
        loop = QtMainLoop(sim)
    else:
        raise RuntimeError('Unknown UI: %s' % (opts['--ui'],))

    if opts['--serial'] is not None:
        loop.attach_serial(opts['--serial'])

    # Start the application
    sys.exit(loop.run())

if __name__ == '__main__':
    main()
