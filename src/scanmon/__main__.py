"""
Scanmon __main__ routine. Runs the Scanmon system.

`Source <src/scanmon.__main__.html>`__
"""

import argparse
from scanmon import Scanmon

_COLORHELP = "{} text color, default={}"

def main():
    """Set up parameter parsing and launch Scanmon
    """

    argmap = {}
    parser = argparse.ArgumentParser(description="Monitor and control the scanner", prog="scanmon")
    _arg = 'config'
    parser.add_argument("--" + _arg, "-C",
                        dest=_arg,
                        required=False,
                        default="config.ini",
                        help="System configuration file")
    # No mapping for config

    _arg = 'logfile'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Log file name")
    argmap[_arg] = ('scanmon', 'logfile')

    _arg = 'scanner'
    parser.add_argument("--" + _arg, "-s",
                        dest=_arg,
                        required=False,
                        action='append',
                        default=argparse.SUPPRESS,
                        help="The USB serial device connected to the scanner."
                        " Usually /dev/ttyUSB0. May be specified multiple times."
                        "The first valid device will be used.")
    argmap[_arg] = ('scanner', 'device')

    _arg = 'debug'
    parser.add_argument("--" + _arg, "-d",
                        dest=_arg,
                        required=False,
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Debugging flag, default False")
    argmap[_arg] = ('scanmon', 'debug')

    _arg = 'monitor'
    parser.add_argument("--" + _arg, "-M",
                        dest=_arg,
                        required=False,
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Auto start GLG monitor")
    argmap[_arg] = ('scanmon', 'logfile')

    _arg = 'color-norm'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help=_COLORHELP.format("Normal", 'light gray'))
    argmap[_arg] = ('window', 'normal')

    _arg = 'color-alert'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help=_COLORHELP.format("Alert", 'light red'))
    argmap[_arg] = ('window', 'alert')

    _arg = 'color-warn'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help=_COLORHELP.format("Warning", 'light magenta'))
    argmap[_arg] = ('window', 'warning')

    _arg = 'color-green'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help=_COLORHELP.format("Green", 'dark green' ))
    argmap[_arg] = ('window', 'green')

    _arg = 'focus-hilight'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="How display lines with the focus are highlighted, default=STANDOUT")
    argmap[_arg] = ('window', 'focus')

    _arg = 'database'
    parser.add_argument("--" + _arg, "--db",
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="File name for the database")
    argmap[_arg] = ('monitor', 'database')

    _arg = 'dblevel'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Recording level for the database")
    argmap[_arg] = ('monitor', 'dblevel')

    _arg = 'timeout'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        type=float,
                        help="Idle timeout for receptions")
    argmap[_arg] = ('monitor', 'timeout')

    _arg = 'titleupdate'
    parser.add_argument("--" + _arg, "-T",
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        action='store_true',
                        help='Disables icecast title updates')
    argmap[_arg] = ('monitor', 'titleupdate')

    _arg = 'titlestream'
    parser.add_argument("--" + _arg, "-S",
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The stream name in icecast for the scanner")
    argmap[_arg] = ('monitor', 'titlestream')

    _arg = 'icecastid'
    parser.add_argument("--" + _arg, "--id",
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The admin ID for icecast to update the titles")
    argmap[_arg] = ('monitor', 'icecastid')

    _arg = 'icecastpwd'
    parser.add_argument("--" + _arg, "--pw",
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The admin ID for icecast to update the titles")
    argmap[_arg] = ('monitor', 'icecastpwd')

    _arg = 'icecasthost'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The system name for icecast")
    argmap[_arg] = ('monitor', 'icecasthost')

    _arg = 'icecastport'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The system port for icecast")
    argmap[_arg] = ('monitor', 'icecastport')

    _arg = 'automute'
    parser.add_argument("--" + _arg,
                        dest=_arg,
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Time (UTC) to automatically mute the scanner")
    argmap[_arg] = ('monitor', 'automute')

    args = parser.parse_args()

    scanner = Scanmon(args, argmap)
    scanner.run()

    scanner.close()

if __name__ == '__main__':
    main()
