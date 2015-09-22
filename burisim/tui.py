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

_LOGGER = logging.getLogger(__name__)

class ACAITerminal(urwid.WidgetWrap):
    def __init__(self, main_loop, acia):
        self.acia = acia

        self._master, self._slave = pty.openpty()
        self._slave_ttyname = os.ttyname(self._slave)

        # Set master to non-blocking IO
        fl = fcntl.fcntl(self._master, fcntl.F_GETFL)
        fcntl.fcntl(self._master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        term = urwid.Terminal(
            ['minicom', '-D', self._slave_ttyname, '-b', '19200'],
            main_loop=main_loop
        )

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

class Buri(urwid.WidgetWrap):
    _signals = ['exit']

    def __init__(self, main_loop=None, sim=None):
        self.sim = sim

        # Create individual panes
        self._panes = {
            'term': ACAITerminal(main_loop, self.sim.acia1),
            'mem': urwid.SolidFill('x'),
        }

        self._sim_freq = urwid.Text('')
        self._footer = urwid.Columns([
            ('pack', urwid.Text('F1 Term')),
            ('pack', urwid.Text('F2 Memory')),
            ('weight', 1, urwid.Divider(div_char=' ')),
            (10, self._sim_freq),
        ], dividechars=1)
        self._main_frame = urwid.Frame(
            urwid.SolidFill(' '), footer=self._footer
        )

        self._switch_pane('term')

        urwid.WidgetWrap.__init__(self, self._main_frame)

        self.main_loop = main_loop

    @property
    def main_loop(self):
        return self.panes['term'].main_loop

    @main_loop.setter
    def main_loop(self, v):
        self._panes['term'].main_loop = v
        if v is not None:
            v.set_alarm_in(1.0, self._status_tick)

    def keypress(self, size, key):
        if key == 'f1':
            self._switch_pane('term')
        elif key == 'f2':
            self._switch_pane('mem')
        else:
            return self._w.keypress(size, key)

    def _status_tick(self, loop, _):
        self._sim_freq.set_text('{0:0.2} MHz'.format(
            self.sim.freq * 1e-6
        ))
        loop.set_alarm_in(1.0, self._status_tick)

    def _switch_pane(self, pane):
        w = self._panes[pane]
        self._main_frame.contents['body'] = (w, None)

    def exit(self):
        self.emit('exit')

def unhandled_input(key):
    if key == 'meta x':
        raise urwid.ExitMainLoop

class MainLoop(object):
    def __init__(self, sim=None, argv=None):
        # Record simulator
        self.sim = sim if sim is not None else BuriSim()

        self._ui = Buri(None, self.sim)
        self._loop = urwid.MainLoop(
            self._ui, unhandled_input=unhandled_input
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

