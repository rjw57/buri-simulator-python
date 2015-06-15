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

from contextlib import contextmanager
from itertools import cycle
import logging
import sys

from docopt import docopt
from past.builtins import basestring # pylint: disable=redefined-builtin

from burisim.lib6502 import M6502
from burisim.acia import ACIA

_LOGGER = logging.getLogger(__name__)

class MachineError(Exception):
    pass

class ReadOnlyMemoryError(MachineError):
    """Raised when code had attempter to write to read-only memory."""
    def __init__(self, address, value):
        self.address = address
        self.value = value
        super(ReadOnlyMemoryError, self).__init__(
            'Illegal attempt to write ${0.value:02X} to ${0.address:04X}'.format(self)
        )

class BuriSim(object):
    ROM_SIZE = 0x2000 # 8K
    ROM_RANGE = 0x10000 - ROM_SIZE, 0x10000
    ACIA1_SIZE = 0x4
    ACIA1_RANGE = 0xDFFC, 0xDFFC + ACIA1_SIZE

    def __init__(self):
        # Create our processor
        self.mpu = M6502()

        # Register ROM as read-only
        def raise_rom_exception(addr, value):
            raise ReadOnlyMemoryError(addr + BuriSim.ROM_RANGE[0], value)
        self.mpu.register_write_handler(
            BuriSim.ROM_RANGE[0], BuriSim.ROM_SIZE, raise_rom_exception
        )

        # Do not trace execution
        self.tracing = False

        # Create I/O devices
        self.acia1 = ACIA()
        self.mpu.register_read_handler(
            BuriSim.ACIA1_RANGE[0], BuriSim.ACIA1_SIZE, self.acia1.read_reg
        )
        self.mpu.register_write_handler(
            BuriSim.ACIA1_RANGE[0], BuriSim.ACIA1_SIZE, self.acia1.write_reg
        )

        # Reset the computer
        self.reset()

    def load_rom(self, fobj_or_string):
        """Load a ROM image from the passed file object or filename-string. The
        ROM is truncated or repeated as necessary to fill the buri ROM region.

        """
        if isinstance(fobj_or_string, basestring):
            with open(fobj_or_string, 'rb') as fobj:
                self.load_rom_bytes(fobj.read())
        else:
            self.load_rom_bytes(fobj_or_string.read())

    def load_ram(self, fobj_or_string, addr):
        """Load a RAM image from the passed file object or filename-string.

        """
        if isinstance(fobj_or_string, basestring):
            with open(fobj_or_string, 'rb') as fobj:
                self.load_ram_bytes(fobj.read(), addr)
        else:
            self.load_ram_bytes(fobj_or_string.read(), addr)

    def load_rom_bytes(self, rom_bytes):
        """Load a ROM image from the passed bytes object. The ROM is truncated
        or repeated as necessary to fill the buri ROM region.

        """
        _LOGGER.info(
            'loading %s bytes from ROM image of %s bytes',
            BuriSim.ROM_RANGE[1] - BuriSim.ROM_RANGE[0], len(rom_bytes)
        )

        # Copy ROM from 0xC000 to 0xFFFF. Loop if necessary.
        for addr, val in zip(range(*BuriSim.ROM_RANGE), cycle(rom_bytes)):
            self.mpu.memory[addr] = val

    def load_ram_bytes(self, ram_bytes, addr):
        """Load a RAM image from the passed bytes object.

        """
        _LOGGER.info('loading RAM image of %s bytes', len(ram_bytes))

        for off, val in enumerate(ram_bytes):
            self.mpu.memory[addr + off] = val

    def reset(self):
        """Perform a hardware reset."""
        # Reset hardware
        self.acia1.hw_reset()

        # Reset MPU
        self.mpu.reset()

    def step(self, ticks):
        """Single-cycle the machine for a specified number of clock ticks."""
        # Poll hardware (inefficient but simple)
        self.acia1.poll()

        # Look for IRQs
        if self.acia1.irq:
            self.mpu.irq()

        # TODO: tracing
        self.mpu.run(ticks)

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
    while True:
        sim.step(int(1e2))

if __name__ == '__main__':
    main()
