"""
Scanmon __main__ routine. Runs the Scanmon system.
"""

import argparse

if __name__ == '__main__':
# Options definition
    parser = argparse.ArgumentParser(description = "Monitor and control the scanner", prog = "scanmon")
    parser.add_argument("-s", "--scanner",
        required = False,
        action = 'append',
        help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
    parser.add_argument("-d", "--debug",
        required = False,
        default = False,
        action = 'store_true',
        help="Debugging flag, default False")
    colorhelp = " text color index (0 to 63)"
    parser.add_argument("--color-norm",
        required = False,
        help = "Normal" + colorhelp,
        type = int)
    parser.add_argument("--color-alert",
        required = False,
        help = "Alert" + colorhelp,
        type = int)
    parser.add_argument("--color-warn",
        required = False,
        help = "Warning" + colorhelp,
        type = int)
    parser.add_argument("--color-green",
        required = False,
        help = "Green" + colorhelp,
        type = int)
    parser.add_argument("--database", "--db",
        required = False,
        default = "scanmon.db",
        help = "File name for the database",
        type = str)
    parser.add_argument("--card",
        required = False,
        help = "The card used by the 'vol' command.This is sent verbatim the to 'amixer' command as '-c[card]'")
    parser.add_argument("--volcontrol",
        required = False,
        type = str,
        default = "HPOUT2 Digital",
        help = "The simple mixer control for setting volume.")
    parser.add_argument("--basevolume",
        required = False,
        default = Scanmon._DEFBASEVOL,
        type = str,
        help = "The setting for the 'norm' volume setting. Other settings go up or down from this. May be set in units or dB.")
    parser.add_argument("--volume",
        required = False,
        action = 'append',
        type = str,
        help = "A volume point given as 'name:set' (ex. vlow:90 -or- norm:-15dB). These are merged with the standard settings (verylow/vlow, low, normal/norm, high/hi, veryhigh/vhi)")
    parser.add_argument("--vstep",
        required = False,
        default = None,
        help = "Step difference between settings (i.e. 'norm' to 'high', etc.) Defaults to 3dB or 6 units.")
    parser.add_argument("--dbfactor",
        required = False,
        default = 2,
        type = int,
        help = "Multiplication factor to change dB to UNITs")
    parser.add_argument("--timeout",
        required = False,
        type = float,
        help = "Idle timeout for receptions")
    args = parser.parse_args()

    SCANNER = Scanmon(args)
    SCANNER.run(args)

    SCANNER.close()


