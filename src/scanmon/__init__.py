"""
Scanmon - Display and control a Uniden BCD996XT scanner.
"""
from collections import deque
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL

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
from scanmon.scanner import Scanner
from scanmon.scanner.formatter import Response, ScannerDecodeError

class Scanmon(Monwin):
    """The main scanmon code. Everything begins here."""

# Class constants
    _logformat = "{asctime} {module}.{funcName} -{levelname}- *{threadName}* {message}"
    _TIMEFMT = '%H:%M:%S'
    _GLGTIME = 0.5  # Half second
    _EPOCH = 3600 * 24 * 356    # A year of seconds
    _DEFBASEVOL = '-12.0dB'
    _ABSVOL = {'normal': 0, 'low': -3, 'verylow': -6, 'veryverylow': -9, 'high': 3, 'veryhigh': 6}  # Adjustments from basevolume (units = dB)
    _RELVOL = {'down': -3, 'up': 3}     # Names for relative adjustments
# NOTE: For the Wolfson card the adjusments are amplified: 3dB+ goes up 6dB, 3+ goes up 3dB. This is a bug but I don't
#       know who to blame. 3+ should go up 3 UNITS which is 1.5dB, etc.
# 8/25/2014: The newer code alleviates the problem.
    _RELBROKEN = False
    _VOLALIAS = {'norm':'normal', 'vlow':'verylow', 'vvlow': 'veryverylow', 'hi':'high', 'vhigh':'veryhigh', 'vhi':'veryhigh', 'dn':'down'}


    @staticmethod
    def _adapt_bool(value):
        return(int(bool(value)))

    @staticmethod
    def _convert_bool(value):
        return value == b'1'

    @staticmethod
    def _adapt_decimal(value):
        return(str(value))

    @staticmethod
    def _convert_decimal(value):
        try:
            return decimal.Decimal(value.decode())
        except decimal.InvalidOperation:
            return decimal.Decimal("NaN")

    def __init__(self, args):
        self.__args = args
        self.__logger = logging.getLogger()
        self.__logger.setLevel(LINFO)
        lfh = logging.FileHandler('scanmon.log')
        lfh.setLevel(LDEBUG)
        lfmt = logging.Formatter(fmt=Scanmon._logformat, style = '{')
        lfh.setFormatter(lfmt)
        self.__logger.addHandler(lfh)
        self.__logger.info("Scanmon initializing")
        self.scanner = Scanner(self.__args.scanner)
        self.Running = False
        self.autocmd = False
        if self.__args.debug: self.__logger.setLevel(LDEBUG)
        else: self.__logger.setLevel(LINFO)
        # Setup sqlite3 adapters
        sqlite3.register_adapter(decimal.Decimal, Scanmon._adapt_decimal)
        sqlite3.register_converter('decimal', Scanmon._convert_decimal)
        sqlite3.register_adapter(bool, Scanmon._adapt_bool)
        sqlite3.register_converter('boolean', Scanmon._convert_bool)

    def f_cmdin(self):
        """Read input from the window and post to the command queue
        """
        while self.Running:
            try:
                cmd = self.getline()
                self.__logger.debug('cmdin: Command "%s"', cmd)
                self.q_cmdin.put(cmd, block = True, timeout = 1)
            except queue.Full:
                self.__logger.error("cmdin: command queue full, command lost")

    def do_glg(self):
        """Send and process a GLG command
        """
        r = self.scanner.command('GLG')
        if self._lastcheck != r.response:
            self.__logger.debug("Checking: status=%s, sql=%r, mut=%r, response=%s", r.status, r.SQL, r.MUT, r.response)
            self._lastcheck = r.response
        try:
            if r.status == Response.RESP:
                self.glgmonitor.process(r)
            else:
                self.__logger.error("Unexpected GLG response: %s", r.status)
        except:
            self.__logger.exception('do_glg: Error processing "%s"', r.response)
            self.message('{}: Error processing GLG response, see log'.format(time.strftime(Scanmon._TIMEFMT)))

    def init_vol(self, args):
        self.VOLRE = re.compile(r'^(?P<value>(?:[+-])?\d+(?:\.\d+)?)(?P<db>db)?(?P<trail>[+-]?)$', re.I)
        basevol = self.VOLRE.search(args.basevolume)
        self.audiocard = args.card
        self.volcontrol = args.volcontrol
        if basevol and basevol.group('trail') != '':
            self.__logger.error('basevolume cannot be relative (%s)', Scanmon._DEFBASEVOL)
            basevol = None
        if not basevol:
            self.__logger.error('Invalid basevolume (%s), using %s', args.basevolume, Scanmon._DEFBASEVOL)
            basevol = self.VOLRE.search(Scanmon._DEFBASEVOL)
        assert basevol is not None, "Unable to parse basevolume. Tried '{}' and '{}'".format(args.basevolume, Scanmon._DEFBASEVOL)
        basevol = basevol.groupdict('')
        self.USEdB = basevol['db'] != ''
        try:
            basevalue = float(basevol['value']) if self.USEdB else int(basevol['value'])
        except:
            self.__logger.error("Error converting %s", basevol['value'])
            basevalue = int(Scanmon._DEFBASEVOL)
            self.USEdB = False
        self.voltable = {}
        if self.USEdB:
            factor = 1
            valstring = "{val:.1f}{db:s}"
        else:
            factor = args.dbfactor
            valstring = "{val:g}{db:s}"
        for k, v in Scanmon._ABSVOL.items():
            self.voltable[k] = valstring.format(val = basevalue + (v * factor), db = 'dB' if self.USEdB else '')
        for k, v in Scanmon._RELVOL.items():
            rv = v / factor if Scanmon._RELBROKEN else v
            self.voltable[k] = valstring.format(val = abs(rv), db = '+' if rv >= 0 else '-')
        for k,v in Scanmon._VOLALIAS.items():
            if v in self.voltable: self.voltable[k] = self.voltable[v]  # For convenience
        if args.volume:
            for vset in args.volume:
                k, p, v = vset.partition(':')
                self.voltable[k] = v
        self.__logger.info("Volume table initialized to: %r", self.voltable)

    def do_amixer(self, cmd, args = None):
        command = ['amixer']
        if self.audiocard:
            command.append('-D' + self.audiocard)
        command.append('--')
        command.append(cmd)
        command.append(self.volcontrol)
        if args:
            command.extend(args)
        try:
            resp = subprocess.check_output(command,
                stderr = subprocess.STDOUT,
                universal_newlines = True).splitlines()
            self.__logger.debug("amixer response: %r", resp)
        except subprocess.CalledProcessError as e:
            self.__logger.exception("%s command returned %s: :%s", e.cmd, e.returncode, e.output)
            self.message("Error getting/setting volume. See log.")
            resp = None

        return resp

    def _amixer_resp(self, resp):
        vline = resp[-1]
        vline = vline[vline.index(':'):]
        self.putline('resp', "Vol{}".format(vline))

    def _vol_help(self):
        help = \
        """Usage: vol[ume] [vol] ['mute'|'unmute']
             vol = A volume expression, relative volume expression or one of the keywords below

        Keywords:
        """.splitlines()
        hline = ""
        dispfmt = "{key:>8s}: {val:<8s}"
        rwin = self.respwin
        avail = rwin.width - rwin.borderright - rwin.borderleft
        cwidth = len(dispfmt.format(key = "key", val = "val"))  # Calculate the absolute column width
        avail -= cwidth * 2 + 3 # Minus the first and last colomns
        packing = int(avail / ( cwidth + 2)) + 2    # Middle columns have ', '

        for eo, k in enumerate(self.voltable.keys(), start = 1):
            hline += dispfmt.format(key = k, val = self.voltable[k])
            if eo % packing == 0:
                help.append(hline)
                hline = ''
            else:
                hline += ", "
        if hline != '': help.append(hline)
        help[-1] = help[-1].rstrip(", ")    # If there is extra
        for l in help:
            self.putline('resp', l)

    def do_mute(self, command, cmd):
        self.do_vol('vol ' + cmd[0], ['vol', cmd[0]])

    def do_vol(self, command, cmd):
        if len(cmd) > 1:
            cmds = cmd[1].split()
            newvol = self.VOLRE.search(cmds[0])
            if newvol is None:      # Not a valid volume, maybe a keyword?
                if cmds[0] in self.voltable:    # It's one of our keywords
                    cmds[0] = self.voltable[cmds[0]]
                elif cmds[0] in ('mute', 'unmute'): # One of these?
                    pass                            # Yes, that's OK
                else:
                    cmds = None     # Don't know, send help
            if cmds:
                resp = self.do_amixer('sset', args = cmds)
                if resp:
                    self._amixer_resp(resp)
            else:
                self._vol_help()
        else:
            resp = self.do_amixer('sget')
            if resp:
                self._amixer_resp(resp)

    def do_cmd(self, command, cmd):
        """Proccess a request to send a scanner command."""
        if len(cmd) > 1:
            try:
                r = self.scanner.command(cmd[1].upper())
                self.putline('resp', '{}: {}'.format(r.CMD, r.display(r)))
            except ScannerDecodeError as e:
                self.__logger.error("do_cmd: Error response from scanner: cmd: %s, error: %s", cmd, e)
                self.message("Error response from scanner: cmd: {}, error: {}".format(cmd, e))
        else:
            self.message('No scanner command found.')

    def do_autocmd(self, command, cmd):
        """Display or set/reset the autocommand setting."""
        if len(cmd) > 1:
            self.autocmd = cmd[1] == 'on'
        self.message("autocommand is {}".format('on' if self.autocmd else 'off'))

    def do_quit(self, command, cmd):
        """Process a quit command."""
        self.message('Quitting...')
        self.__logger.info('Quitting...')
        self.Running = False

    def dispatch_command(self, inputstr):
        """Process commands."""
        self.__logger.info('dispatch_command: Handling "%s"', inputstr)
        command = inputstr.strip()
        if len(command) > 0:
            cmd = command.split(None, 1)
            if cmd[0] in self.q_commands:
                self.q_commands[cmd[0]](command, cmd)
            elif self.autocmd:
                self.q_commands['cmd']("".join(('cmd ', inputstr)), ('cmd', inputstr))
            else:
                self.message('Unknown command: "{}"'.format(command))
                self.__logger.warning('cmd: Unknown command: %s', command)

    def run(self, args):
        """Initialize the window, initialize and start the threads
        Read and process commands from the monitor window.
        """

