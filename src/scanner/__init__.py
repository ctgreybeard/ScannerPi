"""A class and methods to control the Uniden BCD996XT scanner.

Classes: 
Scanner -- Defines data and control structures to control 
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
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL
from threading import RLock

from .formatter import Response

# Internal constants
_ENCERRORS = 'ques'
_ENCODING = 'ascii'
_NEWLINE = '\r'
_TIMEOUT = 0.1
_BAUDRATE = 115200
_DEVS = ("/dev/ttyUSB0", "/dev/ttyUSB1")

def _decodeerror(decodeerror):
	"""Simple static decoder error routine to simply replace errors with a '?'
	"""
	return ('?' * (decodeerror.end - decodeerror.start), decodeerror.end, )

codecs.register_error(_ENCERRORS, _decodeerror)

def _setio(ttyio):
	"""Use termios to set the tty attributes the way we like. Only make changes if necessary.
	"""
	attrs = termios.tcgetattr(ttyio)
	nattrs = copy.deepcopy(attrs)
	iflag, oflag, cflag, lflag, ispeed, ospeed, cc = list(range(7))
    # Shamefully stolen from http://en.wikibooks.org/wiki/Serial_Programming/termios
	# Input flags - Turn off input processing
	# convert break to null byte, no CR to NL translation,
	# no NL to CR translation, don't mark parity errors or breaks
	# no input parity check, don't strip high bit off,
	# no XON/XOFF software flow control
	#
	nattrs[iflag] &= ~(termios.IGNBRK | termios.BRKINT | termios.ICRNL |
		termios.INLCR | termios.PARMRK | termios.INPCK | termios.ISTRIP | termios.IXON)

	# Output flags - Turn off output processing
	# no CR to NL translation, no NL to CR-NL translation,
	# no NL to CR translation, no column 0 CR suppression,
	# no Ctrl-D suppression, no fill characters, no case mapping,
	# no local output processing

	nattrs[oflag] &= ~(termios.OCRNL | termios.ONLCR | termios.ONLRET |
		termios.ONOCR | termios.OFILL | termios.OLCUC | termios.OPOST);

	# No line processing:
	# echo off, echo newline off, canonical mode off, 
	# extended input processing off, signal chars off

	attrs[lflag] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.IEXTEN | termios.ISIG);

	# Turn off character processing
	# clear current char size mask, no parity checking,
	# no output processing, force 8 bit input

	nattrs[cflag] &= ~(termios.CSIZE | termios.PARENB);
	nattrs[cflag] |= termios.CS8;

	# One input byte is enough to return from read()
	# Inter-character timer off

	nattrs[cc][termios.VMIN]  = 1;
	nattrs[cc][termios.VTIME] = 0;

	# Communication speed (simple version, using the predefined
	# constants)

	nattrs[ispeed] = termios.B115200
	nattrs[ospeed] = termios.B115200

	if attrs != nattrs:
		termios.tcsetattr(ttyio, termios.TCSAFLUSH, nattrs)

class Scanner:
	"""
	Scanner -- Defines data and control structures to control.

	Arguments:
		device -- Optional. The name of the USB Serial connection.
		This is usually "/dev/ttyUSB0" or "/dev/ttyUSB1". The class will attempt to use one or the other
		if the device is not indicated.

	Methods:
		readline -- Read one line of response from the scanner.
		writeline -- Write one line of text to the scanner
		close    -- Cease operations on the scanner.
		reopen   -- Reopen a closed connection to the scanner
	"""

	def __init__(self, device = None):
		"""Initialize the class instance.

		Arguments:
		device -- The name of the scanner device. Usually "/dev/ttyUSB0" or "/dev/ttyUSB1"

		Initialization will try to figure out what to use if the argumant is omitted.
		"""

# Initialize the logger
		self.logger = logging.getLogger().getChild(__name__)
		self.logger.info("Initializing scanner")
		self.iolock = RLock()
		if device is None:
			devs = _DEVS
		elif isinstance(device, str):
			devs = (device, )
		else:
			devs = device

		self.device = None
		for d in devs:
			try:
				if stat.S_ISCHR(os.stat(d).st_mode) and os.access(d, os.W_OK):
					self.device = d
					break	# We found it
			except:
				pass

		if self.device is None:
			self.logger.critical("scanner: \"%s\" not found or not suitable", devs)
			raise IOError("\"{}\" not found or not suitable".format(devs))

		try:
			self._serscanner = serial.Serial(port = self.device, baudrate = _BAUDRATE, timeout = _TIMEOUT)
		except serial.SerialException as serexcept:
			self.logger.critical("scanner: \"%s\" not accessable", self.device)
			raise serexcept

		_setio(self._serscanner)
		self._serscanner.flushInput()
		self._serscanner.flushOutput()

		self._scanio = io.TextIOWrapper(io.BufferedRWPair(self._serscanner, self._serscanner), 
			errors = _ENCERRORS, encoding = _ENCODING, newline = _NEWLINE)
		for c in ('MDL', 'VER'):
			r = self.command(c)
			if r.status == Response.RESP:
				setattr(self, c, r.parts[1])
			else:
				raise IOError("Scanner did not properly respond to {} command, status={}".format(c, r.status))

	def close(self):
		"""Close the streams from and to the scanner.
		"""
		if self._serscanner:
			self._serscanner.close()

	def readline(self):
		"""Read an input line from the scanner.
		Note that this is a non-blocking read, it will timeout in _TIMEOUT seconds.
		"""
		with self.iolock:
			response = self._scanio.readline()

			if response and isinstance(response, str):
				response = response.rstrip(_NEWLINE)

		return response
		
	def writeline(self, line):
		"""Write a line to the scanner.
		Note that this is a blocking write but there should be no reason for it to block.
		"""
		with self.iolock:
			written = self._scanio.write(line)
			# Send the '\r' newline
			self._scanio.write(_NEWLINE)
			# And flush all output completely
			self._scanio.flush()
			self._serscanner.flushOutput()

		return written + 1
		
	def command(self, cmdline):
		"""Send one command, read the response, apply formatting and return the result."""
		with self.iolock:
			self.writeline(cmdline)
			reply = self.readline()

		return Response(reply)
