"""
Scanmon __main__ routine. Runs the Scanmon system.
"""

import argparse
from scanmon import Scanmon

def main():
# Options definition
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
    COLORHELP = " text color index (0 to 63)"
    parser.add_argument("--color-norm",
                        required=False,
                        help="Normal" + COLORHELP,
                        type=int)
    parser.add_argument("--color-alert",
                        required=False,
                        help="Alert" + COLORHELP,
                        type=int)
    parser.add_argument("--color-warn",
                        required=False,
                        help="Warning" + COLORHELP,
                        type=int)
    parser.add_argument("--color-green",
                        required=False,
                        help="Green" + COLORHELP,
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

    SCANNER = Scanmon(args)
    SCANNER.run()

    SCANNER.close()

if __name__ == '__main__':
    main()
