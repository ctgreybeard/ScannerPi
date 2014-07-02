## SERIAL branch

###Changelog

####1 Jul 2014

* Installed pyserial v2.7 from https://pypi.python.org/pypi/pyserial

* Had to refactor it for python3 (the setup option didn't work right)

> `2to3 -n -w --no-diffs **/*.py`

> `python3 -m serial.tools.list_ports` now works
