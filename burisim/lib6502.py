from burisim._lib6502 import lib, ffi

class M6502(object):
    def __init__(self):
        # Create underlying C object wrapped so that M6502_delete is called
        # automatically on destruction.
        self._mpu = ffi.gc(
            lib.M6502_new(ffi.NULL, ffi.NULL, ffi.NULL),
            lib.M6502_delete
        )

        #print(lib.M6502_setReadCallback(self._mpu, 0xfffc, self._read_cb))
        #lib.M6502_setReadCallback(self._mpu, 0xfffd, self._read_cb)
        #lib.M6502_setCallCallback(self._mpu, 0xfffc, self._call_cb)

        self.reset()

    @property
    def memory(self):
        return self._mpu.memory

    def run(self, ticks=0):
        lib.M6502_run(self._mpu, ticks)

    def reset(self):
        lib.M6502_reset(self._mpu)

    def nmi(self):
        lib.M6502_nmi(self._mpu)

    def irq(self):
        lib.M6502_irq(self._mpu)

    @ffi.callback("M6502_Callback")
    def _read_cb(self, _, addr, data):
        print('read', addr, data)
        assert False

    @ffi.callback("M6502_Callback")
    def _write_cb(self, _, addr, data):
        print('write', addr, data)
        assert False

    @ffi.callback("M6502_Callback")
    def _call_cb(self, _, addr, data):
        print('call', addr, data)
        assert False
