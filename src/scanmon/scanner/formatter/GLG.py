"""Handle the GLG response"""

from scanmon.scanner.formatter import ScannerDecodeError, Response

varlist = ('CMD','FRQ_TGID','MOD','ATT','CTCSS_DCS','NAME1','NAME2','NAME3','SQL','MUT','SYS_TAG','CHAN_TAG','P25NAC')

def display(response):
    try:
        return 'Sys={NAME1}, Group={NAME2}, Chan={NAME3}, Freq={FRQ_TGID}, SQL={SQL}, MUT={MUT}'.format_map(response.__dict__)
    except KeyError:
        return '[' + response.response + ']'
