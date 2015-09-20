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

class Buri(urwid.WidgetWrap):
    def __init__(self, main_loop=None, sim=None):
        self.sim = sim

        self._master, self._slave = pty.openpty()
        self._slave_ttyname = os.ttyname(self._slave)

        # Set master to non-blocking IO
        fl = fcntl.fcntl(self._master, fcntl.F_GETFL)
        fcntl.fcntl(self._master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # Create individual panes
        self.panes = {
            'term': urwid.Terminal(
                ['minicom', '-D', self._slave_ttyname], main_loop=main_loop
            ),
        }

        if main_loop is not None:
            main_loop.watch_file(self._master, self._kb_input)
        self.sim.acia1.register_listener(self._acia_listener)

        urwid.WidgetWrap.__init__(self, self._create_ui())

    def _kb_input(self):
        while True:
            try:
                data = os.read(self._master, 512)
            except io.BlockingIOError:
                break

            for b in data:
                b = b if type(b) == int else ord(b)
                self.sim.acia1.receive_byte(b)

    def _acia_listener(self, b):
        os.write(self._master, bytes([b]))

    @property
    def main_loop(self):
        return self.panes['term'].main_loop

    @main_loop.setter
    def main_loop(self, v):
        if v is not None:
            v.watch_file(self._master, self._kb_input)
        self.panes['term'].main_loop = v

    def _create_ui(self):
        cols = [ urwid.Text('F1 Term'), ]
        footer = urwid.Columns(cols)

        return urwid.Frame(self.panes['term'], footer=footer)

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

