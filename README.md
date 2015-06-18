# Emulator for buri, my homebrew 6502 machine

This is a work-in-progress emulator for Buri, my homebrew 6502 computer.
Hardware designs and OS can be found at https://github.com/rjw57/buri.

## Installation

Clone this repo and install via ``pip``:

```console
$ pip install git+https://github.com/rjw57/buri-simulator-python#egg=burisim
```

### Requirements

You need a working Python. I develop on Python 3.4 but with a mind to 2.7
compatibility. If the code doesn't work on Python 2.7, it's a bug. Pull requests
welcome :).

The GUI makes use of [PySide](www.pyside.org) which is a Python binding to the
Qt library.

In addition, you'll need a working C-compiler and
[cffi](https://cffi.readthedocs.org/) installed in order to build the
C-accelerated portions.

## Running

The emulator is launched via the ``burisim`` executable. It takes a path to a
Búri ROM image and a device to use for serial I/O. The ``socat`` utility can be
used to create a pseudo-terminal for this device:

```console
$ socat PTY,link=/tmp/a,raw,echo=0 PTY,link=/tmp/b,raw,echo=0
$ picocom --noinit /tmp/a

... in another terminal ...

$ burisim --serial /tmp/b /path/to/rom.bin
```

## Acknowledgements

The core of the 6502 emulator is based on
[lib6502](http://www.piumarta.com/software/lib6502/). This library has been
modified to allow for clock frequency regulation and some small changes for
thread-safety.

## Licensing

See the [COPYING](COPYING.txt) file in the source repository. tl;dr: MIT
license.

