"""A class and methods to control the Uniden BCD996XT scanner.

Classes: 
Scanner -- Defines data and control structures to control 
"""

import os
import stat
import termios
import copy
import codecs
import logging
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL

# Internal constants
_ENCODING = 'ascii'

def _decodeerror(decodeerror):
	"""Simple static decoder error routine to simply replace errors with a '?'
	"""
	return ('?' * (decodeerror.end - decodeerror.start), decodeerror.end, )

def _setio(ttyio):
	"""Use termios to set the tty attributs the way we like. Only make changes as necessary.
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

# Initialize th logger
		self.logger = logging.getLogger('scanmon.scanner')
		self.logger.info("Initializing scanner")
		if device is None:
			devs = ("/dev/ttyUSB0", "/dev/ttyUSB1")
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

		codecs.register_error('ques', _decodeerror)

# Ensure we can open it in both mods
		self._readio = open(self.device, mode = 'rt', buffering = 1, newline = '\r', encoding = _ENCODING, errors = 'ques')
		assert not self._readio.closed, "Unable to open {} for reading".format(self.device)
		if not self._readio.isatty():
			raise IOError("\"{}\" not suitable (not a tty)".format(self.device))
		_setio(self._readio)
		self._readio.close()
		self._writeio = open(self.device, mode = 'wt', buffering = 1, newline = '\r', encoding = _ENCODING)
		assert not self._writeio.closed, "Unable to open {} for writing".format(self.device)
		if not self._writeio.isatty():
			raise IOError("\"{}\" not suitable (not a tty)".format(self.device))
		_setio(self._writeio)
		self._writeio.close()

	def close(self):
		"""Close the streams from and to the scanner.
		"""
		if self._readio:
			self._readio.close()
		if self._writeio:
			self._writeio.close()

	def readline(self):
		"""Read an input line from the scanner.
		Note that this is a blocking read and should be executed in a separate thread.
		"""
		self._readio = open(self.device, mode = 'rt', buffering = 1, newline = '\r', encoding = _ENCODING, errors = 'ques')
		setio(self._readio)
		self._readio.close()
		
	def writeline(self):
		"""Write a line to the scanner.
		Note that this is a non-blocking write
		"""
		self._writeio = open(self.device, mode = 'wt', buffering = 1, newline = '\r', encoding = _ENCODING)
		setio(self._readio)
		self._readio.close()
		
