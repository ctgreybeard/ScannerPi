"""A class and methods to control the Uniden BCD996XT scanner.

Classes: 
Scanner -- Defines data and control structures to control 
"""

import os
import stat

class Scanner:
	"""
	Scanner -- Defines data and control structures to control.

	Arguments:
		device -- Optional. The name of the USB Serial connection.
		This is usually "/dev/ttyUSB0" or "/dev/ttyUSB1". The class will attempt to use one or the other
		if the device is not indicated.

	Methods:
		readline -- Read one line of response from the scanner.
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
			devs = ("/dev/ttyUSB1", "/dev/ttyUSB0")
		else:
			devs = (device)

		self.device = None
		for d in devs:
			try:
				if stat.S_ISCHR(os.stat(d).st_mode):
					self.device = d
			except:
				pass

		if self.device is None:
			raise IOError("\"{}\" not found or not suitable".format(devs))
