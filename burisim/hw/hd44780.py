from PySide import QtCore

class HD44780(QtCore.QObject):
    # emitted when state of display has changed
    update = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(HD44780, self).__init__(*args, **kwargs)
        self.reset()

    def write(self, reg, value):
        if reg not in [0, 1]:
            raise IndexError()

        # write data?
        if reg == 1:
            if self.cursor_index < len(self.ddram):
                self.ddram[self.cursor_index] = value
            self._advance_ac()
        elif value & 0x80 == 0x80:
            # set address
            self.cursor_index = value & 0x7f
        elif value == 0x01:
            # clear display and return home
            self.ddram = [ord(' ')] * 128
            self.cursor_index = 0
        elif value & 0x02 == 0x02:
            # return home
            self.cursor_index = 0

        self.update.emit()

    def read(self, reg):
        if reg not in [0, 1]:
            raise IndexError()

        # read data?
        if reg == 1:
            v = self.ddram[self.cursor_index % len(self.ddram)]
            self._advance_ac()
            return v
        else:
            # must be reading state (reg = 0).
            # TODO: implement busy flag timing
            return self.cursor_index

    def reset(self):
        self.ddram = [ord(' ')] * 128 # display ram
        self.cgram = [0] * 64 # character gen ram
        self.cursor_index = 0 # address counter

    def _advance_ac(self):
        self.cursor_index = (self.cursor_index + 1) & 0x7f
