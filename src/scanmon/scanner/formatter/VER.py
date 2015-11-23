"""VER command response"""

# Import our parent
#from . import ScannerDecodeError, Response

# This list is the names of the response values. Usually taken from the Complete Reference manual

VARLIST = ('CMD', 'VER')

def display(response):
    """Format a string to use as a generic display for the response."""
    return 'Scanner software {}'.format(response.VER)
