from collections import deque
import logging
import struct
import serial

from PySide import QtCore, QtSerialPort

_LOGGER = logging.getLogger(__name__)

class ACIA(object):
    """Emulation of 6551-style ACIA. Optionally pass a PySerial-compatible
    object which will be the serial port connected to the ACIA.

    """
    # Mapping from selected baud rate value to baud rate.
    # None == unimplemented.
    _SBN_TABLE = [
        None, 50, 75, 109.92, 134.58, 150, 300, 600, 1200, 1800,
        2400, 2600, 4800, 7200, 9600, 19200,
    ]

    # Mapping from word length setting to word length constants
    _WL_TABLE = [serial.EIGHTBITS, serial.SEVENBITS, serial.SIXBITS, serial.FIVEBITS]

    # Mapping from parity mode control to parity constants
    _PMC_TABLE = [serial.PARITY_ODD, serial.PARITY_EVEN, serial.PARITY_NONE, serial.PARITY_NONE]

    # Status register bits
    _ST_IRQ = 0b10000000
    _ST_TDRE = 0b00010000
    _ST_RDRF = 0b00001000

    def __init__(self, set_reg_cb=None, serial_port=None):
        self.serial_port = None
        if serial_port is not None:
            self.connect_to_file(serial_port)

        # Registers
        self._recv_data = 0
        self._status_reg = 0
        self._command_reg = 0
        self._control_reg = 0

        # Record "set register" callback
        self._set_reg_cb = set_reg_cb

        # read buffer
        self._in_buffer = deque()

        # Hardware-reset
        self.hw_reset()

    def _note_reg_update(self, number, value):
        if self._set_reg_cb is not None:
            self._set_reg_cb(number, value)

    @property
    def irq(self):
        return self._status_reg & ACIA._ST_IRQ != 0

    def poll(self):
        """Call regularly to check for incoming data."""
        # Early out if no serial port attached or no data waiting
        sp = self.serial_port
        if sp is None:
            return

        while sp.isReadable() and sp.bytesAvailable() > 0:
            print('.')
            self._in_buffer.append(sp.getChar())

        # There is some data, transfer next data if receive data reg is empty
        if len(self._in_buffer) > 0 and self._status_reg & ACIA._ST_RDRF == 0:
            self._recv_data = self._in_buffer.popleft()
            self._status_reg |= ACIA._ST_RDRF
            self._set_reg_cb(0, self._recv_data)
            self._set_reg_cb(1, self._status_reg)
            self._trigger_irq()

    def _data_available(self):
        print('.')

    def connect_to_file(self, filename):
        """Open a file which will be used as the serial port for the ACIA.

        """
        self.serial_port = QtNetwork.QLocalSocket()
        self.serial_port.connectToServer(filename)
        if not self.serial_port.waitForConnected(1000):
            raise ValueError('failed to open %s' % filename)
        self.serial_port.readyRead.connect(self._data_available)
        self._update_serial_port()

    def hw_reset(self):
        """Perform a hardware reset."""
        self._status_reg = 0b00010000
        self._control_reg = 0b00000000
        self._command_reg = 0b00000000
        self._set_reg_cb(1, self._status_reg)
        self._set_reg_cb(2, self._command_reg)
        self._set_reg_cb(3, self._control_reg)
        self._update_serial_port()

    def write_reg(self, reg_idx, value):
        """Write register using RS1 and RS0 as high and low bits indexing the
        register.

        """
        if reg_idx == 0:
            # Write transmit register
            self._tx(value)
        elif reg_idx == 1:
            # Programmed reset
            self._prog_reset()
        elif reg_idx == 2:
            # Write command reg.
            self._command_reg = value
            self._set_reg_cb(2, self._command_reg)
            self._update_serial_port()
        elif reg_idx == 3:
            # Write control reg
            self._control_reg = value
            self._set_reg_cb(3, self._control_reg)
            self._update_serial_port()
        else:
            raise IndexError('No such register: ' + repr(reg_idx))

    def read_reg(self, reg_idx):
        """Read register using RS1 and RS0 as high and low bits indexing the
        register.

        """
        if reg_idx == 0:
            # Read receiver register
            self._status_reg &= ~(ACIA._ST_RDRF) # clear data reg full flag
            return self._recv_data
        elif reg_idx == 1:
            # Read status register clearing interrupt bit after the fact
            sr = self._status_reg
            self._status_reg &= 0b01111111
            return sr
        elif reg_idx == 2:
            # Read command reg.
            return self._command_reg
        elif reg_idx == 3:
            # Read control reg.
            return self._control_reg
        else:
            raise IndexError('No such register: ' + repr(reg_idx))

    def _trigger_irq(self):
        """Trigger an interrupt."""
        if self._control_reg & 0b1100 == 0b0100:
            self._status_reg |= 0b10010000
            self._set_reg_cb(1, self._status_reg)
        # FIXME: trigger on processor?

    def _prog_reset(self):
        """Perform a programmed reset."""
        # NOTE: does not change control reg
        self._status_reg = 0b00010000
        self._command_reg = 0b00000000
        self._set_reg_cb(1, self._status_reg)
        self._set_reg_cb(2, self._command_reg)
        self._update_serial_port()

    def _tx(self, value):
        """Transmit byte."""
        # Ensure transmit data reg. is empty
        if self._status_reg & ACIA._ST_TDRE == 0:
            _LOGGER.warn('serial port overflow: dropping output.')
            return

        # Clear transmit data empty reg
        self._status_reg &= ~(ACIA._ST_TDRE)

        # Write output
        if self.serial_port is not None:
            self.serial_port.putChar(value) # write(struct.pack('B', value))

        # Set transmit data empty reg
        self._status_reg |= ACIA._ST_TDRE

        self._set_reg_cb(1, self._status_reg)

        # Trigger IRQ if required
        tic = (self._command_reg >> 2) & 0b11
        if tic == 1:
            self._trigger_irq()

    def _update_serial_port(self):
        """Update associated serial port with new settings from control register."""

        return

        if self.serial_port is None:
            return
        sp = self.serial_port

        # Extract control-register parameters
        # TODO: rcs setting is ignored
        sbn = (self._control_reg >> 7) & 0b1
        wl = (self._control_reg >> 5) & 0b11
        #rcs = (self._control_reg >> 4) & 0b1
        sbr = self._control_reg & 0b1111

        # Extract command-register parameters.
        # TODO: most of these are ignored
        pmc = (self._command_reg >> 6) & 0b11
        #pme = (self._command_reg >> 5) & 0b1
        #rem = (self._command_reg >> 4) & 0b1
        #tic = (self._command_reg >> 2) & 0b11
        #ird = (self._command_reg >> 1) & 0b1
        dtr = self._command_reg & 0b1

        # Set parameters
        baudrate = ACIA._SBN_TABLE[sbr]
        if baudrate is None:
            # Use maximum baudrate
            baudrate = max(*sp.BAUDRATES)
        sp.baudrate = baudrate

        # Set word length
        sp.bytesize = ACIA._WL_TABLE[wl]

        try:
            # Data terminal ready
            sp.setDTR(dtr == 1)

            # Set parity
            sp.parity = ACIA._PMC_TABLE[pmc]
        except OSError:
            # soft fail...
            pass

        # Set stop bits
        if sbn == 0:
            sp.stopbits = serial.STOPBITS_ONE
        elif sbn == 1:
            if sp.bytesize == serial.FIVEBITS and sp.partiy == serial.PARITY_NONE:
                sp.stopbits = serial.STOPBITS_ONE_POINT_FIVE
            elif sp.bytesize == serial.EIGHTBITS and sp.partiy == serial.PARITY_NONE:
                sp.stopbits = serial.STOPBITS_ONE
            else:
                sp.stopbits = serial.STOPBITS_TWO

