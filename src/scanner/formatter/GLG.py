"""Handle the GLG response"""

_minvar = 11
_maxvar = 11

# Import our parent
from . import ScannerDecodeError, OK, NG, ERR, FER, ORER

varlist = ('GLG','FRQ/TGID','MOD','ATT','CTCSS/DCS','NAME1','NAME2','NAME3','SQL','MUT','SYS_TAG','CHAN_TAG','P25NAC')
def decode(response):
	for i, v in enumerate(response.parts):
		response.val[varlist[i]] = v

def display(response):
	return 'Sys={NAME1}, Group={NAME2}, Chan={NAME3}, Freq={FRQ/TGID}'.format(**response.val)
