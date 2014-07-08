"""Handle the STS response"""

# Import our parent
from . import ScannerDecodeError, Response

_varlist = list(('CMD',
	'DSP_FORM',
	'L1_CHAR','L1_MODE',
	'L2_CHAR','L2_MODE',
	'L3_CHAR','L3_MODE',
	'L4_CHAR','L4_MODE',
	'L5_CHAR','L5_MODE',
	'L6_CHAR','L6_MODE',
	'L7_CHAR','L7_MODE',
	'L8_CHAR','L8_MODE',
	'SQL','MUT','RSV','BAT','WAT','SIG_LVL','BK_COLOR','BK_DIMMER'))

# Note: L1 through L8 exist to the extent of len(DSP_FORM)

def decode(response):
	del _varlist[2 + len(response.parts[1]) * 2: 18]	# Remove the unused Lines
	for i, v in enumerate(response.parts):
		var = _varlist[i] if i < len(_varlist) else 'VAR'
		setattr(response, var, v)

# This seems overly complicated but it works.
def display(response):
	seed = []
	try:
		for i in range(1, len(response.DSP_FORM) + 1):
			seed.append("L{0}:{{L{0}_CHAR}}".format(i))
		rval = ', '.join(seed).format_map(response)
	except Exception as e:
		rval = '?'

	return rval
