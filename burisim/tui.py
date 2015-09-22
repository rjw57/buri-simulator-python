# Make py2 like py3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip
)

import fcntl
import io
import logging
import pty
import os

import urwid
from docopt import docopt
from serial import Serial
from serial.tools import miniterm

_LOGGER = logging.getLogger(__name__)

HORIZ_BAR = '\N{BOX DRAWINGS LIGHT HORIZONTAL}'

class ACAITerminal(urwid.WidgetWrap):
    def __init__(self, main_loop, acia):
        self.acia = acia

        self._master, self._slave = pty.openpty()
        self._slave_ttyname = os.ttyname(self._slave)

        # Set master to non-blocking IO
        fl = fcntl.fcntl(self._master, fcntl.F_GETFL)
        fcntl.fcntl(self._master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        term = urwid.Terminal(self._term_func, main_loop=main_loop)

        if main_loop is not None:
            main_loop.watch_file(self._master, self._kb_input)
        self.acia.register_listener(self._acia_listener)

        urwid.WidgetWrap.__init__(self, term)

    def _kb_input(self):
        while True:
            try:
                data = os.read(self._master, 512)
            except io.BlockingIOError:
                break

            for b in data:
                b = b if type(b) == int else ord(b)
                self.acia.receive_byte(b)

    def _acia_listener(self, b):
        os.write(self._master, bytes([b]))

    @property
    def main_loop(self):
        return self._w.main_loop

    @main_loop.setter
    def main_loop(self, v):
        if v is not None:
            v.watch_file(self._master, self._kb_input)
        self._w.main_loop = v

    def _term_func(self):
        mt = miniterm.Miniterm(self._slave_ttyname, 19200, 'N', False, False)
        miniterm.console.setup()
        mt.start()
        mt.join()

class Buri(urwid.WidgetWrap):
    def __init__(self, main_loop=None, sim=None):
        self._pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, urwid.Frame(self._pile))

        self.sim = sim

        self._term = ACAITerminal(main_loop, self.sim.acia1)

        self._pane_title = urwid.Text('Doo')
        self._pane_frame = urwid.Frame(urwid.SolidFill('/'))

        self._pile.contents = [
            (urwid.Columns([
                ('weight', 1, urwid.Divider(HORIZ_BAR)),
                ('pack', urwid.Text('Serial console')),
                ('weight', 1, urwid.Divider(HORIZ_BAR)),
            ], dividechars=1), ('pack', None)),
            (self._term, ('weight', 1)),
            (urwid.Columns([
                ('weight', 1, urwid.Divider(HORIZ_BAR)),
                ('pack', self._pane_title),
                ('weight', 1, urwid.Divider(HORIZ_BAR)),
            ], dividechars=1), ('pack', None)),
            (self._pane_frame, ('weight', 1)),
        ]
        self._pile.focus_position = 1

        self._sim_freq = urwid.Text('')
        self._footer = urwid.AttrMap(urwid.Columns([
            urwid.Text([
                ' ',
                ('hotkey', 'Alt+q'), ' Quit ',
                ('hotkey', 'Alt+t'), ' Term ',
                ('hotkey', 'Alt+m'), ' Memory ',
            ]),
            ('weight', 1, urwid.Divider(div_char=' ')),
            (10, self._sim_freq),
        ]), { None: 'status', 'hotkey': 'status hotkey' })
        self._w.contents['footer'] = (self._footer, None)

        self.main_loop = main_loop

    @property
    def main_loop(self):
        return self._term.main_loop

    @main_loop.setter
    def main_loop(self, v):
        self._term.main_loop = v
        if v is not None:
            v.set_alarm_in(1.0, self._status_tick)

    def keypress(self, size, key):
        if key == 'meta q':
            raise urwid.ExitMainLoop()
        else:
            return self._w.keypress(size, key)

    def _status_tick(self, loop, _):
        self._sim_freq.set_text('{0:0.2} MHz'.format(
            self.sim.freq * 1e-6
        ))
        loop.set_alarm_in(1.0, self._status_tick)

def unhandled_input(key):
    if key == 'meta x':
        raise urwid.ExitMainLoop

class MainLoop(object):
    PALETTE = [
        (None, 'light gray', 'dark blue'),
        ('status', 'black', 'light gray'),
        ('status hotkey', 'dark red', 'light gray'),
    ]

    def __init__(self, sim=None, argv=None):
        # Record simulator
        self.sim = sim if sim is not None else BuriSim()

        self._ui = Buri(None, self.sim)
        self._loop = urwid.MainLoop(
            self._ui, unhandled_input=unhandled_input,
            palette=MainLoop.PALETTE
        )
        self._ui.main_loop = self._loop

    def attach_serial(self, filename):
        raise NotImplementedError()

    def run(self):
        # Start simulating once event loop is running
        self._loop.set_alarm_in(0, lambda *_: self.sim.start())
        with self._loop.screen.start():
            self._loop.run()
        self.sim.stop()

