# Make py2 like py3
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip
)
from past.builtins import basestring # pylint: disable=redefined-builtin

import logging
import pty
import os

import urwid
from docopt import docopt
from serial.tools import miniterm

_LOGGER = logging.getLogger(__name__)

class Buri(urwid.WidgetWrap):
    def __init__(self, main_loop=None):
        master, slave = pty.openpty()

        self._slave = os.ttyname(slave)
        self._master_fd = master

        # Create individual panes
        self.panes = {
            'term': urwid.Terminal(
                self._term_start, main_loop=main_loop
            ),
        }

        urwid.WidgetWrap.__init__(self, self._create_ui())

    @property
    def main_loop(self):
        return self.panes['term'].main_loop

    @main_loop.setter
    def main_loop(self, v):
        self.panes['term'].main_loop = v

    def _create_ui(self):
        cols = [ urwid.Text('F1 Term'), ]
        footer = urwid.Columns(cols)

        return urwid.Frame(self.panes['term'], footer=footer)

    def _term_start(self):
        mt = miniterm.Miniterm(
            self._slave, 19200, 'N', False, False, echo=False,
        )
        mt.start()
        try:
            mt.join(True)
        except KeyboardInterrupt:
            pass
        mt.join()


def unhandled_input(key):
    if key == 'meta x':
        raise urwid.ExitMainLoop

class MainLoop(object):
    def __init__(self, sim=None, argv=None):
        # Record simulator
        self.sim = sim if sim is not None else BuriSim()

        self._ui = Buri(self.sim)
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

