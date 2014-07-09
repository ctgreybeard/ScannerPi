"""Handle the (dummy) TST response"""

# Import our parent
from . import ScannerDecodeError, Response

# This test is less meaningful since we removed the duplicate names handling

varlist = ('CMD', 'T1', 'T2', 'RSV1', 'RSV2')

def display(response):
	return 'CMD={CMD}, T1={T1}, T2={T2}, RSV={RSV1}, RSV={RSV2}, NOT={NOT}, Time={TIME}'.format_map(response)
