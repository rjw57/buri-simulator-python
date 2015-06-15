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
import sys
import time

from docopt import docopt
from PySide import QtCore

from burisim.acia import ACIA
from burisim.sim import BuriSim

_LOGGER = logging.getLogger(__name__)

# Dirty trick to *REALLY KILL* on Ctrl-C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

def main():
    opts = docopt(__doc__)
    logging.basicConfig(
        level=logging.WARN if opts['--quiet'] else logging.INFO,
        stream=sys.stderr, format='%(name)s: %(message)s'
    )

    # Create simulator
    sim = BuriSim()
    sim.tracing = opts['--trace']

    # Create serial port
    from serial import serial_for_url
    sim.acia1.connect_to_file(opts['--serial'])

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    # Reset the simulator
    sim.reset()

    # Application loop
    app = QtCore.QCoreApplication(sys.argv)
    ticks_per_step = 10000
    s = dict(
        last_report=time.time(),
        total_ticks=0,
    )
    def tick():
        sim.acia1.poll()
        then = time.time()
        sim.step(ticks_per_step)
        s['total_ticks'] += ticks_per_step
        now = time.time()

        if s['last_report'] + 10 < now:
            print('Running at {0:d}Hz'.format(
                int(s['total_ticks'] / (now - s['last_report']))
            ))
            s['total_ticks'] = 0
            s['last_report'] = now

        next_at = max(0, 1000*((ticks_per_step/2e6)-(now-then)))
        QtCore.QTimer.singleShot(next_at, tick)
    tick()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
