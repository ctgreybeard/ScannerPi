'''GLGMonitor - Processing for GLG monitor
'''

from datetime import datetime as DateTime, timedelta as TimeDelta
from .scanner.formatter import Response
from .receivingstate import ReceivingState

class Reception:
	"""Holds information related to a single reception"""

	def __init__(self, glgresp):
		self.Starttime = glgresp.TIME
		self.Duration = 0.0
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
		self.lastActive = True

	@property
	def sys_id(self):
		return '-'.join((self.System, self.Group, self.Channel,))

	def __eq__(self, other):
		if isinstance(other, Reception):
			return self.sys_id == other.sys_id and self.Starttime == other.Starttime
		else:
			raise ValueError

# Class for GLG monitoring
class GLGMonitor(ReceivingState):
	"""Class to hold monitoring info for GLG monitoring."""

	IDLE = 15.0		# 15 seconds between transmissions is a new transmission
	TAGNONE = -1	# System and Channel tag NONE

	@property
	def sys_id(self):
		"""Get the unique ID for this System/Group.Channel combination"""
		if self.isActive:
			return '-'.join((self.systemName, self.groupName, self.channelName))
		else:
			return None

	@property
	def isActive(self):
		"""Get the transmission status.

		Checks the Squelch, returns True on open Squelch"""
		return self.squelch

	def __init__(self, monwin = None, db = None):
		"""Initialize the instance"""
		super().__init__()
		self.lastseen = {}
		self.lastid = ''
		self.lastactive = 1.0
		self.squelch = False
		self.monwin = monwin
		self.reception = None
		self.state = GLGMonitor.IDLE
		self.db = db

	def createReception(self, glgresp):
		"""Create a Reception instance"""
		self.state = GLGMonitor.RECEIVING
		self.reception = Reception(glgresp)
		self.scrollWin()
		self.writeWin()

	def accumulateTime(self):
		"""Accumulate time in the current reception, set state"""
		samesystem = self.sys_id == self.reception.sys_id

		if self.reception.lastActive or samesystem:
			self.reception.Duration = (self.receiveTime - self.reception.Starttime).total_seconds()
			self.writeWin()

		self.reception.lastActive = self.isActive

		if self.isActive:
			self.state = GLGMonitor.RECEIVING
			if not samesystem:
				self.writeDatabase()
		else:
			self.state = GLGMonitor.TIMEOUT

	def writeDatabase(self):
		"""Write database record, set state"""
		if self.isActive:
			self.createReception(self.glgresp)
			self.state = GLGMonitor.RECEIVING
		else:
			self.reception = None
			self.state = GLGMonitor.IDLE

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
		self.glgresp = glgresp
		parseResponse(self.glgresp)
		if self.isActive:
			self.lastActive = glgresp.TIME
		if self.isIdle:
			if self.isActive:
				createReception(self.glgresp)
			else:
				pass
		elif self.isReceiving:
			accumulateTime()
		elif self.isTimeout:
			timeExceeded = (self.lastActive - DateTime.now()).total_seconds() > GLGMonitor.IDLE
			if self.isActive or not timeExceeded:
				accumulateTime()
			elif timeExceeded:
				writeDatabase()
		else:
			raise RuntimeError("Invalid GLG monitor state: {}".format(self.state))
