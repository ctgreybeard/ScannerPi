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
import configparser

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
    _DATETIMEFMT = '%a %d %b %Y %H:%M %Z'
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

    def __init__(self, args, argmap):
        """Initialize the instance.
        """

        self.config = self.merge_config(args, argmap)

        # Establish logging
        lfh = logging.FileHandler(self.config.get('scanmon', 'logfile', fallback='scanmon.log'))
        lfmt = logging.Formatter(fmt=Scanmon._LOGFORMAT, style='{')
        lfh.setFormatter(lfmt)
        root_logger = logging.getLogger()
        root_logger.addHandler(lfh)

        if self.config.getboolean('scanmon', 'debug', fallback=False):
            root_logger.setLevel(LDEBUG)
        else:
            root_logger.setLevel(LINFO)

        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self.__logger.info("Scanmon initializing")

        # Initialize the mainloop
        super().__init__(self.config['window'])

        # Get the scanner started
        self.scanner = Scanner(self.config.get('scanner', 'device', fallback=None))
        self.scanner_handle = self.watch_file(self.scanner.fileno, self.scanner.read_scanner)
        self.scanner.watch_command(Command('*', callback=self.catch_all))
        self.running = False
        self.autocmd = False
        self.automute = None

        # Commands entered at the console
        self.q_cmdin = queue.Queue(maxsize=Scanmon._MAXSIZE)

        # Set up GLG monitoring
        self.glgmonitor = GLGMonitor(self, config=self.config['monitor'])
        self.scanner.watch_command(Command('GLG', callback=self.glgmonitor.process))

        # Setup sqlite3 adapters
        sqlite3.register_adapter(decimal.Decimal, Scanmon._adapt_decimal)
        sqlite3.register_converter('decimal', Scanmon._convert_decimal)
        sqlite3.register_adapter(bool, Scanmon._adapt_bool)
        sqlite3.register_converter('boolean', Scanmon._convert_bool)

        # Initialization complete
        self.__logger.info("Scanmon initialization complete")

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

    def cmd_mute(self, cmd, cmd_args):
        """Send a 'vol mute' command

        Args:
            cmd (str): The command entered (unused)
            cmd_args (str): The command argument (unused)
        """

        del cmd, cmd_args # unused
        self.cmd_vol('vol', 'mute')

    def cmd_mon(self, _, cmd_args):
        """Start or stop the GLG monitoring

        Args:
            cmd (str): The command entered (unused)
            cmd_args (str): 'start', 'stop', or null
        """

        if len(cmd_args) > 0:
            if cmd_args == 'start':
                self.glgmonitor.start()
            elif cmd_args == 'stop':
                self.glgmonitor.stop()
            else:
                self.message("Unknown option: {}".format(cmd_args))
        else:
            startstop = 'Running' if self.glgmonitor.running else 'Stopped'
            self.putline('resp', "Monitoring {}".format(startstop))

    def cmd_vol(self, cmd, cmd_args):
        """Send the volume request to the scanner

        Args:
            cmd (str): The command entered (unused)
            cmd_args (str): The volume number (0-29) or 'mute'
        """

        del cmd # unused

        if len(cmd_args) > 0:
            vol = ','
            if cmd_args == 'mute':
                vol += '0'
            else:
                vol += cmd_args
        else:
            vol = ''

        vol_cmd = Command('VOL' + vol)
        self.scanner.send_command(vol_cmd)

    def cmd_cmd(self, cmd, cmd_args):
        """Proccess a request to send a scanner command.

        Args:
            cmd (str): The command entered (unused)
            cmd_args (str): The command to send to the scanner
        """

        del cmd # Unused
        cmd_args = cmd_args.lstrip()

        # Split out the command and make it uppercase
        (cmd, sep, rest) = cmd_args.partition(',')
        cmd = cmd.upper()

        # Put it back together
        cmd_args = cmd + sep + rest

        self.scanner.send_command(Command(cmd_args))

    def cmd_autocmd(self, cmd, cmd_args):
        """Display or set/reset the autocommand setting.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'autocmd', [1] = 'on', 'off', or None
        """

        del cmd # unused
        if len(cmd_args) > 1:
            self.autocmd = cmd_args == 'on'

        self.message("autocommand is {}".format('on' if self.autocmd else 'off'))

    def cmd_quit(self, cmd, cmd_args):
        """Process a quit command.

        Args:
            command (str): the command line as entered
            cmd ([str]): the list [0] = 'quit', [1] = **ignored**
        """

        del cmd, cmd_args # unused
        self.message('Quitting...')
        self.__logger.info('Quitting...')
        self.running = False
        raise ExitMainLoop

    def set_automute(self, mute_t):
        """Set the automute time.

        Args:
            mute_t (datetime): New automute time or None to cancel
        """

        if self.automute:
            # First, cancel any existing automute
            (_, t_handle) = self.automute
            self.remove_alarm(t_handle)
            self.automute = None

        if mute_t:
            self.automute = (mute_t, self.set_alarm_at(mute_t.timestamp(), self.do_automute))

    def cmd_automute(self, cmd, cmd_args):
        """Set or unset time to automatically mute the scanner.

        Args:
            cmd (str): "automute"
            cmd_args (str): Either a time or "off"
        """

        if cmd_args == "":
            if self.automute:
                (m_time, _) = self.automute
                ans = m_time.strftime(Scanmon._DATETIMEFMT)
            else:
                ans = "Off"

            self.putline('resp', "Automute: {}".format(ans))

        elif cmd_args == "off":
            self.set_automute(None)

            self.putline('resp', "Automute: Off")

        else:
            try:
                newtime = datetime.datetime.strptime(cmd_args, "%H:%M")
            except ValueError:
                self.putline('resp', "Invalid time for automute")
                return

            thisday = datetime.date.today()
            thistime = datetime.time(newtime.hour, newtime.minute, 0)
            mute_t = datetime.datetime.combine(thisday, thistime)

            while mute_t < datetime.datetime.today():
                mute_t += datetime.timedelta(days=1)

            self.set_automute(mute_t)
            self.putline('resp', "Automute: {}".format(mute_t.strftime(Scanmon._DATETIMEFMT)))

    def do_automute(self, win, user_data=None):
        """Execute mute (VOL,0) and update the automute time if set.

        Args:
            none
        """

        self.cmd_vol("VOL", "0")
        if self.automute:
            (mute_t, _) = self.automute
            mute_t = mute_t + datetime.timedelta(days=1)
            self.set_automute(mute_t)
            self.putline('msg', "Auto muted")
        else:
            self.__logger.error("Automute called for no reason")
            self.putline('msg', "Automute called for no reason")

    def dispatch_command(self, inputstr):
        """Process commands.

        Args:
            inputstr (str): The user-entered command.
        """

        self.__logger.info('dispatch_command: Handling "%s"', inputstr)
        (cmd, _, cmd_args) = inputstr.partition(' ')
        cmd_method = 'cmd_' + cmd.strip()
        cmd_args = cmd_args.lstrip()

        handler = getattr(self, cmd_method, None)

        if handler:
            self.putline('resp', "CMD: {}".format(inputstr))

        elif self.autocmd:
            handler = self.cmd_cmd
            cmd_args = inputstr

        if handler:
            handler(cmd, cmd_args)

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

        if self.config.getboolean('monitor', 'start', fallback=True):
            self.glgmonitor.start()

        self.scanner.send_command(Command('VER', callback=self.set_disp, userdata=self.ver.set_text))
        self.scanner.send_command(Command('MDL', callback=self.set_disp, userdata=self.mdl.set_text))

        self.running = True
        super().run()                   # Start the whole thing going


    def close(self):
        """Close the scanner and the main window."""
        self.scanner.close()

    def merge_config(self, args, argmap):
        """Merge an commandline arguments into the config.ini configuration.
        """

        configfile_name = args.config
        assert configfile_name is not None and configfile_name != '', 'Invalid config file'
        config = configparser.ConfigParser()
        for sname in ('scanmon', 'monitor', 'window', 'scanner'):
            config.add_section(sname)

        with open(configfile_name, 'r') as configfile:
            config.read_file(configfile)

        for key, val in argmap.items():
            if key in args:
                aval = str(vars(args)[key])
                config[val[0]][val[1]] = aval

        return config
