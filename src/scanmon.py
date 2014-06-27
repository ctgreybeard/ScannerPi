#!/usr/bin/python3

import sys
import curses
import curses.ascii as ascii
import curses.panel as panel
import curses.textpad as textpad
import threading
import argparse
import io
import subprocess

# Our own definitions
from scanner import Scanner

class Scanmon:

	NORM = 1
	ALERT = NORM + 1    # Color pair #2
	WARN = ALERT + 1    # color pair #3
	GREEN = WARN + 1    # Color pair #4

	def __init__(self, scandevice):
		self.scanner = Scanner(scandevice)

	def putline(self, win, line):
		pass

	def runmon(self, glgwin, respwin):
		for line in SCANNER:
			resp = line.split(',')
			if resp[0] == 'GLG':
				postglg(glgwin, resp)
			else:
				postresp(respwin, line, resp)

	def startmon(self, glgwin, respwin):
		pass

	def main(self, stdscr):

# global variables that we set

		global MAINLINES, MAINCOLS, MSGLINES, RESPLINES, CMDLINES, GLGLINES, WINCOLS, CMDORIG_X, CMDORIG_Y
		global GLGBOT, RESPBOT
		# Clear screen
		stdscr.clear()
		main_panel = panel.new_panel(stdscr)

		MAINLINES = curses.LINES
		MAINCOLS = curses.COLS
# Define window sizes lines and columns do NOT include border characters
		MSGLINES = 1
		RESPLINES = 8
		CMDLINES = 1
# GLG gets the rest minus the borders
		GLGLINES = MAINLINES - MSGLINES - RESPLINES - CMDLINES - 5
# All subwindows have the same width
		WINCOLS = MAINCOLS - 2
# Some handy calculations
		CMDORIG_Y = MSGLINES + GLGLINES + RESPLINES + 4
		CMDORIG_X = 1
		GLGBOT = MSGLINES + GLGLINES + 1
		RESPBOT = MSGLINES + GLGLINES + RESPLINES + 2

		print("MAIN={},MSG={},GLG={},RESP={},CMD={},Total={}".format(MAINLINES, MSGLINES, GLGLINES, RESPLINES, CMDLINES, 
			MSGLINES + 1 + GLGLINES + 2 + RESPLINES + CMDLINES + 2), file=sys.stderr)

# Set the color pairs
		curses.init_pair(NORM, curses.COLOR_CYAN, curses.COLOR_BLACK)
		curses.init_pair(ALERT, curses.COLOR_WHITE, curses.COLOR_RED)
		curses.init_pair(WARN, curses.COLOR_YELLOW, curses.COLOR_BLACK)
		curses.init_pair(GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)

		stdscr.attrset(curses.color_pair(NORM))
		stdscr.border()

		msgwin = stdscr.subwin(MSGLINES, WINCOLS, 1, 1)
		glgwin = stdscr.subwin(GLGLINES, WINCOLS, MSGLINES + 2, 1)
		glgwin.setscrreg(0, GLGLINES - 1)
		respwin = stdscr.subwin(RESPLINES, WINCOLS, MSGLINES + GLGLINES + 3, 1)
		respwin.setscrreg(0, RESPLINES - 1)
		cmdwin = stdscr.subwin(CMDLINES, WINCOLS, CMDORIG_Y, CMDORIG_X)
		stdscr.hline(MSGLINES + 1, 1, curses.ACS_HLINE, WINCOLS)
		stdscr.hline(MSGLINES + GLGLINES + 2, 1, curses.ACS_HLINE, WINCOLS)
		stdscr.hline(MSGLINES + GLGLINES + RESPLINES + 3, 1, curses.ACS_HLINE, WINCOLS)
		stdscr.move(CMDORIG_Y, CMDORIG_X)
		stdscr.leaveok(False)

		cmdbox = textpad.Textbox(cmdwin)
		cmdbox.stripspaces = True

		stdscr.refresh()
		startmon(glgwin, respwin)

		cmd = cmdbox.edit().strip()

		print("cmd=\"{}\"".format(cmd), file=sys.stderr)

if __name__ == '__main__':
# Options definition
	parser = argparse.ArgumentParser(description = "Monitor and control the scanner")
	parser.add_argument("-s", "--scanner", 
		required = False, 
		action = 'append',
		help="The USB serial device connected to the scanner. Usually /dev/ttyUSB0. May be specified multiple times. The first valid device will be used.")
	args = parser.parse_args()
	print("args=\"{}\"".format(args))
	sys.exit()
	SCANNER = Scanmon(args.scanner)

	curses.wrapper(SCANNER.main)
	SCANNER.close()


