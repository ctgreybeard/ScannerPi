"""A class and methods to control the Uniden BCD996XT scanner.

Classes: 
Scanner -- Defines data and control structures to control 
"""

import os
import stat
import subprocess

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
		if device is None:
			devs = ("/dev/ttyUSB0", "/dev/ttyUSB1")
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
			raise IOError("\"{}\" not found or not suitable".format(devs))

		rc = subprocess.call("stty --file {} ispeed 115200 ospeed 115200 -echo -ocrnl onlcr".format(self.device).split())
		if rc != 0:
			raise IOError("Unable to initialize \"{}\"".format(self.device))

		self._readio = open(self.device, mode = 'rt', buffering = 1, newline = '\r')
		self._writeio = open(self.device, mode = 'wt', buffering = 1, newline = '\r')

	def close(self):
		self._readio.close()
		self._writeio.close()
