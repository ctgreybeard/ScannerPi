'''GLGMonitor - Processing for GLG monitor
'''

from datetime import datetime as DateTime, timedelta as TimeDelta
import logging
from logging import DEBUG as LDEBUG, INFO as LINFO, WARNING as LWARNING, ERROR as LERROR, CRITICAL as LCRITICAL
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
		self.lastActiveTime = self.Starttime
		self.lastActiveState = True

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

	IDLETIME = 15.0		# 15 seconds between transmissions is a new transmission
	TAGNONE = -1	# System and Channel tag NONE
	_TIMEFMT = '%H:%M:%S'
	_EPOCH = 3600 * 24 * 356	# A year of seconds

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

	def __init__(self, monwin = None, db = None, args = None):
		"""Initialize the instance"""
		super().__init__()
# Set up logging
		self.__logger = logging.getLogger().getChild(__name__)
		self.__logger.info(__class__.__name__+': Initializing')
		self.lastseen = {}
		self.lastid = ''
		self.lastactive = 1.0
		self.squelch = False
		self.monwin = monwin
		self.reception = None
		self.state = GLGMonitor.IDLE
		self.db = db
		self.IDLETIME = GLGMonitor.IDLETIME
		if args and hasattr(args, 'timeout'):
			self.__logger.info("Timeout override: %s", args.timeout)
			try:
				self.IDLETIME = float(args.timeout)
			except:
				self.__logger.error("Invalid timeout argument: %s", args.timeout)

	def createReception(self, glgresp):
		"""Create a Reception instance"""
		self.__logger.debug("new Reception-%s", self.sys_id)
		self.state = GLGMonitor.RECEIVING
		self.reception = Reception(glgresp)
		self.writeWin()

	def accumulateTime(self):
		"""Accumulate time in the current reception, set state"""
		samesystem = self.sys_id == self.reception.sys_id
		self.__logger.debug("system: %s, samesystem: %s, isActive: %s", self.sys_id, samesystem, self.isActive)

		if self.reception.lastActiveState or samesystem:
			self.reception.Duration = (self.receiveTime - self.reception.Starttime).total_seconds()
			self.writeWin()

		self.reception.lastActiveState = self.isActive

		if self.isActive:
			self.state = GLGMonitor.RECEIVING
			if samesystem:
				self.reception.lastActiveTime = self.receiveTime
			else:
				self.writeDatabase()
		else:
			self.state = GLGMonitor.TIMEOUT

	def writeDatabase(self):
		"""Write database record, set state"""
		self.__logger.debug("system: %s", self.reception.sys_id)
		self.scrollWin()
		if self.isActive:
			self.createReception(self.glgresp)
			self.state = GLGMonitor.RECEIVING
		else:
			self.reception = None
			self.state = GLGMonitor.IDLE

	def scrollWin(self):
		"""Scroll the output window if necessary"""
		self.__logger.debug("")
		self.monwin.putline('.', scroll = True)

	def writeWin(self):
		"""Write the current reception info to the window"""
		self.__logger.debug("system: %s", self.reception.sys_id)
# Temorary line for testing only
		try:
			frq = float(self.reception.Frequency_TGID)
		except ValueError:
			frq = decimal.Decimal('NaN')
		self.monwin.putline("{time:s}: Sys={sys:.<16s}|Grp={grp:.<16s}|Chan={chn:.<16s}|Freq={frq:#9.4f}|C/D={ctc:>3s} dur={dur}".\
			format(time=self.reception.Starttime.strftime(GLGMonitor._TIMEFMT),
				sys=self.reception.System,
				grp=self.reception.Group,
				chn=self.reception.Channel,
				frq=frq,
				dur=int(self.reception.Duration),
				ctc=self.reception.CTCSS_DCS), scroll = False)

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
			self.channelTag = int(glgresp.CHAN_TAG)
		except ValueError:
			self.channelTag = GLGMonitor.TAGNONE
		self.p25nac = glgresp.P25NAC
		self.squelch = glgresp.SQL == '1'
		self.mute = glgresp.MUT == '1'

	def process(self, glgresp):
		"""Process a GLG response"""
		self.__logger.debug("processing: %s, state: %s", glgresp, self.state)
		self.glgresp = glgresp
		self.parseResponse(self.glgresp)
		if self.isIdle:
			if self.isActive:
				self.createReception(self.glgresp)
		elif self.isReceiving:
			self.accumulateTime()
		elif self.isTimeout:
			timeExceeded = (DateTime.now() - self.reception.lastActiveTime).total_seconds() > self.IDLETIME
			if timeExceeded:
				self.__logger.debug("Timeout: %s", self.reception.sys_id)
			if self.isActive or not timeExceeded:
				self.accumulateTime()
			elif timeExceeded:
				self.writeDatabase()
		else:
			raise RuntimeError("Invalid GLG monitor state: {}".format(self.state))
