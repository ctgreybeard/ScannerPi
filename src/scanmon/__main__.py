"""The main scanmon code. Evertything begines here."""

import sys
import time
import threading
import argparse
import io
import decimal
import datetime
import subprocess
import curses
import threading
import queue
from collections import deque
import logging
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL
import re

# Our own definitions
from .scanner import Scanner
from .scanner.formatter import Response
from .monwin import Monwin
from glgmonitor import GLGMonitor

class Scanmon:

# Class constants
	_logformat = "{asctime} {module}.{funcName} -{levelname}- *{threadName}* {message}"
	_TIMEFMT = '%H:%M:%S'
	_GLGTIME = 0.5	# Half second
	_EPOCH = 3600 * 24 * 356	# A year of seconds
	_DEFBASEVOL = '100'
	_ABSVOL = {'normal': 0, 'low': -3, 'verylow': -6, 'high': 3, 'veryhigh': 6}	# Adjustments from basevolume (units = dB)
	_RELVOL = {'down': -3, 'up': 3}		# Names for relative adjustments
# NOTE: For the Wolfson card the adjusments are amplified: 3dB+ goes up 6dB, 3+ goes up 3dB. This is a bug but I don't
#		know who to blame. 3+ should go up 3 UNITS which is 1.5dB, etc.
	_RELBROKEN = True
	_VOLALIAS = {'norm':'normal', 'vlow':'verylow', 'hi':'high', 'vhigh':'veryhigh', 'vhi':'veryhigh', 'dn':'down'}


	def __init__(self, args):
		self._args = args
		self.logger = logging.getLogger()
		self.logger.setLevel(LINFO)
		lfh = logging.FileHandler('scanmon.log')
		lfh.setLevel(LDEBUG)
		lfmt = logging.Formatter(fmt=Scanmon._logformat, style = '{')
		lfh.setFormatter(lfmt)
		self.logger.addHandler(lfh)
		self.logger.info("Scanmon initializing")
		self.scanner = Scanner(self._args.scanner)
		self.Running = False
		self.glgmonitor = GLGMonitor()
		self.autocmd = False
		if self._args.debug: self.logger.setLevel(LDEBUG)
		else: self.logger.setLevel(LINFO)

	def f_cmdin(self):
		"""Read input from the window and post to the command queue
		"""
		while self.Running:
			try:
				cmd = self.monwin.getline()
				self.logger.debug('cmdin: Command "%s"', cmd)
				self.q_cmdin.put(cmd, block = True, timeout = 1)
			except queue.Full:
				self.logger.error("cmdin: command queue full, command lost")

	def do_glg(self):
		"""Send and process a GLG command
		"""
		r = self.scanner.command('GLG')
		if self._lastcheck != r.response:
			self.logger.debug("Checking: status=%s, sql=%r, mut=%r, response=%s", r.status, r.SQL, r.MUT, r.response)
			self._lastcheck = r.response
		try:
			if r.status == Response.RESP:
				self.glgmonitor.process(r)
			else:
				self.logger.error("Unexpected GLG response: %s", r.status)
		except:
			self.logger.exception('do_glg: Error processing "%s"', r.response)
			self.monwin.message('{}: Error processing GLG response, see log'.format(time.strftime(Scanmon._TIMEFMT)))

	def init_vol(self, args):
		self.VOLRE = re.compile(r'(?P<value>(?:[+-])?\d+(?:\.\d+)?)(?P<db>db)?(?P<trail>[+-]?)', re.I)
		basevol = self.VOLRE.search(args.basevolume)
		self.audiocard = args.card
		self.volcontrol = args.volcontrol
		if basevol and basevol.group('trail') != '':
			self.logger.error('basevolume cannot be relative (%s)', Scanmon._DEFBASEVOL)
			basevol = None
		if not basevol:
			self.logger.error('Invalid basevolume (%s), using %s', args.basevolume, Scanmon._DEFBASEVOL)
			basevol = self.VOLRE.search(Scanmon._DEFBASEVOL)
		assert basevol is not None, "Unable to parse basevolume. Tried '{}' and '{}'".format(args.basevolume, Scanmon._DEFBASEVOL)
		basevol = basevol.groupdict('')
		self.USEdB = basevol['db'] != ''
		try:
			basevalue = float(basevol['value']) if self.USEdB else int(basevol['value'])
		except:
			self.logger.error("Error converting %s", basevol['value'])
			basevalue = int(Scanmon._DEFBASEVOL)
			self.USEdB = False
		self.voltable = {}
		if self.USEdB:
			factor = 1
			valstring = "{val:.1f}{db:s}"
		else:
			factor = args.dbfactor
			valstring = "{val:d}{db:s}"
		for k, v in Scanmon._ABSVOL.items():
			self.voltable[k] = valstring.format(val = basevalue + (v * factor), db = 'dB' if self.USEdB else '')
		for k, v in Scanmon._RELVOL.items():
			rv = v / factor if Scanmon._RELBROKEN else v
			self.voltable[k] = valstring.format(val = abs(rv), db = '+' if rv >= 0 else '-')
		for k,v in Scanmon._VOLALIAS.items():
			if v in self.voltable: self.voltable[k] = self.voltable[v]	# For convenience
		if args.volume:
			for vset in args.volume:
				k, p, v = vset.partition(':')
				self.voltable[k] = v
		self.logger.info("Volume table initialized to: %r", self.voltable)

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
			self.logger.debug("amixer response: %r", resp)
		except subprocess.CalledProcessError as e:
			self.logger.exception("%s command returned %s: :%s", e.cmd, e.returncode, e.output)
			self.monwin.message("Error getting/setting volume. See log.")
			resp = None

		return resp

	def _amixer_resp(self, resp):
		vline = resp[-1]
		vline = vline[vline.index(':'):]
		self.monwin.putline('resp', "Vol{}".format(vline))

	def _vol_help(self):
		help = \
