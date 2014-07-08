"""Handle the (dummy) TST response"""

# Import our parent
from . import ScannerDecodeError, Response

_rsv = 'RSV'
varlist = ('CMD', 'T1', 'T2', _rsv, _rsv)

def display(response):
	return 'CMD={CMD}, T1={T1}, T2={T2}, RSV={RSV}, RSV={RSV1}, NOT={NOT}, Time={TIME}'.format_map(response)
