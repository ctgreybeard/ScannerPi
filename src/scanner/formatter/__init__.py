"""Format decoders and encoder for Uniden BCDX96XT scanner
"""

import sys
import logging
from datetime import datetime as DateTime

class ScannerDecodeError(TypeError):
	"""A generic error for decoders to use."""
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

def gendecode(response):
	"""Generalized decoder. Disassemble using the supplied or default varlist."""
	for i, v in enumerate(response.parts):
		var = response.varlist[i] if i < len(response.varlist) else 'VAR'
		response.addvalue(var, v)


def gendisplay(response):
	"""Generalized display. Just assemble the parts."""
	try:
		resp = ','.join(response.parts[1:])
	except:
		resp = '?'
	return resp

class Response:
	"""A generic response class. Handles deconstruction of arbitrary scanner responses.

	Attributes:
		CMD -- The first word of the response or Null
		status -- 'OK', 'NG', 'ERR', or 'DECODEERROR'
			OK -- Response was 'OK' or response was decoded correctly
			NG -- Response was 'NG' (Command invalid at this time)
			ERR -- Error response from scanner (Command format error / Value error, Framing error, Overrun error)
		response -- The original response string (trailing '\r' removed if any existed)
		parts -- ordered list of the parsed response
		*values* -- decoded terms. Names are in UPPER CASE as given in the BCD396XT Complete Reference
			This is implemented such that ANY upper case name is available to be retrieved.
			Names not set by the response return None.
			Duplicate names (typically "RSV") are numbered from 1 after the first: RSV, RSV1, RSV2, etc.
	"""

# Class variables
	OK = 'OK'
	NG = 'NG'
	ERR = 'ERR'
	FER = 'FER'
	ORER = 'ORER'
	DECODEERROR = 'DECODEERROR'
	RESP = 'RESP'

# Maximum loop count correcting name collisions in __setattr__()
	MAXi = 100


	def __init__(self, response):
		"""Initialize the instance, load a specific format if available.

		Arguments:
		response -- The returned string from the scanner

		Process:
		Separate the pieces of the response using ',' separator
		If a first piece exists look for a decoder for it
		Load and execute the appropriate decoder if found
		Otherwise decode by separating the parts using ','
		If the second piece is 'Response.ERR' or 'Response.NG' set the error flags appropriately
		If the response is Null or None set the error flags
		"""

		# Ensure that we have values for the necessary attributes
		self.cmd = '?'
		self.response = ''
		self.parts = tuple()
		self.TIME = DateTime.now()
		self.display = gendisplay
		self.varlist = ('CMD',)		# Default variable list

		if response:
		# Something is there, look further
			self.response = response.rstrip('\r')
			self.parts = self.response.split(',')
			if len(self.parts) < 2:		# Not exactly sure what this is but it's not good
				raise ScannerDecodeError("Invalid response ({}) from scanner".format(self.response))
			self.cmd = self.parts[0]
			if len(self.parts) == 2:	# Probably just an simple response
				if self.parts[1] in (Response.OK, Response.NG, Response.FER, Response.ORER):
					# Bypass our __setattr__ trap
					object.__setattr__(self, 'CMD', self.parts[0])
					object.__setattr__(self, 'RESP', self.parts[1])
					self.status = self.parts[1]
					return	# We are done ...
			# We got here with something. Let's deconstruct it
			self.status = Response.RESP
			decode = gendecode
			try:
				handler = __import__(self.cmd, globals(), locals(), None, 1)
				if hasattr(handler, 'decode'):
					decode = handler.decode
				elif hasattr(handler, 'varlist'):
					self.varlist = handler.varlist

				if hasattr(handler, 'display'):
					self.display = handler.display
			except ImportError as e:			# In case there is no handler my that name ...
				logging.warning(repr(e))		# Note: we do not have an instance logger because we are short lived

			decode(self)
			# We are done ...

		elif response is None:
		# We can't handle 'None', it's a big error
			raise ScannerDecodeError("'None' is invalid as a response")
		else:
		# Must be a Null response. This isn't good but isn't fatal
			self.cmd = ''
			self.status = Response.DECODEERROR

	def __str__(self):
		"""Return whatever was set during initialization."""
		return self.display(self)

	def addvalue(self, name, value):
		"""Add a response value making sure the name is upper case."""
		self.__setattr__(name.upper(), value)

	def __setattr__(self, name, value):
		"""Add a response value to this response.

		If the name already exists then append digits, incrementing until the name is unique.
		Note: getattr() cannot be used because we implement __getattr__ to return values for
		non-existent values.
		"""
		vname = name
		if name == name.upper():		# An uppercase name?
			try:
				object.__getattribute__(self, vname)		# Check if we already have one of these
				# If we get here then there is already one ...
				i = 1
				while True:
					vname = "{}{}".format(name, i)
					# We could do this with recursion but this is simpler
					object.__getattribute__(self, vname)	# Test if it's still there
					# Still there, try the next
					i += 1
					if i > Response.MAXi: raise TypeError("too many iterations")
			except AttributeError:
				pass	# The error that isn't an error

		object.__setattr__(self, vname, value)

	def __getattr__(self, name):
		"""Called ONLY if the requested attribute does NOT exist. For response variables we return None."""
		if name == name.upper():	# All uppercase?
			return None
		raise AttributeError("{} not found".format(name))

	def __getitem__(self, key):
		"""Convenience method to allow use of str.format_map()"""
		if key == key.upper():			# ONLY response variables allowed
			return getattr(self, key)
		raise IndexError("key not a response variable")

