#!/usr/bin/env python3

import sys
import codecs
import subprocess
from threading import Thread
from time import sleep
import inspect

dev = "/dev/ttyUSB0"

# Setup the tty
rc = subprocess.call("stty --file {} 115200 -echo -ocrnl -onlcr raw time 5".format(dev).split())
if rc != 0:
	raise IOError("Unable to initialize \"{}\"".format(dev))

def decodeerror(decodeerror):
	return ('?' * (decodeerror.end - decodeerror.start), decodeerror.end, )

codecs.register_error('scanner', decodeerror)

running = True

def putit():
	try:
		writeio = None
		while running:
			sleep(1)
			#print("Writing...")
			if writeio is None or writeio.closed:
				writeio = open(dev, mode = 'wt', buffering = 1, newline = '\r', encoding = 'ascii')
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
