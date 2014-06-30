"""A curses window for scanmon

Classes:
Monwin -- the main class using curses 
Subwin -- an internal class for Monwin for the sub-windows
"""

import sys
import curses
import curses.ascii as ascii
import curses.panel as panel
import curses.textpad as textpad
import logging
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL

NORM = 1
ALERT = NORM + 1    # Color pair #2
WARN = ALERT + 1    # color pair #3
GREEN = WARN + 1    # Color pair #4
COLORS = {"NORM":NORM, "ALERT":ALERT, "WARN":WARN, "GREEN":GREEN}

class Monwin:

	"""Build and control the curses screen for Scanmon.

	Internal classes:
	Subwin -- The individual sub-windows (msg, glg, resp, cmd, and alert)

	Functions:
	__init__ -- The usual.
	putline -- Scroll the sub-window and write a new line at the bottom.
	getline -- Read input from the command window.
	alert -- Display a message in the message window. Wait for acknowledgement.
	message -- Display a message in the message window.
	"""
	class Subwin:

		"""Build a subwindow or overlay window.

		Functions:
		__init__ -- Initialization
		putline -- Scroll the sub-window and write a new line at the bottom
		getline -- Read input from the command window
		hint -- Write text as a hint line within the top border allowance
		"""

		def __init__(self, master, name, 
			height, width, 
			origin_y, origin_x, 
			overlay = False, 
			textinput = False,
			borderleft = 1, borderright = 1, bordertop = 1, borderbottom = 1,
			border = False,
			hlinetop = False, hlinebottom = False):

			"""Initialize the class.

			Positional arguments:
			master -- The master window (usually stdscr)
			name -- The name of the subwindow
			origin_y, origin_x -- relative position within the master window
			height, width -- height and width including border allowance

			Keyword arguments:
			overlay -- Define subwindow as an overlay rather than subwindow (False)
			textinput -- This is a text input window (False)
			border{left,right,top,bottom} -- Setback allowance for borders (1)
			border -- Draw a standard border within the allowance (False)
			hline{top,bottom} -- Draw a horizontal line top or bottom with this character (False)
			"""

# Set up logging
			self.logger = logging.getLogger('scanmon.monwin.subwin')
			self.logger.info('subwin %s: Initializing', name)
# Record the initial parameters
			self.master = master
			self.name = name
			self.height = height
			self.width = width 
			self.origin_y = origin_y
			self.origin_x = origin_x
			self.overlay = overlay
			self.textinput = textinput
			self.borderleft = borderleft
			self.borderright = borderright
			self.bordertop = bordertop
			self.borderbottom = borderbottom
			self.border = border
			self.hlinetop = hlinetop
			self.hlinebottom = hlinebottom
			self.logger.info("subwin %s: Initialized master=%s height=%s, width=%s origin_y=%s,origin_x=%s overlay=%s,textinput=%s borders=%s,%s,%s,%s border=%s hlinetop=%s,hlinebottom=%s", name, master, height, width, origin_y, origin_x, overlay, textinput, borderleft, borderright, bordertop, borderbottom, border, hlinetop, hlinebottom)

			if not overlay:
				if border:
