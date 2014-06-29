#!/usr/bin/env python3

import subprocess
from threading import Thread
from time import sleep

dev = "/dev/ttyUSB0"

# Setup the tty
rc = subprocess.call("stty --file {} 115200 -echo -ocrnl -onlcr raw time 5".format(dev).split())
if rc != 0:
	raise IOError("Unable to initialize \"{}\"".format(dev))

def putit():
	writeio = None
	while True:
		sleep(0.2)
		#print("Writing...")
		if writeio is None or writeio.closed:
			writeio = open(dev, mode = 'wt', buffering = 1, newline = '\r', encoding = 'ascii')
		writeio.write("STS\r")
	writeio.close()

def getit():
	readio = None
	while True:
		#print("Reading...")
		if readio is None or readio.closed:
			readio = open(dev, mode = 'rt', buffering = 1, newline = '\r', encoding = 'ascii', errors = 'replace')
		r = readio.readline().rstrip('\r')
		#print("Received: \"{}\"".format(r.rstrip('\r')))
		s = r.split(',')
		print(','.join(s[4:13:2]))
	readio.close()

writer = Thread(target=putit, name='Writer')
reader = Thread(target=getit, name='Reader')

reader.start()
writer.start()
