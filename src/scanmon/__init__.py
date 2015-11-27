"""
Scanmon - Display and control a Uniden BCD996XT scanner.

`Source <src/scanmon.html>`__
"""
from collections import deque
from logging \
    import DEBUG as LDEBUG, \
        INFO as LINFO, \
        WARNING as LWARNING, \
        ERROR as LERROR, \
        CRITICAL as LCRITICAL

import datetime
import decimal
import io
import logging
import queue
import re
import sqlite3
import subprocess
import sys
import threading
import time

from urwid import ExitMainLoop

# Our own definitions
from scanmon.glgmonitor import GLGMonitor
from scanmon.monwin import Monwin
from scanmon.scanner import Scanner, Command
from scanmon.scanner.formatter import Response, ScannerDecodeError

class Scanmon(Monwin):
    """The main scanmon code. Everything begins here.

    Arguments:
        args: An args object from argparser.
    """

# Class constants
    _LOGFORMAT = "{asctime} {name}.{funcName} -{levelname}- *{threadName}* {message}"
    _TIMEFMT = '%H:%M:%S'
    _GLGTIME = 0.5  # Half second
    _EPOCH = 3600 * 24 * 356    # A year of seconds
    _MAXSIZE = 10


    @staticmethod
    def _adapt_bool(value):
        """sqllite3 adapter

        Adapts a python bool value to an int to use in mysql.

        Args:
            value (object): A value to convert to an int

        Returns:
            A 1 or 0 from the converted boolean interpretation of 'value'
        """
        return int(bool(value))

    @staticmethod
    def _convert_bool(value):
        """sqllite3 converter

        Adapts a sql bool value (0 or 1) to a bool from mysql.

        Args:
            value (b'0' or b'1'): A value to convert to a bool

        Returns:
            A True or False from the converted boolean interpretation of 'value'
        """
        return value == b'1'

    @staticmethod
    def _adapt_decimal(value):
        """sqllite3 adapter

        Adapts a python decimal value to a str to use in mysql.

        Args:
            value (number): A value to convert to a str

        Returns:
            A str from the converted 'value'
        """
        return str(value)

    @staticmethod
    def _convert_decimal(value):
        """sqllite3 converter

        Adapts a sql decimal string value to a number

        Args:
            value (str): A string value to convert to a number (decimal)

        Returns:
            A decimal from the converted interpretation of 'value'
            or Decimal('NaN')
        """
        try:
            rval = decimal.Decimal(value.decode())
        except decimal.InvalidOperation:
            rval = decimal.Decimal("NaN")

        return rval

    def __init__(self, args):
        """Initialize the instance.
        """

        self.__args = args

        # Establish logging
        lfh = logging.FileHandler('scanmon.log')
        lfmt = logging.Formatter(fmt=Scanmon._LOGFORMAT, style='{')
        lfh.setFormatter(lfmt)
        root_logger = logging.getLogger()
        root_logger.addHandler(lfh)

        if self.__args.debug:
            root_logger.setLevel(LDEBUG)
        else:
            root_logger.setLevel(LINFO)

        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self.__logger.info("Scanmon initializing")

        # Initialize the mainloop
        super().__init__()

        # Get the scanner started
        self.scanner = Scanner(self.__args.scanner)
        self.scanner_handle = self.watch_file(self.scanner.fileno, self.scanner.read_scanner)
        self.scanner.watch_command(Command('*', callback=self.catch_all))
        self.running = False
        self.autocmd = False

        # Commands entered at the console
        self.q_cmdin = queue.Queue(maxsize=Scanmon._MAXSIZE)

        # Set up GLG monitoring
        self.glgmonitor = GLGMonitor(self, args=self.__args)
        self.scanner.watch_command(Command('GLG', callback=self.glgmonitor.process))

        # Setup sqlite3 adapters
        sqlite3.register_adapter(decimal.Decimal, Scanmon._adapt_decimal)
        sqlite3.register_converter('decimal', Scanmon._convert_decimal)
        sqlite3.register_adapter(bool, Scanmon._adapt_bool)
        sqlite3.register_converter('boolean', Scanmon._convert_bool)

        # Initialization complete
        self.__logger.info("Scanmon initializing")

    def catch_all(self, command, response):
        """Fallback response handler. If no other handler is registered this handler
        will be called.

        Args:
            command (Command): The original command (unused)
            response (Response): The formatted scanner response
        """

        del command
        self.putline('resp', 'R({}): {}'.format(response.CMD, response.display(response)))
        return False

    def cmd_mute(self, cmd, args):
        """Send a 'vol mute' command

        Args:
            cmd (str): The command entered (unused)
            args (str): The command argument (unused)
        """

        del cmd, args # unused
        self.cmd_vol('vol', 'mute')

    def cmd_mon(self, _, args):
        """Start or stop the GLG monitoring

        Args:
            cmd (str): The command entered (unused)
            args (str): 'start', 'stop', or null
        """

        if len(args) > 0:
            if args == 'start':
                self.glgmonitor.start()
            elif args == 'stop':
                self.glgmonitor.stop()
            else:
                self.message("Unknown option: {}".format(args))
        else:
            startstop = 'Running' if self.glgmonitor.running else 'Stopped'
            self.putline('resp', "Monitoring {}".format(startstop))

    def cmd_vol(self, cmd, args):
        """Send the volume request to the scanner

        Args:
            cmd (str): The command entered (unused)
            args (str): The volume number (0-29) or 'mute'
        """

        del cmd # unused

        if len(args) > 0:
            vol = ','
            if args == 'mute':
                vol += '0'
            else:
                vol += args
        else:
            vol = ''

        vol_cmd = Command('VOL' + vol)
        self.scanner.send_command(vol_cmd)

    def cmd_cmd(self, cmd, args):
        """Proccess a request to send a scanner command.

        Args:
            cmd (str): The command entered (unused)
            args (str): The command to send to the scanner
        """

        del cmd # Unused
        args = args.lstrip()

        # Split out the command and make it uppercase
        (cmd, sep, rest) = args.partition(',')
        cmd = cmd.upper()

        # Put it back together
        args = cmd + sep + rest

        self.scanner.send_command(Command(args))

    def cmd_autocmd(self, cmd, args):
        """Display or set/reset the autocommand setting.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'autocmd', [1] = 'on', 'off', or None
        """

        del cmd # unused
        if len(args) > 1:
            self.autocmd = args == 'on'

        self.message("autocommand is {}".format('on' if self.autocmd else 'off'))

    def cmd_quit(self, cmd, args):
        """Process a quit command.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'quit', [1] = **ignored**
        """

        del cmd, args # unused
        self.message('Quitting...')
        self.__logger.info('Quitting...')
        self.running = False
        raise ExitMainLoop

    def dispatch_command(self, inputstr):
        """Process commands.

        Args:
            inputstr (str): The user-entered command.
        """

        self.__logger.info('dispatch_command: Handling "%s"', inputstr)
        (cmd, _, args) = inputstr.partition(' ')
        cmd_method = 'cmd_' + cmd.strip()
        args = args.lstrip()

        handler = getattr(self, cmd_method, None)

        if handler:
            self.putline('resp', "CMD: {}".format(inputstr))

        elif self.autocmd:
            handler = self.cmd_cmd
            args = inputstr

        if handler:
            handler(cmd, args)

        else:
            self.message("Unknown command: {}".format(inputstr))

    def set_disp(self, cmd, resp):
        """Set version in main window

        Args:
            cmd (Command): scanner command
            resp (Response): scanner response
        """

        self.__logger.info("Setting response: %s", resp.parts[1])
        cmd.userdata(resp.parts[1])

    def run(self):
        """Initialize the window, initialize and start the threads
        Read and process commands from the monitor window.

        """

        if self.__args.monitor:
            self.glgmonitor.start()

        self.scanner.send_command(Command('VER', callback=self.set_disp, userdata=self.ver.set_text))
        self.scanner.send_command(Command('MDL', callback=self.set_disp, userdata=self.mdl.set_text))

        self.running = True
        super().run()                   # Start the whole thing going


    def close(self):
        """Close the scanner and the main window."""
        self.scanner.close()