# Create a dummy "master" window to hold the border
					master = self.master.subwin(height, width, origin_y, origin_x)
					master.border()
					self.logger.info("subwin %s: non-overlay+border master at %s", self.name, (height, width, origin_y, origin_x))
					origin_x = 0
					origin_y = 0
					borderleft = 1
					borderright = 1
					bordertop = 1
					borderbottom = 1
					hlinetop = False
					hlinebottom = False

				self.winheight = height - bordertop - borderbottom
				self.winwidth = width - borderleft - borderright
				self.winorigin_y = origin_y + bordertop
				self.winorigin_x = origin_x + borderleft
				self.window = master.subwin(height - bordertop - borderbottom, 
					width - borderleft - borderright,
					origin_y + bordertop,
					origin_x + borderleft)
				self.logger.info("subwin %s: subwindow at %s", self.name, (height - bordertop - borderbottom, width - borderleft - borderright, origin_y + bordertop, origin_x + borderleft))

				self.bottomline = height - bordertop - borderbottom - 1
				assert self.bottomline >= 0, "%s: bottomline(%s) less than 0".format(self.name, self.bottomline)
				self.firstcol = 0
				self.msgwidth = width - borderleft - borderright
				if self.bottomline > 0:
					self.window.scrollok(True)
					try:
						self.window.setscrreg(0, self.bottomline)
					except:
						self.logger.error("subwin %s: setscrreg(0, %s) failed.", self.name, self.bottomline)

				if hlinetop and bordertop:
					master.hline(origin_y, borderleft, hlinetop, self.msgwidth)
					self.logger.info("subwin %s: hlinetop at %s,%s", self.name, origin_y, borderleft)

				if hlinebottom and borderbottom:
					bline = origin_y + height - 1
					master.hline(bline, borderleft, hlinebottom, self.msgwidth)
					self.logger.info("subwin %s: hlinebottom at %s,%s", self.name, origin_y, borderleft)

			else:
				raise NotImplementedError("Overlays still need to be done")

			if textinput:
				self.textbox = curses.textpad.Textbox(self.window)
				self.logger.info("subwin %s: textbox set", self.name)
			else:
				self.textbox = None

		def putline(self, message, color):
			"""Scroll the window and write the message on the bottom line.

			Positional parameters:
			message -- The message (a string)
			color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
			"""
			self.logger.info("subwin %s: writing\"%s\"", self.name, message)
			target = self.window
			target.scroll()
			try:
				target.addnstr(self.bottomline, self.firstcol, message, self.winwidth, curses.color_pair(COLORS[color]))
			except:
				self.logger.error("subwin %s: addnstr(%s, %s, %s, %s, %s) failed", self.name, self.bottomline, self.firstcol, message, self.winwidth, curses.color_pair(COLORS[color]))
				sys.exit(1)
			target.refresh()

	def __init__(self, stdscr):

		"""Initialize the master screen (stdscr)
		
		Positional parameters:
		stdscr -- The master curses screen

		Initializes the master screen with a border and builds the subwindows: msg, glg, resp, cmd, and alert
		"""

# Set up logging
		self.logger = logging.getLogger('scanmon.monwin')
		self.logger.info('monwin: Initializing')
		self._mainlines, self._maincols = stdscr.getmaxyx()
		self.logger.info("monwin: Screen is %s lines, %s cols", self._mainlines, self._maincols)
# Define window sizes lines and columns include border characters
		MSGLINES = 4
		RESPLINES = 10
		CMDLINES = 2
# GLG gets the rest minus the borders
		GLGLINES = self._mainlines - MSGLINES - RESPLINES - CMDLINES
# All subwindows (except alert) have the same width
		WINCOLS = self._maincols

		# Clear screen
		self._stdscr = stdscr
		stdscr.clear()
		stdscr.leaveok(False)

		self.main_panel = panel.new_panel(stdscr)
# Set the color pairs
		curses.init_pair(NORM, curses.COLOR_CYAN, curses.COLOR_BLACK)
		curses.init_pair(ALERT, curses.COLOR_WHITE, curses.COLOR_RED)
		curses.init_pair(WARN, curses.COLOR_YELLOW, curses.COLOR_BLACK)
		curses.init_pair(GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)

		stdscr.attrset(curses.color_pair(NORM))
		stdscr.border()

		self.msgwin = Monwin.Subwin(stdscr, "msg", MSGLINES, WINCOLS, 0, 0, hlinebottom = curses.ACS_HLINE)
		self.glgwin = Monwin.Subwin(stdscr, "glg", GLGLINES, WINCOLS, MSGLINES, 0, hlinebottom = curses.ACS_HLINE, bordertop = 0)
		self.respwin = Monwin.Subwin(stdscr, "resp", RESPLINES, WINCOLS, MSGLINES + GLGLINES, 0, hlinebottom = curses.ACS_HLINE, bordertop = 0)
		self.cmdwin = Monwin.Subwin(stdscr, "cmd", CMDLINES, WINCOLS, MSGLINES + GLGLINES + RESPLINES, 0, textinput = True, bordertop = 0)
		self.homepos = (self._mainlines - 2, 1)
		stdscr.move(*self.homepos)

		self.windows = {"msg":self.msgwin, "glg": self.glgwin, "resp": self.respwin, "cmd": self.cmdwin}
		stdscr.refresh()

	def putline(self, window, message, color = "NORM"):
		"""Scroll the window and write the message on the bottom line.

		Positional parameters:
		window -- The name of the window("msg", "glg", "resp")
		message -- The message (a string)

		Keyword parameters:
		color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
		"""
		target = self.windows[window]
		target.putline(message, color)

	def getline(self):
		"""Get a line from the command window
		"""
		self.windows["cmd"].window.erase()
		self.windows["cmd"].window.move(0, 0)
		target = self.windows["cmd"].textbox
		return target.edit().strip()

	def alert(self):
		raise NotImplementedError("We cannot alert just yet")

	def message(self, message, color = "WARN"):
		"""Put a message in the message window

		Positional parameters:
		message -- The message (a string)

		Keyword parameters:
		color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
		"""
		self.putline("msg", message, color)

	def close(self):
		curses.endwin()
