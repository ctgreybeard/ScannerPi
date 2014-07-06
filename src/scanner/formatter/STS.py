"""Handle the GLG response"""

# Import our parent
from . import ScannerDecodeError, OK, NG, ERR, FER, ORER

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
		var = _varlist[i] if i < len(_varlist) else 'var{}'.format(i)
		response.val[var] = v

def display(response):
	seed = []
	try:
		for i in range(1, len(response.val['DSP_FORM'])+1):
			seed.append("{{L{}_CHAR}}".format(i))
		rval = ','.join(seed).format(**response.val)
	except:
		rval = '?'

	return rval
