"""A model decoder

Simply copy this file to "CMD.py" where 'CMD' is the response you want to decode.

To customize the variable names ONLY simply supply a 'varlist' as shown below.

If you supply a decode then that will be called to decode the response, otherwise the varlist will
be used to decode the response. For most scanner responses a customized decode is not necessary.
(STS is a notable exception because that response has a variable length.)

A display is usually provided here which will format the response display into something more readable."""

# Import our parent
from . import ScannerDecodeError, Response

# This list is the names of the response values. Usually taken from the Complete Reference manual

varlist = ('CMD', 'T1', 'T2', 'RSV1', 'RSV2')

def display(response):
    """Format a string to use as a generic display for the response."""
    return 'CMD={CMD}, T1={T1}, T2={T2}, RSV={RSV1}, RSV={RSV2}, NOT={NOT}, Time={TIME}'.format_map(response.__dict__)

## See MDL.py and VER.py for other examples.

def decode(response):
    """Decode the response object.

    Useful attributes in the object:
        response.response -- The entire response from the scanner
        response.parts -- A list built from the response split on commas"""

    for i, v in enumerate(response.parts):
        var = varlist[i] if i < len(varlist) else 'VAR'
        setattr(response, var, v)
