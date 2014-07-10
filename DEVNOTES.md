## Development notes to remember

### Mac stuff

* Serial-USB driver at http://nozap.me/driver/osxpl2303/index.html

* Error in termios:

```
Traceback (most recent call last):
  File "scanmon.py", line 226, in <module>
    SCANNER = Scanmon(args.scanner)
  File "scanmon.py", line 88, in __init__
    self.scanner = Scanner(scandevice)
  File "/Volumes/WaggExt4/Projects/ScannerPi/src/scanner/__init__.py", line 144, in __init__
    _setio(self._serscanner)
  File "/Volumes/WaggExt4/Projects/ScannerPi/src/scanner/__init__.py", line 59, in _setio
    termios.ONOCR | termios.OFILL | termios.OLCUC | termios.OPOST);
AttributeError: 'module' object has no attribute 'OLCUC'
```

* Initial tests on the Mac show that reading from the scanner is unreliable at best.
