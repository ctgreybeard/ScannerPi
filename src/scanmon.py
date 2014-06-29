#!/usr/bin/env python3

import sys
import threading
import argparse
import io
import subprocess
import curses
import threading
import queue
from collections import deque

# Our own definitions
from scanner import Scanner
from monwin import Monwin

class Scanmon:

	def __init__(self, scandevice):
		self.scanner = Scanner(scandevice)
# Build the queues, use an arbitrary 10 as the maxsize
		self.q_scanout = queue.Queue(maxsize=10)	# Output to the scanner
		self.q_scanin = queue.Queue(maxsize=10)	# Responses from the scanner
		self.q_command = queue.Queue(maxsize=10)	# Commands entered at the console
		self.q_response = {}		# request to receive responses
		self.q_response['GLG'] = self.do_glg	# We know who wants to see GLG responses

	def putline(self, win, line):
		pass

	def runmon(self, glgwin, respwin):
		for line in SCANNER:
			resp = line.split(',')
			if resp[0] == 'GLG':
				postglg(glgwin, resp)
			else:
				postresp(respwin, line, resp)

	def main(self, stdscr):

		self.monwin = Monwin(stdscr)

		self.monwin.putline("glg", "A test line in GLG")
		self.monwin.putline("resp", "A test line in RESP")
		self.monwin.message("A test MESSAGE")
		self.monwin.putline("resp", "A second test line in RESP")

		cmd = self.monwin.getline()

		print("cmd=\"{}\"".format(cmd), file=sys.stderr)

	def close(self):
		self.scanner.close()
		self.monwin.close()

	def do_glg(self, response):
		pass

if __name__ == '__main__':
# Options definition
	parser = argparse.ArgumentParser(description = "Monitor and control the scanner")
	parser.add_argument("-s", "--scanner", 
		required = False, 
		action = 'append',
		help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
	args = parser.parse_args()

	SCANNER = Scanmon(args.scanner)

	curses.wrapper(SCANNER.main)
	SCANNER.close()


