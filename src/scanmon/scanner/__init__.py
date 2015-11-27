"""A class and methods to control the Uniden BCD996XT scanner.

Classes:
Scanner -- Defines data and control structures to control

`Source <src/scanmon.scanner.html>`__
"""

import serial
import io
import os
import sys
import stat
import termios
import copy
import codecs
import logging
from logging import DEBUG as LDEBUG, \
                    INFO as LINFO, \
                    WARNING as LWARNING, \
                    ERROR as LERROR, \
                    CRITICAL as LCRITICAL
from threading import RLock
from collections import UserDict

from .formatter import Response

# Internal constants
_ENCERRORS = 'ques'
_ENCODING = 'ascii'
_NEWLINE = b'\r'
_TIMEOUT = 0.1
_BAUDRATE = 115200
_DEVS = ("/dev/ttyUSB0", "/dev/ttyUSB1")

def _decodeerror(decodeerror):
    """Simple static decoder error routine to simply replace errors with a '?'."""
    return ('?' * (decodeerror.end - decodeerror.start), decodeerror.end, )

codecs.register_error(_ENCERRORS, _decodeerror)

def _setio(ttyio):
    """Use termios to set the tty attributes the way we like. Only make changes if necessary."""
    attrs = termios.tcgetattr(ttyio)
    nattrs = copy.deepcopy(attrs)
    iflag, oflag, cflag, lflag, ispeed, ospeed, schars = list(range(7))
    # Shamefully stolen from http://en.wikibooks.org/wiki/Serial_Programming/termios
    # Input flags - Turn off input processing
    # convert break to null byte, no CR to NL translation,
    # no NL to CR translation, don't mark parity errors or breaks
    # no input parity check, don't strip high bit off,
    # no XON/XOFF software flow control
    #
    nattrs[iflag] &= ~(termios.IGNBRK |
                       termios.BRKINT |
                       termios.ICRNL |
                       termios.INLCR |
                       termios.PARMRK |
                       termios.INPCK |
                       termios.ISTRIP |
                       termios.IXON)

    # Output flags - Turn off output processing
    # no CR to NL translation, no NL to CR-NL translation,
    # no NL to CR translation, no column 0 CR suppression,
    # no Ctrl-D suppression, no fill characters, no case mapping,
    # no local output processing

    nattrs[oflag] &= ~(termios.OCRNL | termios.ONLCR | termios.ONLRET |
                       termios.ONOCR | termios.OFILL | termios.OLCUC |
                       termios.OPOST)

    # No line processing:
    # echo off, echo newline off, canonical mode off,
    # extended input processing off, signal chars off

    attrs[lflag] &= ~(termios.ECHO |
                      termios.ECHONL |
                      termios.ICANON |
                      termios.IEXTEN |
                      termios.ISIG)

    # Turn off character processing
    # clear current char size mask, no parity checking,
    # no output processing, force 8 bit input

    nattrs[cflag] &= ~(termios.CSIZE | termios.PARENB)
    nattrs[cflag] |= termios.CS8

    # One input byte is enough to return from read()
    # Inter-character timer off

    nattrs[schars][termios.VMIN] = 1
    nattrs[schars][termios.VTIME] = 0

    # Communication speed (simple version, using the predefined
    # constants)

    nattrs[ispeed] = termios.B115200
    nattrs[ospeed] = termios.B115200

    if attrs != nattrs:
        termios.tcsetattr(ttyio, termios.TCSAFLUSH, nattrs)

class ResponseQueue(UserDict):
    """Convenience method to supply default value
    """

    # pylint: disable=no-self-use
    def __missing__(self, key):
        """Return an empty set for any missing indexes
        """

        del key # Unused
        return set()

class Command(object):
    """
    Comand -- A command send request with an option callback

    Arguments:
        cmdstring: the entire scanner command string without \\\\r termination
        callback: optional callback for the response string
        userdata: optional user data object to return to the callback

    The callback function is given two arguments, the Response object
    from the command response and the userdata object from the original request.
    The callback must return a boolean indicating whether it is complete. A True
    return causes the callback to be removed from the queue, a False response
    will retain the callback where it will be called again for any responses
    from the requested command.
    """

    def __init__(self, cmdstring, callback=None, userdata=None):
        (cmd, _, _) = cmdstring.partition(',')
        if len(cmd) == 0:
            raise ValueError('CMD must not be null')
        self._cmd = cmd.upper()
        self._cmdstring = cmdstring
        self._callback = callback
        self._userdata = userdata

    @property
    def cmdstring(self):
        '''The string to send to the scanner'''
        return self._cmdstring

    @property
    def callback(self):
        '''The callback to receive any response for this command.

        Callback returns True if the processing is complete.'''
        return self._callback

    @property
    def userdata(self):
        '''user data object supplied to the callback function'''
        return self._userdata

    @property
    def cmd(self):
        """The base command to the scanner always upper case
        """
        return self._cmd

    def __repr__(self):
        return "Command({!r}, callback={!r}, userdata={!r}". \
            format(self._cmdstring, self._callback, self._userdata)

    def __hash__(self):
        """__hash__ required for set operations
        """

        return hash(self._cmd) ^ hash(self._cmdstring) ^ hash(self._callback) ^ hash(self._userdata)

    def __eq__(self, other):
        """__eq__ required for set operations
        """

        return self.__hash__() == other.__hash__()

