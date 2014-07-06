"""Format decoders and encoder for Uniden BCDX96XT scanner
"""

import datetime

# Class variables
OK = 'OK'
NG = 'NG'
ERR = 'ERR'
FER = 'FER'
ORER = 'ORER'
DECODEERROR = 'DECODEERROR'

class ScannerDecodeError(TypeError):
	"""A generic error for decoders to use."""
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

def gendecode(response):	# A generic handler
	for i, t in enumerate(response.parts):
		exec('response.val["var{}"] = """{}"""'.format(i, t))


def gendisplay(response):
	try:
		resp = ','.join(response.parts)
	except:
		resp = '?'
	return resp

class Response:
	"""A generic response class. Handles deconstruction of arbitrary scanner responses.

	Attributes:
		cmd -- The first word of the response or Null
		status -- 'OK', 'NG', 'ERR', or 'DECODEERROR'
			OK -- Response was 'OK' or response was decoded correctly
			NG -- Response was 'NG' (Command invalid at this time)
			ERR -- Error response from scanner (Command format error / Value error, Framing error, Overrun error)
		response -- The original response string (trailing '\r' removed if any existed)
		parts -- ordered list of the parsed response
		val -- dictionary of the decoded terms. For responses with no specific decoder this is empty.
	"""

	def __init__(self, response):
		"""Initialize the instance, load a specific format if available

		Arguments:
		response -- The returned string from the scanner

		Process:
		Separate the pieces of the response using ',' separator
		If a first piece exists look for a decoder for it
		Load and execute the appropriate decoder if found
		Otherwise decode by separating the parts using ','
		If the second piece is 'ERR' or 'NG' set the error flags appropriately
		If the response is Null or None set the error flags
		"""

		# Ensure that we have values for the necessary attributes
		self.cmd = '?'
		self.status = ''
		self.response = ''
		self.parts = tuple()
		self.val = dict()
		self.time = datetime.datetime.now()
		self.display = gendisplay

		if response:
		# Something is there, look further
			self.response = response.rstrip('\r')
			self.parts = self.response.split(',')
			if len(self.parts) < 2:		# Not exactly sure what this is but it's not good
				raise ScannerDecodeError("Invalid response ({}) from scanner".format(self.response))
			self.cmd = self.parts[0]
			if len(self.parts) == 2:	# Probably just an simple response
				if self.parts[1] in (OK, NG, FER, ORER):
					self.status = self.parts[1]
					return	# We are done ...
			# We got here with something. Let's deconstruct it
			decode = gendecode
			try:
				handler = __import__('formatter.{}'.format(self.cmd), globals(), locals(), ['decode'], 2)
				if hasattr(handler, 'decode'):
					decode = handler.decode
				if hasattr(handler, 'display'):
					self.display = handler.display
			except ImportError as e:			# In case there is no handler my that name ...
				print(e)
				pass

			decode(self)
			# We are done ...

		elif response is None:
		# We can't handle 'None', it's a big error
			raise ScannerDecodeError("'None' is invalid as a response")
		else:
		# Must be a Null response. This isn't good but isn't fatal
			self.cmd = ''
			self.status = DECODEERROR
	def __str__(self):
		return self.display(self)

if __name__ == "__main__":	# Do a simple test
	GLG = 'GLG,0463.0000,FM,0,0,Public Safety,EMS MED Channels,Med 1,1,0,NONE,NONE,NONE'
	STS = 'STS,011000,        ����    ,,Fairfield County,,FAPERN VHF      ,, 154.1000 C151.4,,S0:12-*5*7*9-   ,,GRP----5-----   ,,1,0,0,0,0,0,5,GREEN,1'

	for t in (GLG, STS):
		v = Response(t)
		print("{} dict: {}".format(t[:3], v.__dict__))
		print('{} str={}'.format(t[:3], v.__str__()))
