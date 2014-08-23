'''GLGMonitor - Processing for GLG monitor
'''

from datetime import datetime, timedelta
from time import time
from .scanner.formatter import Response
from .receivingstate import ReceivingState as State

class Reception:
	"""Holds information related to a single reception"""

	def __init__(self, glgresp):
		self.Starttime = glgresp.TIME
		self.Duration =0.0
		self.System = glgresp.NAME1
		self.Group = glgresp.NAME2
		self.Channel = glgresp.NAME3
		self.Frequency_TGID = glgresp.FRQ_TGID
		self.CTCSS_DCS = glgresp.CTCSS_DCS
		self.Modulation = glgresp.MOD
		self.Attenuation = glgresp.ATT
		self.SystemTag = glgresp.SYS_TAG
		self.ChannelTag = glgresp.CHAN_TAG
		self.P25NAC = glgresp.P25NAC
	
	@property
	def sys_id(self):
		return '-'.join((self.System, self.Group, self.Channel,))
	
	def __eq__(self, other):
		if isinstance(other, Reception):
			return self.sys_id == other.sys_id and self.Starttime == other.Starttime
		else:
			raise ValueError

# Class for GLG monitoring
class GLGMonitor:
	"""Class to hold monitoring info for GLG monitoring."""

	IDLE = 15.0		# 15 seconds between transmissions is a new transmission
	TAGNONE = -1	# System and Channel tag NONE

	@property
	def sysId(self):
		"""Get the unique ID for this System/Group.Channel combination"""
		return '-'.join((self.systemName, self.groupName, self.channelName))

	@property
	def isActive(self):
		"""Get the transmission status.

		Checks the Squelch, returns True on open Squelch"""
		return self.squelch == '1'

	def __init__(self):
		"""Initialize the instance"""
		self.lastseen = {}
		self.lastid = ''
		self.lastactive = 1.0
		self.squelch = ''
		self.state = State.IDLE

	def createReception(self):
		"""Create a Reception instance"""
		self.state = State.RECEIVING
		self.reception = Reception(glgresp)

	def accumulateTime(self):
		"""Accumulate time in the current reception, set state"""
		pass

	def writeDatabase(self):
		"""Write database record, set state"""
		pass

	def scrollWin(self):
		"""Scroll the output window if necessary"""
		pass

	def writeWin(self):
		"""Write the current reception info to the window"""
		pass

	def parseResponse(self, glgresp):
		assert isinstance(glgresp, Response)
		assert glgresp.CMD == 'GLG'
		self.receiveTime = glgresp.TIME
		self.systemName = glgresp.NAME1
		self.groupName = glgresp.NAME2
		self.channelName = glgresp.NAME3
		self.frequency_tgid = glgresp.FRQ_TGID
		self.ctcss_dcs = glgresp.CTCSS_DCS
		self.modulation = glgresp.MOD
		self.attenuation = glgresp.ATT == '1'
		try:
			self.systemTag = int(glgresp.SYS_TAG)
		except ValueError:
			self.systemTag = GLGMonitor.TAGNONE
		try:
			self.channelTag = int(glgrsp.CHAN_TAG)
		except ValueError:
			self.channelTag = GLGMonitor.TAGNONE
		self.p25nac = glgresp.P25NAC
		self.squelch = glgresp.SQL == '1'
		self.mute = glgresp.MUT == '1'

	def process(self, glgresp):
		"""Process a GLG response"""
		parseResponse(glgresp)
		if self.isActive:
			self.lastActive = glgresp.TIME
		if self.state == State.IDLE:
			if self.isactive:
				createReception()
			else:
				pass
		elif self.state == State.RECEIVING:
			accumulateTime()
		elif self.state == State.TIMEOUT:
			timeExceeded = self.lastactive - time() > GLGMonitor.IDLE
			if self.isActive or not timeExceeded:
				accumulateTime()
			elif timeExceeded:
				writeDatabase()
			else:
				pass
		else:
			raise RuntimeError("Invalid GLG monitor state: {}".format(self.state))