class Scanner(object):
    """
    Scanner -- Defines data and control structures to control.

    Arguments:
        device: Optional. The name of the USB Serial connection.
            This is usually ``/dev/ttyUSB0`` or ``/dev/ttyUSB1``.
            The class will attempt to use one or the other
            if the device is not indicated.
    """

    def __init__(self, device=None):
        """Initialize the class instance.

        Arguments:
        device -- The name of the scanner device. Usually "/dev/ttyUSB0" or "/dev/ttyUSB1"

        Initialization will try to figure out what to use if the argumant is omitted.
        """

# Initialize the logger
        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self.__logger.info("Initializing scanner")
        self.iolock = RLock()
        if device is None:
            devs = _DEVS
        elif isinstance(device, str):
            devs = (device, )
        else:
            devs = device

        self.device = None
        for dev in devs:
            if stat.S_ISCHR(os.stat(dev).st_mode) and os.access(dev, os.W_OK):
                self.device = dev
                break   # We found it

        if self.device is None:
            self.__logger.critical('scanner: "%s" not found or not suitable', devs)
            raise IOError('"{}" not found or not suitable'.format(devs))

        self.__logger.info("Using: %s", self.device)

        try:
            self._serscanner = serial.Serial(port=self.device, baudrate=_BAUDRATE, timeout=_TIMEOUT)
        except serial.SerialException:
            self.__logger.exception("scanner: \"%s\" not accessable", self.device)
            raise

        _setio(self._serscanner)
        self._serscanner.flushInput()
        self._serscanner.flushOutput()

        self._response_queue = ResponseQueue()
        self._read_buffer = b''

    @property
    def fileno(self):
        '''Returns the file descriptor for the underlying Serial stream'''
        return self._serscanner.fileno()

    def watch_command(self, command):
        """Set a *"watch"* for a command response.

        Args:
            command: an instance of Command containing the command to monitor.

        The callback included is called by read_scanner when this response is received.
        When the callback returns ``True`` the watch is removed.

        Only one instance of the callback can exist on the queue for a response. Subsequent
        requests to add the same callback will not duplicate.
        """

        if isinstance(command, Command):
            if command.callback is not None:
                self.__logger.debug("Watching: %r", command)
                clist = self._response_queue[command.cmd]   # Get existing or empty set
                clist.add(command)
                self._response_queue[command.cmd] = clist
        else:
            raise ValueError('watch_command requires a Command instance')

    def close(self):
        """Close the streams from and to the scanner.
        """
        if self._serscanner:
            self._serscanner.close()

    def read_scanner(self):
        """Read available input from the scanner.

        If a complete line is found then perform any callbacks if found.
        """

        self.__logger.debug('Reading')

        while self._serscanner.inWaiting() > 0:
            self._read_buffer += self._serscanner.read(self._serscanner.inWaiting())
            self.__logger.debug('Scanner sent: %r', self._read_buffer)

        while _NEWLINE in self._read_buffer:
            (read_line, _, self._read_buffer) = self._read_buffer.partition(b'\r')
            read_line = read_line.decode(encoding='utf-8', errors='ignore')
            self.__logger.debug('Read scanner: %r', read_line)
            response = Response(read_line)
            clist = self._response_queue[response.CMD]

            if len(clist) == 0:
                clist = self._response_queue['*']       # Use default if there is one registered

            for entry in clist.copy():
                self.__logger.debug("Callback: %r", entry)
                if entry.callback(entry, response):
                    self.__logger.debug("Removing callback: %r", entry)
                    clist.remove(entry)

    def _writeline(self, line):
        """Write a line to the scanner.

        Note that this is a blocking write but there should be no reason for it to block.

        Args:
            line (str): line to write to the scanner
        """

        self.__logger.debug("Sending to scanner: %s", line)
        with self.iolock:
            self._serscanner.write(bytes(line, 'UTF-8', 'ignore'))
            # Send the '\r' newline
            self._serscanner.write(_NEWLINE)
            # And flush all output completely
            self._serscanner.flushOutput()

    def send_command(self, cmdline):
        """Send one command, queue the callback if supplied to the response queue

        Args:
            cmdline (Command): instance of Command containing command and callback
        """

        if isinstance(cmdline, Command):
            self.watch_command(cmdline)
            with self.iolock:
                self._writeline(cmdline.cmdstring)
        else:
            raise ValueError('command takes a Command argument')
