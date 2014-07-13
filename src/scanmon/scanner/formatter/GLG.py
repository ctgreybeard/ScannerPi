"""Handle the GLG response"""

# Import our parent
from . import ScannerDecodeError, Response

varlist = ('CMD','FRQ_TGID','MOD','ATT','CTCSS_DCS','NAME1','NAME2','NAME3','SQL','MUT','SYS_TAG','CHAN_TAG','P25NAC')

def display(response):
	return 'Sys={NAME1}, Group={NAME2}, Chan={NAME3}, Freq={FRQ_TGID}'.format_map(response)
