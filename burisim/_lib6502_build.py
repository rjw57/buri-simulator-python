import os

from cffi import FFI

ffi = FFI()

def read_src_file(n):
    with open(os.path.join("lib6502", n)) as f:
        return f.read()

special_src = '''
    /* These functions wrap the M6502_getCallback macro. */

    static M6502_Callback
    M6502_getReadCallback(M6502 *mpu, uint16_t address) {
        return M6502_getCallback(mpu, read, address);
    }

    static M6502_Callback
    M6502_getWriteCallback(M6502 *mpu, uint16_t address) {
        return M6502_getCallback(mpu, write, address);
    }

    static M6502_Callback
    M6502_getCallCallback(M6502 *mpu, uint16_t address) {
        return M6502_getCallback(mpu, call, address);
    }

    /* These functions wrap the M6502_setCallback macro. */

    static M6502_Callback
    M6502_setReadCallback(M6502 *mpu, uint16_t address, M6502_Callback callback) {
        return M6502_setCallback(mpu, read, address, callback);
    }

    static M6502_Callback
    M6502_setWriteCallback(M6502 *mpu, uint16_t address, M6502_Callback callback) {
        return M6502_setCallback(mpu, write, address, callback);
    }

    static M6502_Callback
    M6502_setCallCallback(M6502 *mpu, uint16_t address, M6502_Callback callback) {
        return M6502_setCallback(mpu, call, address, callback);
    }

    /* These functions wrap the M6502_getVector macro. */

    uint16_t
    M6502_getRSTVector(M6502 *mpu) { return M6502_getVector(mpu, RST); }

    uint16_t
    M6502_getNMIVector(M6502 *mpu) { return M6502_getVector(mpu, NMI); }

    uint16_t
    M6502_getIRQVector(M6502 *mpu) { return M6502_getVector(mpu, IRQ); }

    /* These functions wrap the M6502_setVector macro. */

    uint16_t
    M6502_setRSTVector(M6502 *mpu, uint16_t address) {
        return M6502_setVector(mpu, RST, address);
    }

    uint16_t
    M6502_setNMIVector(M6502 *mpu, uint16_t address) {
        return M6502_setVector(mpu, NMI, address);
    }

    uint16_t
    M6502_setIRQVector(M6502 *mpu, uint16_t address) {
        return M6502_setVector(mpu, IRQ, address);
    }
'''

ffi.set_source(
    "burisim._lib6502",
    read_src_file("lib6502.c") + special_src,
    include_dirs=["lib6502"],
)

# From lib6502 man page:
ffi.cdef("""
    struct _M6502_Registers
    {
        uint8_t   a;  /* accumulator */
        uint8_t   x;  /* X index register */
        uint8_t   y;  /* Y index register */
        uint8_t   p;  /* processor status register */
        uint8_t   s;  /* stack pointer */
        uint16_t pc;  /* program counter */
    };
    typedef struct _M6502_Registers M6502_Registers;

    typedef uint8_t* M6502_Memory;

    typedef struct _M6502_Callbacks M6502_Callbacks;

    struct _M6502
    {
        M6502_Registers  *registers;   /* processor state */
        uint8_t          *memory;      /* memory image */
        ...;
    };
    typedef struct _M6502 M6502;

    M6502 *
    M6502_new(M6502_Registers *registers, M6502_Memory memory,
            M6502_Callbacks *callbacks);

    void
    M6502_reset(M6502 *mpu);

    void
    M6502_nmi(M6502 *mpu);

    void
    M6502_irq(M6502 *mpu);

    typedef int   (*M6502_Callback)(M6502 *mpu, uint16_t address, uint8_t data);

    M6502_Callback
    M6502_getReadCallback(M6502 *mpu, uint16_t address);

    M6502_Callback
    M6502_getWriteCallback(M6502 *mpu, uint16_t address);

    M6502_Callback
    M6502_getCallCallback(M6502 *mpu, uint16_t address);

    M6502_Callback
    M6502_setReadCallback(M6502 *mpu, uint16_t address, M6502_Callback callback);

    M6502_Callback
    M6502_setWriteCallback(M6502 *mpu, uint16_t address, M6502_Callback callback);

    M6502_Callback
    M6502_setCallCallback(M6502 *mpu, uint16_t address, M6502_Callback callback);

    uint16_t
    M6502_getRSTVector(M6502 *mpu);

    uint16_t
    M6502_getNMIVector(M6502 *mpu);

    uint16_t
    M6502_getIRQVector(M6502 *mpu);

    uint16_t
    M6502_setRSTVector(M6502 *mpu, uint16_t address);

    uint16_t
    M6502_setNMIVector(M6502 *mpu, uint16_t address);

    uint16_t
    M6502_setIRQVector(M6502 *mpu, uint16_t address);

    void
    M6502_run(M6502 *mpu, uint32_t n_ticks);

    int
    M6502_disassemble(M6502 *mpu, uint16_t addres_s, char buffer[64]);

    void
    M6502_dump(M6502 *mpu, char buffer[64]);

    void
    M6502_delete(M6502 *mpu);
""")

if __name__ == "__main__":
    ffi.compile()