"""Usage: vol[ume] [vol] ['mute'|'unmute']
     vol = A volume expression, relative volume expression or one of the keywords below

Keywords:
""".splitlines()
		hline = ""
		dispfmt = "{key:>8s}: {val:<8s}"
		rwin = self.monwin.respwin
		avail = rwin.width - rwin.borderright - rwin.borderleft
		cwidth = len(dispfmt.format(key = "key", val = "val"))	# Calculate the absolute column width
		avail -= cwidth * 2 + 3	# Minus the first and last colomns
		packing = int(avail / ( cwidth + 2)) + 2	# Middle columns have ', '

		for eo, k in enumerate(self.voltable.keys(), start = 1):
			hline += dispfmt.format(key = k, val = self.voltable[k])
			if eo % packing == 0:
				help.append(hline)
				hline = ''
			else:
				hline += ", "
		if hline != '': help.append(hline)
		help[-1] = help[-1].rstrip(", ")	# If there is extra
		for l in help:
			self.monwin.putline('resp', l)

	def do_mute(self, command, cmd):
		self.do_vol('vol ' + cmd[0], ['vol', cmd[0]])

	def do_vol(self, command, cmd):
		if len(cmd) > 1:
			cmds = cmd[1].split()
			newvol = self.VOLRE.search(cmds[0])
			if newvol is None:		# Not a valid volume, maybe a keyword?
				if cmds[0] in self.voltable:	# It's one of our keywords
					cmds[0] = self.voltable[cmds[0]]
				elif cmds[0] in ('mute', 'unmute'):	# One of these?
					pass							# Yes, that's OK
				else:
					cmds = None		# Don't know, send help
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
			r = self.scanner.command(cmd[1].upper())
			self.monwin.putline('resp', '{}: {}'.format(r.CMD, r.display(r)))
		else:
			self.monwin.message('No scanner command found.')

	def do_autocmd(self, command, cmd):
		"""Display or set/reset the autocommand setting."""
		if len(cmd) > 1:
			self.autocmd = cmd[1] == 'on'
		self.monwin.message("autocommand is {}".format('on' if self.autocmd else 'off'))

	def do_quit(self, command, cmd):
		"""Process a quit command."""
		self.monwin.message('Quitting...')
		self.logger.info('Quitting...')
		self.Running = False

	def dispatch_command(self, inputstr):
		"""Process commands."""
		self.logger.info('dispatch_command: Handling "%s"', inputstr)
		command = inputstr.strip()
		if len(command) > 0:
			cmd = command.split(None, 1)
			if cmd[0] in self.q_commands:
				self.q_commands[cmd[0]](command, cmd)
			elif self.autocmd:
				self.q_commands['cmd']("".join(('cmd ', inputstr)), ('cmd', inputstr))
			else:
				self.monwin.message('Unknown command: "{}"'.format(command))
				self.logger.warning('cmd: Unknown command: %s', command)

	def main(self, stdscr, args):
		"""Initialize the curses window, initialize and start the threads
		Read and process commands from the monitor window.
		"""

		self.monwin = Monwin(stdscr, args)

