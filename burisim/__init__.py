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

from burisim.acia import ACIA
from burisim.sim import BuriSim

_LOGGER = logging.getLogger(__name__)

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
    sp = serial_for_url(opts['--serial'])
    sim.acia1.connect_to_serial(sp)

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    # Step
    sim.reset()

    then = time.time()
    sim.step(int(2e6))
    now = time.time()

    have_reported = False
    start_time = time.time()
    total_ticks = 0
    ticks_per_step = 10
    while True:
        then = time.time()
        sim.acia1.poll()
        sim.step(ticks_per_step)
        now = time.time()
        time.sleep(max(0, (ticks_per_step/2e6)-(now-then)))
        total_ticks += ticks_per_step
        if not have_reported and (now - start_time) > 2:
            print(
                'Running at {0}Hz'.format(
                    int(total_ticks / (now-start_time))
                )
            )
            have_reported = True

if __name__ == '__main__':
    main()
