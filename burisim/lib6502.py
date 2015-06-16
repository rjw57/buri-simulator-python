import weakref

import intervaltree

from burisim._lib6502 import lib, ffi # pylint: disable=no-name-in-module

# Dictionary weakly mapping MPU pointers to the owning M6502 objects.
_map_dict = weakref.WeakKeyDictionary()

def _mpu_to_obj(mpu):
    """Return the M6502 object which owns mpu. Returns None if the object
    has been garbage collected or there is no owner.

    """
    obj_wr = _map_dict.get(mpu, None)
    if obj_wr is None:
        return 0
    return obj_wr()

@ffi.callback("M6502_Callback")
def _read_cb(mpu, addr, _):
    obj = _mpu_to_obj(mpu)
    if obj is None:
        return int(0)
    return int(obj._read(addr)) # pylint: disable=no-member,protected-access

@ffi.callback("M6502_Callback")
def _call_cb(mpu, addr, _):
    obj = _mpu_to_obj(mpu)
    if obj is None:
        return int(0)
    obj._call(addr) # pylint: disable=no-member,protected-access
    return int(0)

@ffi.callback("M6502_Callback")
def _write_cb(mpu, addr, data):
    obj = _mpu_to_obj(mpu)
    if obj is None:
        return int(0)
    obj._write(addr, data) # pylint: disable=no-member,protected-access
    return int(0)

class M6502(object):
    """A 65C02 processor emulator.

    """
    def __init__(self):
        # Create underlying C object wrapped so that M6502_delete is called
        # automatically on destruction.
        self._mpu = ffi.gc(
            lib.M6502_new(ffi.NULL, ffi.NULL, ffi.NULL),
            lib.M6502_delete
        )

        # Three interval trees mapping address intervals to callables for read,
        # write and call callbacks.
        self._read_cbs = intervaltree.IntervalTree()
        self._write_cbs = intervaltree.IntervalTree()
        self._call_cbs = intervaltree.IntervalTree()

        # Record a weak reference ourselves in the mapping dict for callbacks.
        _map_dict[self._mpu] = weakref.ref(self)
        self.reset()

    def register_read_handler(self, offset, length, read_cb):
        """Registers read_cb as a callable called each time an address in the
        range [offset, offset_length) is read. Note that this is *non-inclusive*
        at the high address range. read_cb will be called with a single argument
        giving the address relative to offset, i.e. in the range [0, length). It
        should return the value to be read from that location in the range
        [0x00, 0xFF].

        If multiple callbacks are defined for a given location, the order they
        are called in is not guaranteed. The one called last will "win".

        """
        self._read_cbs.addi(offset, offset+length, read_cb)
        for v in range(offset, offset+length):
            lib.M6502_setReadCallback(self._mpu, v, _read_cb)

    def register_call_handler(self, offset, length, call_cb):
        """Registers call_cb as a callable called each time an address in the
        range [offset, offset_length) is jumped to due to anything other than a
        relative branch. Note that this is *non-inclusive* at the high address
        range. call_cb will be called with a single argument giving the address
        relative to offset, i.e. in the range [0, length). It should return the
        value to be call from that location in the range [0x00, 0xFF].

        If multiple callbacks are defined for a given location, the order they
        are called in is not guaranteed.

        """
        self._call_cbs.addi(offset, offset+length, call_cb)
        for v in range(offset, offset+length):
            lib.M6502_setCallCallback(self._mpu, v, _call_cb)

    def register_write_handler(self, offset, length, write_cb):
        """Registers write_cb as a writeable called each time an address in the
        range [offset, offset_length) is written to. Note that this is
        *non-inclusive* at the high address range. write_cb will be called with
        two arguments giving the address relative to offset, i.e. in the range
        [0, length), and the value to write.

        If multiple callbacks are defined for a given location, the order they
        are called in is not guaranteed.

        """
        self._write_cbs.addi(offset, offset+length, write_cb)
        for v in range(offset, offset+length):
            lib.M6502_setWriteCallback(self._mpu, v, _write_cb)

    @property
    def memory(self):
        """A list-like object which allows direct read/write access to the 64K
        of memory. Note that this does not trigger any read/write/call
        callbacks.

        """
        return self._mpu.memory

    def run(self, ticks=0):
        """Run the processor for at least the specified number of clock ticks.
        If ticks is 0, the processor is run forever. Due to an implementation
        issue, ticks < 4 billion-ish.

        Returns the number of ticks actually performed. This may be different
        that the amount requested since emulation always stops on an instruction
        boundary.

        """
        return lib.M6502_run(self._mpu, ticks)

    def reset(self):
        """Trigger a processor reset.

        """
        lib.M6502_reset(self._mpu)

    def nmi(self):
        """Trigger a non-maskable interrupt.

        """
        lib.M6502_nmi(self._mpu)

    def irq(self):
        """Trigger a maskable interrupt.

        """
        lib.M6502_irq(self._mpu)

    @property
    def rst_vector(self):
        return lib.M6502_getRSTVector(self._mpu)

    @rst_vector.setter
    def rst_vector(self, v):
        return lib.M6502_setRSTVector(self._mpu, v)

    @property
    def irq_vector(self):
        return lib.M6502_getIRQVector(self._mpu)

    @irq_vector.setter
    def irq_vector(self, v):
        return lib.M6502_setIRQVector(self._mpu, v)

    @property
    def nmi_vector(self):
        return lib.M6502_getNMIVector(self._mpu)

    @nmi_vector.setter
    def nmi_vector(self, v):
        return lib.M6502_setNMIVector(self._mpu, v)

    # Internal callback handlinmg

    def _read(self, addr):
        v = 0
        for i in self._read_cbs[addr]:
            v = i.data(addr - i.begin)
        return v

    def _write(self, addr, data):
        for i in self._write_cbs[addr]:
            i.data(addr - i.begin, data)

    def _call(self, addr):
        for i in self._call_cbs[addr]:
            i.data(addr - i.begin)