# Build the queues, use an arbitrary 10 as the maxsize
		MAXSIZE = 10
		self.q_cmdin = queue.Queue(maxsize=MAXSIZE)	# Commands entered at the console
		self.q_commands = {}		# request to process commands
		self.q_commands['quit'] = self.do_quit	# We know who wants to see this
		self.q_commands['cmd'] = self.do_cmd	# We know who wants to see this
		self.q_commands['autocmd'] = self.do_autocmd	# We know who wants to see this
		self.q_commands['vol'] = self.do_vol	# volume setting
		self.q_commands['volume'] = self.do_vol	# an alias
		self.q_commands['mute'] = self.do_mute	# A convenience command
		self.q_commands['unmute'] = self.do_mute	# A convenience command

		self.init_vol(args)			# Allow the vol command to see the args

		self.Running = True
		self.send_glg = True

		self.t_cmdin = threading.Thread(target = self.f_cmdin, name = "cmdin")
		self.t_cmdin.daemon = True	# We can ignore this on exit

# Start the threads
		self.t_cmdin.start()
		self.monwin.message("Scanner running - Model: {}, Version: {}".format(self.scanner.MDL, self.scanner.VER))

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
		self.logger.debug("%d threads: %s", threading.active_count(), list(threading.enumerate()))
		self.logger.debug("glgmonitor.lastseen=%s", self.glgmonitor.lastseen)

	def close(self):
		self.scanner.close()
		self.monwin.close()

if __name__ == '__main__':
# Options definition
	parser = argparse.ArgumentParser(description = "Monitor and control the scanner", prog = "scanmon")
	parser.add_argument("-s", "--scanner",
		required = False,
		action = 'append',
		help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
	parser.add_argument("-d", "--debug",
		required = False,
		default = False,
		action = 'store_true',
		help="Debugging flag, default False")
	colorhelp = " text color index (0 to 63)"
	parser.add_argument("--color-norm",
		required = False,
		help = "Normal" + colorhelp,
		type = int)
	parser.add_argument("--color-alert",
		required = False,
		help = "Alert" + colorhelp,
		type = int)
	parser.add_argument("--color-warn",
		required = False,
		help = "Warning" + colorhelp,
		type = int)
	parser.add_argument("--color-green",
		required = False,
		help = "Green" + colorhelp,
		type = int)
	parser.add_argument("--database",
		required = False,
		default = "scanmon.db",
		help = "File name for the database",
		type = str)
	parser.add_argument("--card",
		required = False,
		help = "The card used by the 'vol' command.This is sent verbatim the to 'amixer' command as '-c[card]'")
	parser.add_argument("--volcontrol",
		required = False,
		type = str,
		default = "HPOUT2 Digital",
		help = "The simple mixer control for setting volume.")
	parser.add_argument("--basevolume",
		required = False,
		default = Scanmon._DEFBASEVOL,
		type = str,
		help = "The setting for the 'norm' volume setting. Other settings go up or down from this. May be set in units or dB.")
	parser.add_argument("--volume",
		required = False,
		action = 'append',
		type = str,
		help = "A volume point given as 'name:set' (ex. vlow:90 -or- norm:-15dB). These are merged with the standard settings (verylow/vlow, low, normal/norm, high/hi, veryhigh/vhi)")
	parser.add_argument("--vstep",
		required = False,
		default = None,
		help = "Step difference between settings (i.e. 'norm' to 'high', etc.) Defaults to 3dB or 6 units.")
	parser.add_argument("--dbfactor",
		required = False,
		default = 2,
		type = int,
		help = "Multiplication factor to change dB to UNITs")
	args = parser.parse_args()

	SCANNER = Scanmon(args)

	curses.wrapper(SCANNER.main, args)
	SCANNER.close()


