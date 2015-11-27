"""
Scanmon __main__ routine. Runs the Scanmon system.

`Source <src/scanmon.__main__.html>`__
"""

import argparse
from scanmon import Scanmon

_COLORHELP = " text color index (0 to 63)"

def main():
    """Set up parameter parsing and launch Scanmon
    """

    parser = argparse.ArgumentParser(description="Monitor and control the scanner", prog="scanmon")
    parser.add_argument("-s", "--scanner",
                        required=False,
                        action='append',
                        help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
    parser.add_argument("-d", "--debug",
                        required=False,
                        default=False,
                        action='store_true',
                        help="Debugging flag, default False")
    parser.add_argument("-M", "--monitor",
                        required=False,
                        default=False,
                        action='store_true',
                        help="Auto start GLG monitor")
    parser.add_argument("--color-norm",
                        required=False,
                        help="Normal" + _COLORHELP,
                        type=int)
    parser.add_argument("--color-alert",
                        required=False,
                        help="Alert" + _COLORHELP,
                        type=int)
    parser.add_argument("--color-warn",
                        required=False,
                        help="Warning" + _COLORHELP,
                        type=int)
    parser.add_argument("--color-green",
                        required=False,
                        help="Green" + _COLORHELP,
                        type=int)
    parser.add_argument("--database", "--db",
                        required=False,
                        default="scanmon.db",
                        help="File name for the database",
                        type=str)
    parser.add_argument("--timeout",
                        required=False,
                        type=float,
                        help="Idle timeout for receptions")
    args = parser.parse_args()

    scanner = Scanmon(args)
    scanner.run()

    scanner.close()

if __name__ == '__main__':
    main()
