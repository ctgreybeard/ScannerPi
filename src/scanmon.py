#!/usr/bin/env python3

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

# Our own definitions
from scanner import Scanner
from scanner.formatter import Response
from monwin import Monwin

class Scanmon:

# Class constants
	_logformat = "{asctime} {module}.{funcName} -{levelname}- *{threadName}* {message}"
	_TIMEFMT = '%H:%M:%S'
	_GLGTIME = 0.5	# Half second
	_EPOCH = 3600 * 24 * 356	# A year of seconds

# Inner class for GLG monitoring
	class GLGinfo:
		"""Class to hold monitoring info for GLG monitoring."""

		IDLE = 15.0		# 15 seconds between transmissions is a new transmission

# Class method
		def id(r):
			return '-'.join((r.NAME1, r.NAME2, r.NAME3))

		def __init__(self):
			self.lastseen = {}
			self.lastid = ''
			self.lastsql = False
			self.lasttime = time.time()

		def logoff(self):
			"""Log a squelch off event"""
			if self.lastsql == True:
				self.loglast()

		def logon(self, r):
			id = Scanmon.GLGinfo.id(r)
			now = time.time()
			if id != self.lastid or now - self.lasttime > Scanmon.GLGinfo.IDLE:
				self.loglast()
				self.logthis(id, now)
			self.lasttime = now

		def logit(self, r):
			self.rval = False	# Assume we don't print this
			heard = r.SQL == '1' and r.MUT == '0'
			if heard:
				self.logon(r)
			else:
				self.logoff()
			self.lastsql = bool(r.SQL)
			return self.rval

		def loglast(self):
			self.lastseen[self.lastid] = self.lasttime

		def logthis(self, id, now):
			self.rval = now - ( self.lastseen[id] if id in self.lastseen else 0 )
			self.lastseen[id] = now
			self.lastid = id


	def __init__(self, scandevice):
		self.logger = logging.getLogger()
		self.logger.setLevel(LINFO)
		lfh = logging.FileHandler('scanmon.log')
		lfh.setLevel(LDEBUG)
		lfmt = logging.Formatter(fmt=Scanmon._logformat, style = '{')
		lfh.setFormatter(lfmt)
		self.logger.addHandler(lfh)
		self.logger.info("Scanmon initializing")
		self.scanner = Scanner(scandevice)
		self.Running = False
		self.glginfo = Scanmon.GLGinfo()
		self.autocmd = False

	def setDebug(self, debug):
		if debug: self.logger.setLevel(LDEBUG)
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
				dur = int(self.glginfo.logit(r))
				if bool(dur):
					try:
						frq = float(r.FRQ_TGID)
					except ValueError:
						frq = decimal.Decimal('NaN')
					self.monwin.putline('glg', 
						"{0}: Sys={1:.<16s}|Grp={2:.<16s}|Chan={3:.<16s}|Freq={4:#9.4f}|C/D={6:>3s} since={5}".\
						format(r.TIME.strftime(Scanmon._TIMEFMT), r.NAME1, r.NAME2, r.NAME3, frq, 
						str(datetime.timedelta(seconds=dur)) if dur < Scanmon._EPOCH else 'Forever', r.CTCSS_DCS))
			else:
				self.logger.error("Unexpected GLG response: %s", r.status)
		except:
			self.logger.exception('do_glg: Error processing "%s"', r.response)
			self.monwin.message('{}: Error processing GLG response, see log'.format(time.strftime(Scanmon._TIMEFMT)))

	def do_cmd(self, command, cmd):
		"""Proccess a request to send a scanner command."""
		if len(cmd) > 1:
			r = self.scanner.command(cmd[1].upper())
			self.monwin.putline('resp', '{}: {}'.format(r.CMD, r.response))
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

	def main(self, stdscr):
		"""Initialize the curses window, initialize and start the threads
		Read and process commands from the monitor window.
		"""

		self.monwin = Monwin(stdscr)

# Build the queues, use an arbitrary 10 as the maxsize
		MAXSIZE = 10
		self.q_cmdin = queue.Queue(maxsize=MAXSIZE)	# Commands entered at the console
		self.q_commands = {}		# request to process commands
		self.q_commands['quit'] = self.do_quit	# We know who wants to see this
		self.q_commands['cmd'] = self.do_cmd	# We know who wants to see this
		self.q_commands['autocmd'] = self.do_autocmd	# We know who wants to see this

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
		self.logger.debug("glginfo.lastseen=%s", self.glginfo.lastseen)

	def close(self):
		self.scanner.close()
		self.monwin.close()

if __name__ == '__main__':
# Options definition
	parser = argparse.ArgumentParser(description = "Monitor and control the scanner")
	parser.add_argument("-s", "--scanner", 
		required = False, 
		action = 'append',
		help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
	parser.add_argument("-d", "--debug",
		required = False,
		default = False,
		action = 'store_true',
		help="Debugging flag, default False")
	args = parser.parse_args()

	SCANNER = Scanmon(args.scanner)
	SCANNER.setDebug(args.debug)

	curses.wrapper(SCANNER.main)
	SCANNER.close()


