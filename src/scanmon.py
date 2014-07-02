#!/usr/bin/env python3

import sys
import time
import threading
import argparse
import io
import subprocess
import curses
import threading
import queue
from collections import deque
import logging
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL

# Our own definitions
from scanner import Scanner
from monwin import Monwin

_logformat = "{asctime} {module}.{funcName} -{levelname}- *{threadName}* {message}"
_TIMEFMT = '%H:%M:%S'
_GLGTIME = 0.5	# Half second

class Scanmon:

	def __init__(self, scandevice):
		self.logger = logging.getLogger('scanmon')
		self.logger.setLevel(LDEBUG)
		lfh = logging.FileHandler('scanmon.log')
		lfh.setLevel(LDEBUG)
		lfmt = logging.Formatter(fmt=_logformat, style = '{')
		lfh.setFormatter(lfmt)
		self.logger.addHandler(lfh)
		self.logger.info("Scanmon initializing")
		self.scanner = Scanner(scandevice)
		self.Running = False

	def f_scanout(self):
		"""Monitor the scanout queue and send any commands to the scanner
		"""
		while self.Running:
			try:
				msg = self.q_scanout.get(block = True, timeout = 1)
				self.logger.info("scanout: Sending \"%s\"", msg)
				self.scanner.writeline(msg)
			except queue.Empty:
				pass

	def f_scanin(self):
		"""Read input from the scanner and post to the scanin queue
		"""
		while self.Running:
			try:
				msg = self.scanner.readline()
				if msg:
					self.logger.debug('scanin: Received "%s"', msg)
					self.q_scanin.put(msg, block = True, timeout = 1)
			except queue.Full:
				self.logger.error("scanin: scanin queue full, msg lost")

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

	def do_glg(self, response):
		"""Process a GLG response
		"""
		try:
			cmd, frq, mod, att, ctss, name1, name2, name3, sql, mut, sys_tag, chan_tag, p25nac = response.split(',')
			if name1:
				self.monwin.putline('glg', "{}: Sys={}, Grp={}, Chan={}, Freq={}".format(time.strftime(_TIMEFMT), name1, name2, name3, frq))
		except:
			self.monwin.message('{}: Error processing GLG response, see log'.format(time.strftime(_TIMEFMT)))
			self.logger.error('do_glg: Error processing "%s"', response)

	def do_quit(self, command):
		"""Process a quit command
		"""
		self.monwin.message('Quitting...')
		self.logger.info('Quitting...')
		self.Running = False

	def dispatch_command(self, command):
		"""Process commands
		"""
		self.logger.debug('dispatch_command: Handling "%s"', command)
		cmd = command.split(None, 1)
		if len(cmd) > 0 and cmd[0] in self.q_commands:
			self.q_commands[cmd[0]](command)
		else:
			self.monwin.message('Unknown command: "{}"'.format(command))
			self.logger.warning('cmd: Unknown command: %s', command)

	def do_response(self, response):
		"""Process an unrequested response
		"""
		self.monwin.putline('resp', "{}: Resp=".format(time.strftime(_TIMEFMT), response))

	def dispatch_resp(self, response):
		"""Receive response messages and call the registered handler
		"""
		cmd = response.split(',', 1)
		if len(cmd) > 0 and cmd[0] in self.q_response:
			self.q_response[cmd[0]](response)
		else:
			self.do_response(response)

	def main(self, stdscr):
		"""Initialize the curses window, initialize and start the threads
		Read and process commands from the monitor window.
		"""

		self.monwin = Monwin(stdscr)

# Build the queues, use an arbitrary 10 as the maxsize
		MAXSIZE = 10
		self.q_scanout = queue.Queue(maxsize=MAXSIZE)	# Output to the scanner
		self.q_scanin = queue.Queue(maxsize=MAXSIZE)	# Responses from the scanner
		self.q_cmdin = queue.Queue(maxsize=MAXSIZE)	# Commands entered at the console
		self.q_response = {}		# request to receive responses
		self.q_response['GLG'] = self.do_glg	# We know who wants to see GLG responses
		self.q_commands = {}		# request to process commands
		self.q_commands['quit'] = self.do_quit	# We know who wants to see this

		self.Running = True
		self.send_glg = True

		self.t_scanout = threading.Thread(target = self.f_scanout, name = "scanout")
		self.t_scanin = threading.Thread(target = self.f_scanin, name = "scanin")
		self.t_cmdin = threading.Thread(target = self.f_cmdin, name = "cmdin")
		self.t_cmdin.daemon = True	# We can ignore this on exit

# Start the threads
		self.t_scanout.start()
		self.t_scanin.start()
		self.t_cmdin.start()

		last_glg = 0
		while self.Running:
			if self.send_glg and time.time() - last_glg >= _GLGTIME:
				last_glg = time.time()
				try:
					self.q_scanout.put('GLG', block = False)
				except queue.Full:
					self.logger.error("main: scanout queue full, GLG lost")
				try:
					resp = self.q_scanin.get(block = False)
					self.dispatch_resp(resp)
				except queue.Empty:
					pass
				try:
					cmd = self.q_cmdin.get(block = False)
					self.dispatch_command(cmd)
				except queue.Empty:
					pass
			time.sleep(0.1)
		# Done running, wait a bit for everything to shut down
		for n in range(10):
			active = False
			for t in (self.t_scanout, self.t_scanin):
				active |= t.is_alive()
			if not active: break
			time.sleep(0.5)
		self.logger.debug("%d threads: %s", threading.active_count(), list(threading.enumerate()))

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
	args = parser.parse_args()

	SCANNER = Scanmon(args.scanner)

	curses.wrapper(SCANNER.main)
	SCANNER.close()


