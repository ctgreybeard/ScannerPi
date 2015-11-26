"""Format decoders and encoder for Uniden BCDX96XT scanner

`Source <src/scanmon.scanner.formatter.html>`__
"""

import sys
import logging
from datetime import datetime as DateTime
from importlib import import_module

class ScannerDecodeError(TypeError):
    """A generic error for decoders to use.
    """

def gendecode(response):
    """Generalized decoder. Disassemble using the supplied or default VARLIST.

    Note:
        Duplicate names in VARLIST are adjusted by appending a number
        to make them unique.
    """

    for i, val in enumerate(response.parts):
        var = response.VARLIST[i] if i < len(response.VARLIST) else 'VAR'
        if hasattr(response, var):
            incr = 1
            while hasattr(response, var + str(incr)):
                incr += 1
            var = var + str(incr)

        setattr(response, var, val)

def gendisplay(response):
    """Generalized display. Just assemble the parts.
    """

    try:
        resp = ','.join(response.parts[1:])
    except IndexError:
        resp = '?'

    return resp

class Response(object):
    """A generic response class. Handles deconstruction of arbitrary scanner responses.

    Attributes:
        CMD: The first word of the response or Null

        status: 'OK', 'NG', 'ERR', or 'DECODEERROR'
            OK: Response was 'OK' or response was decoded correctly
            NG: Response was 'NG' (Command invalid at this time)
            ERR: Error response from scanner (Command format error / Value error,
            Framing error, Overrun error)

        response: The original response string (trailing '\\\\r' removed if any existed)

        parts: ordered list of the parsed response

        *values*: decoded terms. Names are in UPPER CASE as given in the BCD396XT Complete Reference
            This is implemented such that ANY upper case name is available to be retrieved.

            Names not set by the response return None.

            Duplicate names (typically "RSV") are numbered from 1
            after the first: RSV, RSV1, RSV2, etc.

    Raises:
       ScannerDecodeError: Scanner returned illegal response

    Process:
        * Separate the pieces of the response using ',' separator
        * If a first piece exists look for a decoder for it
        * Load and execute the appropriate decoder if found
        * Otherwise decode by separating the parts using ','
        * If the second piece is 'Response.ERR' or 'Response.NG' set the error flags appropriately
        * If the response is Null or None set the error flags
    """

# Class variables
    OK = 'OK'
    NG = 'NG'
    ERR = 'ERR'
    FER = 'FER'
    ORER = 'ORER'
    DECODEERROR = 'DECODEERROR'
    RESP = 'RESP'

    def __init__(self, response):
        """Initialize the instance, load a specific format if available.

        Arguments:
            response: The returned string from the scanner

        """

        # Ensure that we have values for the necessary attributes
        self.CMD = '?'
        self.response = ''
        self.parts = tuple()
        self.TIME = DateTime.now()
        self.display = gendisplay
        self.VARLIST = ('CMD',)     # Default variable list

        if response:
        # Something is there, look further
            self.response = response.rstrip('\r')
            self.parts = self.response.split(',')

            if len(self.parts) < 2:     # Not exactly sure what this is but it's not good
                raise ScannerDecodeError("Invalid response ({}) from scanner".format(self.response))

            self.CMD = self.parts[0].upper()

            if (len(self.parts) == 2 and    # Probably just an simple response
                    self.parts[1] in (Response.OK, Response.NG, Response.FER, Response.ORER)):
                self.RESP = self.parts[1]
                self.status = self.parts[1]

            else:
                # We got here with something. Let's deconstruct it
                self.status = Response.RESP
                decode = gendecode      # Set a generic decode as fallback

                try:
                    handler = import_module('.' + self.CMD, package=__name__)
                    if hasattr(handler, 'decode'):
                        decode = handler.decode         # Use a specific decoder
                    elif hasattr(handler, 'VARLIST'):
                        self.VARLIST = handler.VARLIST

                    if hasattr(handler, 'display'):
                        self.display = handler.display
                except ImportError:            # In case there is no handler my that name ...
                    # Note: we do not have an instance logger because we are short lived
                    logging.warning('Missing decoder for %s', self.CMD)

                decode(self)
                # We are done ...

        elif response is None:
        # We can't handle 'None', it's a big error
            raise ScannerDecodeError("'None' is invalid as a response")
        else:
        # Must be a Null response. This isn't good but isn't fatal
            self.CMD = ''
            self.status = Response.DECODEERROR

    def __str__(self):
        """Return whatever was set during initialization."""
        return self.display(self)

    def __getattr__(self, name):
        """Called ONLY if the requested attribute does NOT exist.
        For response variables (upper case) we return None.
        """

        if name == name.upper():    # All uppercase?
            return None

        super().__getattr__(name)
