"""Handle the STS response

`Source <src/scanmon.scanner.formatter.STS.html>`__
"""

_VARLIST = ('CMD',
            'DSP_FORM',
            'L1_CHAR', 'L1_MODE',
            'L2_CHAR', 'L2_MODE',
            'L3_CHAR', 'L3_MODE',
            'L4_CHAR', 'L4_MODE',
            'L5_CHAR', 'L5_MODE',
            'L6_CHAR', 'L6_MODE',
            'L7_CHAR', 'L7_MODE',
            'L8_CHAR', 'L8_MODE',
            'SQL', 'MUT', 'RSV', 'BAT', 'WAT', 'SIG_LVL', 'BK_COLOR', 'BK_DIMMER')

# Note: L1 through L8 exist to the extent of len(DSP_FORM)
_DSP_FORM_INDEX = _VARLIST.index('DSP_FORM')
_SQL_INDX = _VARLIST.index('SQL')

def decode(response):
    """Decode the STS response

    Note that the DSP_FORM has one character for each line of the display. The L\\ *n* CHAR
    and MODE lines correspond. Unused CHAR and MODE lines do not exist in the response and
    must be removed from VARLIST in order to properly associate the data.
    """

    varlist = list(_VARLIST[:])   # Make a mutable copy
    del varlist[1 +
                _DSP_FORM_INDEX +
                len(response.parts[_DSP_FORM_INDEX]) * 2:
                _SQL_INDX]  # Remove the unused Lines
    # Note that we can't use response.DSP_FORM because we haven't created it yet! We do that next.
    for i, val in enumerate(response.parts):
        var = varlist[i] if i < len(varlist) else 'VAR'
        setattr(response, var, val)

# This seems overly complicated but it works.
def display(response):
    """Display the response accounting for the variable length.
    """

    seed = []
    try:
        for i in range(1, len(response.DSP_FORM) + 1):
            seed.append("L{0}:{{L{0}_CHAR}}".format(i))
        rval = ', '.join(seed).format_map(response.__dict__)
    except KeyError as keyerror:
        rval = '? ' + repr(keyerror)

    return rval
