"""A model decoder

`Source <src/scanmon.scanner.formatter.Model.html>`__

Simply copy this file to "CMD.py" where 'CMD' is the response you want to decode.

To customize the variable names ONLY simply supply a 'VARLIST' as shown below.

If you supply a decode then that will be called to decode the response,
otherwise the VARLIST will be used to decode the response.
For most scanner responses a customized decode is not necessary.
(STS is a notable exception because that response has a variable length.)

A display is usually provided here which will format the response
display into something more readable.
"""

# from scanmon.scanner.formatter import ScannerDecodeError, Response

# This list is the names of the response values. Usually taken from the Complete Reference manual

VARLIST = ('CMD', 'T1', 'T2', 'RSV1', 'RSV2')

def display(response):
    """Format a string to use as a generic display for the response.

    Args:
        response (Response): Scanner response object
    """
    return ('CMD={CMD}, '
            'T1={T1}, '
            'T2={T2}, '
            'RSV={RSV1}, '
            'RSV={RSV2}, '
            'NOT={NOT}, '
            'Time={TIME}').format_map(response.__dict__)

## See MDL.py and VER.py for other examples.

def decode(response):
    """Decode the response object.

    Args:
        response (Response): Scanner response object

    Useful attributes in the object:
        response.response: The entire response from the scanner
        response.parts: A list built from the response split on commas
    """

    for i, value in enumerate(response.parts):
        var = VARLIST[i] if i < len(VARLIST) else 'VAR'
        setattr(response, var, value)
