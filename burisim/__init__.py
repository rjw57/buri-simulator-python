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

from contextlib import contextmanager
from itertools import cycle
import logging
import sys

from docopt import docopt

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
    ACIA1_RANGE = 0xDFFC, 0xDFFF

    def __init__(self):
        self.tracing = False

        # Behaviour flags
        self._raise_on_rom_write = True

        # Create I/O devices
        # self.acia1 = ACIA()

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
        with self.writable_rom():
            for addr, val in zip(range(*BuriSim.ROM_RANGE), cycle(rom_bytes)):
                self.mem[addr] = val

    def load_ram_bytes(self, ram_bytes, addr):
        """Load a RAM image from the passed bytes object.

        """
        _LOGGER.info('loading RAM image of %s bytes', len(ram_bytes))

        for off, val in enumerate(ram_bytes):
            self.mem[addr + off] = val

    def reset(self):
        """Perform a hardware reset."""
        # Reset hardware
        self.acia1.hw_reset()

        # Reset MPU
        self.mpu.reset()

        # Read reset-vector
        self.mpu.pc = self.mpu.WordAt(MPU.RESET)

    def step(self):
        """Single-step the machine."""
        # Poll hardware (inefficient but simple)
        self.acia1.poll()

        # Look for IRQs
        if self.acia1.irq:
            self.trigger_irq()

        # Step CPU
        if self.tracing:
            _LOGGER.info(repr(self.mpu))
        self.mpu.step()

    def trigger_irq(self):
        """Trigger an IRQ on the machine."""
        # Do nothing if interrupts disabled
        if self.mpu.p & MPU.INTERRUPT != 0:
            return

        # Push PC and P
        self.mpu.stPushWord(self.mpu.pc)
        self.mpu.stPush(self.mpu.p)

        # Set IRQ disable
        self.mpu.opSET(MPU.INTERRUPT)

        # Vector to IRQ handler
        self.mpu.pc = self.mpu.WordAt(self.mpu.IRQ)

    @contextmanager
    def writable_rom(self):
        """Return a context manager which will temporarily enable writing to
        ROM within the context and restore the old state after. Imagine this as
        a "EEPROM programmer".

        """
        old_val = self._raise_on_rom_write
        self._raise_on_rom_write = False
        yield
        self._raise_on_rom_write = old_val

    def _add_mem_observers(self):
        """Internal method to add read/write observers to memory."""
        def raise_hell(address, value):
            if self._raise_on_rom_write:
                raise ReadOnlyMemoryError(address, value)
        self.mem.subscribe_to_write(range(*BuriSim.ROM_RANGE), raise_hell)

        # Register screen
        self.screen.observe_mem(self.mem, BuriSim.SCREEN_RANGE[0])

        # Register ACIA
        self.acia1.observe_mem(self.mem, BuriSim.ACIA1_RANGE[0])

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
    sp = serial.serial_for_url(opts['--serial'])
    sim.acia1.connect_to_serial(sp)

    # Read ROM
    sim.load_rom(opts['<rom>'])

    if opts['--load'] is not None:
        sim.load_ram(opts['--load'], 0x5000)

    # Step
    sim.reset()
    while True:
        sim.step()

if __name__ == '__main__':
    main()
