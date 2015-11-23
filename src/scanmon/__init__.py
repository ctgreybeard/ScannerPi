"""
Scanmon - Display and control a Uniden BCD996XT scanner.
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
    _LOGFORMAT = "{asctime} {module}.{funcName} -{levelname}- *{threadName}* {message}"
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

# Establish logging
        self.__logger = logging.getLogger()
        self.__logger.setLevel(LINFO)
        lfh = logging.FileHandler('scanmon.log')
        lfmt = logging.Formatter(fmt=Scanmon._LOGFORMAT, style='{')
        lfh.setFormatter(lfmt)
        self.__logger.addHandler(lfh)
        self.__args = args
        if self.__args.debug:
            self.__logger.setLevel(LDEBUG)
        else:
            self.__logger.setLevel(LINFO)
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
            command (Command): The original command (not valid in this case)
            response (Response): The formatted scanner response
        """
        del command
        self.putline('resp', 'R({}): {}'.format(response.CMD, response.display()))
        return False

    def do_mute(self, command, cmd):
        """Send a 'vol mute' command
        """

        del command, cmd # unused
        self.do_vol('vol mute', ['vol', 'mute'])

    def do_vol(self, command, cmd):
        """Send the volume request to the scanner

        .. TODO:: Needs to be rewritten to send scanner command
        """

        del command, cmd # unused

    def do_cmd(self, command, cmd):
        """Proccess a request to send a scanner command.

        .. TODO:: REWRITE!
        """

        pass

    def do_autocmd(self, command, cmd):
        """Display or set/reset the autocommand setting.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'autocmd', [1] = 'on', 'off', or None
        """

        del command, cmd # unused
        if len(cmd) > 1:
            self.autocmd = cmd[1] == 'on'
        self.message("autocommand is {}".format('on' if self.autocmd else 'off'))

    def do_quit(self, command, cmd):
        """Process a quit command.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'quit', [1] = **ignored**
        """

        del command, cmd # unused
        self.message('Quitting...')
        self.__logger.info('Quitting...')
        self.running = False

    def dispatch_command(self, inputstr):
        """Process commands.

        .. TODO:: REWRITE

        Args:
            inputstr (str): The user-entered command.
        """

        self.__logger.info('dispatch_command: Handling "%s"', inputstr)
        command = inputstr.strip()

    def run(self):
        """Initialize the window, initialize and start the threads
        Read and process commands from the monitor window.

        .. TODO:: WRITE
        """
        pass

# Build the queues, use an arbitrary 10 as the maxsize

        self.running = True
        super().run()                   # Start the whole thing going


    def close(self):
        """Close the scanner and the main window."""
        self.scanner.close()
        super().close()

