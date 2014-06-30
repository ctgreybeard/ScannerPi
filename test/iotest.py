#!/usr/bin/env python3

import sys
import codecs
from threading import Thread
from time import sleep
import inspect
import termios
import copy

dev = "/dev/ttyUSB0"

def decodeerror(decodeerror):
	return ('?' * (decodeerror.end - decodeerror.start), decodeerror.end, )

codecs.register_error('scanner', decodeerror)

def setio(ttyio):
	attrs = termios.tcgetattr(ttyio)
	nattrs = copy.deepcopy(attrs)
	iflag, oflag, cflag, lflag, ispeed, ospeed, cc = list(range(7))
# Shamefully stolen from http://en.wikibooks.org/wiki/Serial_Programming/termios
	# Input flags - Turn off input processing
	# convert break to null byte, no CR to NL translation,
	# no NL to CR translation, don't mark parity errors or breaks
	# no input parity check, don't strip high bit off,
	# no XON/XOFF software flow control
	#
	nattrs[iflag] &= ~(termios.IGNBRK | termios.BRKINT | termios.ICRNL |
		termios.INLCR | termios.PARMRK | termios.INPCK | termios.ISTRIP | termios.IXON)

	# Output flags - Turn off output processing
	# no CR to NL translation, no NL to CR-NL translation,
	# no NL to CR translation, no column 0 CR suppression,
	# no Ctrl-D suppression, no fill characters, no case mapping,
	# no local output processing

	nattrs[oflag] &= ~(termios.OCRNL | termios.ONLCR | termios.ONLRET |
		termios.ONOCR | termios.OFILL | termios.OLCUC | termios.OPOST);

	# No line processing:
	# echo off, echo newline off, canonical mode off, 
	# extended input processing off, signal chars off

	attrs[lflag] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.IEXTEN | termios.ISIG);

	# Turn off character processing
	# clear current char size mask, no parity checking,
	# no output processing, force 8 bit input

	nattrs[cflag] &= ~(termios.CSIZE | termios.PARENB);
	nattrs[cflag] |= termios.CS8;

	# One input byte is enough to return from read()
	# Inter-character timer off

	nattrs[cc][termios.VMIN]  = 1;
	nattrs[cc][termios.VTIME] = 0;

	# Communication speed (simple version, using the predefined
	# constants)

	nattrs[ispeed] = termios.B115200
	nattrs[ospeed] = termios.B115200

	if attrs != nattrs:
		termios.tcsetattr(ttyio, termios.TCSAFLUSH, nattrs)

running = True

def putit():
	try:
		writeio = None
		while running:
			sleep(1)
			#print("Writing...")
			if writeio is None or writeio.closed:
				writeio = open(dev, mode = 'wt', buffering = 1, newline = '\r', encoding = 'ascii')
				print("Write attrs:", termios.tcgetattr(writeio))
				setio(writeio)
				print("Write nattrs:", termios.tcgetattr(writeio))
			writeio.write("GLG\r")
	finally:
		writeio.close()

def getit():
	try:
		readio = None
		while running:
			#print("Reading...")
			if readio is None or readio.closed:
				readio = open(dev, mode = 'rt', buffering = 1, newline = '\r', encoding = sys.argv[1], errors = 'scanner')
				print("Read attrs:", termios.tcgetattr(readio))
				setio(readio)
				print("Read nattrs:", termios.tcgetattr(readio))
			r = readio.readline().rstrip('\r')
			print("Received: \"{}\"".format(r.rstrip('\r')))
			#s = r.split(',')
			#print(','.join(s[4:13:2]))
	finally:
		readio.close()

writer = Thread(target=putit, name='Writer')
reader = Thread(target=getit, name='Reader')

reader.start()
writer.start()
try:
	writer.join()
except KeyboardInterrupt:
	print("Stopping...")
	running = False

reader.join()
