# Make py2 like py3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip
)

from itertools import cycle
import logging
import threading
import time

from past.builtins import basestring # pylint: disable=redefined-builtin

from burisim.lib6502 import M6502
from burisim.hw.acia import ACIA

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
    """Main simulator implementation.

    """
    ROM_SIZE = 0x2000 # 8K
    ROM_RANGE = 0x10000 - ROM_SIZE, 0x10000
    ACIA1_SIZE = 0x4
    ACIA1_RANGE = 0xDFFC, 0xDFFC + ACIA1_SIZE

    def __init__(self):
        # Create our processor
        self.mpu = M6502()
        self._mpu_lock = threading.Lock()
        self._mpu_thread = None
        self._want_stop = True

        # Register ROM as read-only
        def raise_rom_exception(addr, value):
            raise ReadOnlyMemoryError(addr + BuriSim.ROM_RANGE[0], value)
        self.mpu.register_write_handler(
            BuriSim.ROM_RANGE[0], BuriSim.ROM_SIZE, raise_rom_exception
        )

        # Do not trace execution
        self.tracing = False

        # IRQ lines
        self._irq_lines = {}

        # Create I/O devices
        self.acia1 = ACIA()
        self.acia1.irq_cb = self._new_irq_line()
        self.mpu.register_read_handler(
            BuriSim.ACIA1_RANGE[0], BuriSim.ACIA1_SIZE, self.acia1.read_reg
        )
        self.mpu.register_write_handler(
            BuriSim.ACIA1_RANGE[0], BuriSim.ACIA1_SIZE, self.acia1.write_reg
        )

        # Reset the computer
        self.reset()

    def _new_irq_line(self):
        idx = len(self._irq_lines)
        def setter(flag):
            prev_irq = self.irq
            self._irq_lines[idx] = flag
            new_irq = self.irq
            if prev_irq and not new_irq:
                self.mpu.irq()
        self._irq_lines[idx] = True
        return setter

    @property
    def memory(self):
        """A *read-only* sequence representing the machine memory. Don't mutate
        this unless you are some sort of crazy expert.

        """
        return self.mpu.memory

    @property
    def irq(self):
        """The state of the ~IRQ line. This is an AND of all the individual ~IRQ
        lines of each I/O device. (I.e. the NOR of the IRQ lines.)

        """
        return all(self._irq_lines.values())

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
        with self._mpu_lock:
            for addr, val in zip(range(*BuriSim.ROM_RANGE), cycle(rom_bytes)):
                self.mpu.memory[addr] = val

    def load_ram_bytes(self, ram_bytes, addr):
        """Load a RAM image from the passed bytes object.

        """
        _LOGGER.info('loading RAM image of %s bytes', len(ram_bytes))

        with self._mpu_lock:
            for off, val in enumerate(ram_bytes):
                self.mpu.memory[addr + off] = val

    def reset(self):
        """Perform a hardware reset."""
        # Reset hardware
        self.acia1.hw_reset()

        # Reset MPU
        with self._mpu_lock:
            self.mpu.reset()

    def start(self):
        # ensure we're stopped!
        self.stop()

        # create simulator loop function
        def loop():
            ticks_per_loop = int(5*2e6) # should mean the loop is around 5Hz.
            last_report, n_ticks = time.time(), 0
            while not self._want_stop:
                n_ticks += self.step(ticks_per_loop)
                now = time.time()
                print('Running at {0:d}Hz'.format(int(n_ticks / (now - last_report))))
                last_report, n_ticks = now, 0

        # create and start thread
        self._mpu_thread = threading.Thread(target=loop)
        self._want_stop = False
        self._mpu_thread.start()

    def stop(self):
        if self._mpu_thread is None or not self._mpu_thread.is_alive():
            # we're not running
            return

        # signal stop
        self._want_stop = True
        self.mpu.exit()

        # wait for thread
        self._mpu_thread.join()

    def step(self, ticks):
        """Single-cycle the machine for a specified number of clock ticks."""
        # TODO: tracing
        with self._mpu_lock:
            return self.mpu.run(ticks)
