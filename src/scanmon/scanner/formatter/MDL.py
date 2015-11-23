"""MDL command response"""

#from scanmon.scanner.formatter import ScannerDecodeError, Response

# This list is the names of the response values. Usually taken from the Complete Reference manual

VARLIST = ('CMD', 'MDL')

def display(response):
    """Format a string to use as a generic display for the response."""
    return 'Scanner model is {}'.format(response.MDL)
