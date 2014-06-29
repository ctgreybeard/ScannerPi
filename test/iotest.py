#!/usr/bin/env python3

import subprocess
from threading import Thread, RLock
from time import sleep

dev = "/dev/ttyUSB0"

# Setup the tty
rc = subprocess.call("stty --file {} 115200 -echo -ocrnl -onlcr raw time 5".format(dev).split())
if rc != 0:
	raise IOError("Unable to initialize \"{}\"".format(dev))

def putit():
	while True:
		sleep(5)
		print("Writing...")
		writeio = open(dev, mode = 'wt', buffering = 1, newline = '\r', encoding = 'ascii')
		writeio.write("STS\r")
		writeio.close()

def getit():
	while True:
		sleep(0.5)
		print("Reading...")
		readio = open(dev, mode = 'rt', buffering = 1, newline = '\r', encoding = 'ascii', errors = 'replace')
		r = readio.readline()
		print("Received: \"{}\"".format(r.rstrip('\r')))
		readio.close()

writer = Thread(target=putit, name='Writer')
reader = Thread(target=getit, name='Reader')

reader.start()
writer.start()