# Build the queues, use an arbitrary 10 as the maxsize
        MAXSIZE = 10
        self.q_cmdin = queue.Queue(maxsize=MAXSIZE) # Commands entered at the console
        self.q_commands = {}        # request to process commands
        self.q_commands['quit'] = self.do_quit  # We know who wants to see this
        self.q_commands['cmd'] = self.do_cmd    # We know who wants to see this
        self.q_commands['autocmd'] = self.do_autocmd    # We know who wants to see this
        self.q_commands['vol'] = self.do_vol    # volume setting
        self.q_commands['volume'] = self.do_vol # an alias
        self.q_commands['mute'] = self.do_mute  # A convenience command
        self.q_commands['unmute'] = self.do_mute    # A convenience command
        self.glgmonitor = GLGMonitor(monwin = self, args = self.__args)

        self.init_vol(args)         # Allow the vol command to see the args

        self.Running = True
        self.send_glg = True

        self.t_cmdin = threading.Thread(target = self.f_cmdin, name = "cmdin")
        self.t_cmdin.daemon = True  # We can ignore this on exit

# Start the threads
        self.t_cmdin.start()
        self.message("Scanner running - Model: {}, Version: {}".format(self.scanner.MDL, self.scanner.VER))

        last_glg = 0
        self._lastcheck = ''
        while self.Running:
            now = time.time()
            if self.send_glg and now - last_glg >= Scanmon._GLGTIME:
                last_glg = now
                self.do_glg()
            try:
                cmd = self.q_cmdin.get(block = False)
                self.dispatch_command(cmd)
            except queue.Empty:
                pass
            time.sleep(0.1)
        self.__logger.debug("%d threads: %s", threading.active_count(), list(threading.enumerate()))

    def close(self):
        self.scanner.close()
        super().close()

