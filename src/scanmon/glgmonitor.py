"""GLGMonitor - Processing for GLG monitor"""

from datetime import datetime, timedelta

import decimal
import logging
import sqlite3

# Import our private modules
from scanmon.receivingstate import ReceivingState
from scanmon.scanner.formatter import Response

class Reception:
    """Holds information related to a single reception"""

    def __init__(self, glgresp):
        self.Starttime = glgresp.TIME
        self.Duration = 0
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
        """A simple identifier for the System-Group-Channel"""
        return '-'.join((self.System, self.Group, self.Channel,))

    def __eq__(self, other):
        """Reception equality -- equal if System, Group, Channel, and Startime are equal"""
        if isinstance(other, Reception):
            return self.sys_id == other.sys_id and self.Starttime == other.Starttime
        else:
            raise ValueError

class GLGMonitor(ReceivingState):
    """Class to hold monitoring info for GLG monitoring.

    Usually only one instance is necessary. After initialization call process repeatedly to perform the monitoring."""

    IDLETIME = 11.0 # 11 seconds between transmissions is a new transmission
    TAGNONE = -1    # System and Channel tag NONE
    _TIMEFMT = '%H:%M:%S'
    _EPOCH = 3600 * 24 * 356    # A year of seconds (sort of ...)

    @property
    def sys_id(self):
        """Get the unique ID for this System/Group/Channel combination"""
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
        self.lastid = ''
        self.lastactive = 1.0
        self.squelch = False
        self.monwin = monwin
        self.reception = None
        self.state = GLGMonitor.IDLE
        self.db = db
# FIXME: Straighten out db param and args.database processing
        self.IDLETIME = GLGMonitor.IDLETIME
        if args and hasattr(args, 'timeout') and args.timeout is not None:
            self.__logger.info("Timeout override: %s", args.timeout)
            try:
                self.IDLETIME = float(args.timeout)
            except:
                self.__logger.error("Invalid timeout argument: %s", args.timeout)
        if args and hasattr(args, 'database') and args.database is not None and len(args.database) > 3:
            self.__initdb__(args.database)
        else:
            self.__initdb__(':memory:')

    def __initdb__(self, database):
        """Initialize the database for storing Receptions and tracking lastseen."""
        try:
            self.db = database
            self.__logger.info("Using database: %s", self.db)
            self.dbconn = sqlite3.connect(self.db, detect_types = sqlite3.PARSE_DECLTYPES, isolation_level = None)
            self.dbconn.row_factory = sqlite3.Row
            create = """CREATE TABLE IF NOT EXISTS "Reception"
                ("Starttime" timestamp,
                 "Duration" integer,
                 "System" text,
                 "Group" text,
                 "Channel" text,
                 "Frequency_TGID" text,
                 "CTCSS_DCS" integer,
                 "Modulation" text,
                 "Attenuation" boolean,
                 "SystemTag" integer,
                 "ChannelTag" integer,
                 "P25NAC" text)"""
            self.dbconn.execute(create)
        except:
            self.__logger.exception("Error initializing database")
            raise
        # Build the lastseen table from the database
        try:
            self.dbconn.execute("""CREATE TEMPORARY TABLE LastSeen
                AS SELECT "System", "Group", "Channel", MAX("Starttime") AS 'LastTime timestamp' FROM "Reception"
                    GROUP BY "System", "Group", "Channel" """)
            r = self.dbconn.execute("""pragma tableinfo(temp.LastSeen)""")
            for row in r:
                self.__logger.info
        except:
            self.__logger.exception("Error populating lastseen table")
            raise

    def createReception(self, glgresp):
        """Create a Reception instance"""
        self.__logger.debug("new Reception-%s", self.sys_id)
        self.state = GLGMonitor.RECEIVING
        self.reception = Reception(glgresp)
        curs = self.dbconn.execute("""SELECT "LastTime" FROM "LastSeen"
            WHERE "System" == :System AND "Group" == :Group AND "Channel" == :Channel""", self.reception.__dict__)
        row = curs.fetchone()
        if row:
            assert isinstance(row['LastTime'], datetime), "LastSeen.LastTime is not a datetime"
            self.reception.lastseen = row['LastTime']
            dbupdate = """UPDATE LastSeen SET LastTime = :Starttime
                WHERE "System" = :System AND "Group" = :Group AND "Channel" = :Channel"""
        else:
            self.reception.lastseen = None
            dbupdate = """INSERT INTO LastSeen ("System", "Group", "Channel", "LastTime")
                VALUES (:System, :Group, :Channel, :Starttime)"""
        self.dbconn.execute(dbupdate, self.reception.__dict__)
        self.writeWin()

    def accumulateTime(self):
        """Accumulate time in the current reception, set state.

        Time acculumates while the response is Active. During the timeout period time is not
        accumulated unless the same system becomes active; at that time the elapsed idle time is included in the
        reception. If the system times out or another system comes active during the timeout period then the idle
        time is not accumulated."""
        samesystem = self.sys_id == self.reception.sys_id
        self.__logger.debug("system: %s, samesystem: %s, isActive: %s", self.sys_id, samesystem, self.isActive)

        if self.reception.lastActiveState or samesystem:
            self.reception.Duration = (self.receiveTime - self.reception.Starttime).seconds
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

        if self.reception:
            try:
                dbwrite = """INSERT INTO "Reception"
                    ("Starttime", "Duration", "System", "Group", "Channel", "Frequency_TGID", "CTCSS_DCS",
                     "Modulation", "Attenuation", "SystemTag", "ChannelTag", "P25NAC") VALUES
                    (:Starttime, :Duration, :System, :Group, :Channel, :Frequency_TGID, :CTCSS_DCS,
                     :Modulation, :Attenuation, :SystemTag, :ChannelTag, :P25NAC)"""
                self.dbconn.execute(dbwrite, self.reception.__dict__)
            except:
                self.__logger.exception("Error writing Reception to database")
                raise
        else:
            self.__logger.error("Cannot write database if no Reception exists!")

        self.scrollWin()

        if self.isActive:
            self.createReception(self.glgresp)
            self.state = GLGMonitor.RECEIVING
        else:
            self.reception = None
            self.state = GLGMonitor.IDLE

    def scrollWin(self):
        """Scroll the output window."""
        self.__logger.debug("")
        try:
            self.monwin.putline('\u2026Idle\u2026', scroll = True)
        except:
            self.monwin.putline('...Idle...', scroll = False)   # Just in case the '\u2026' is rejected

    def writeWin(self):
        """Write the current reception info to the window"""
        self.__logger.debug("system: %s", self.reception.sys_id)

# Compute the static information string once and cache it
        if not hasattr(self.reception, 'infocache'):
# Compute the frequency or 'NaN'
            with decimal.localcontext() as lctx:
                lctx.traps[decimal.InvalidOperation] = False
                frq = decimal.Decimal(self.reception.Frequency_TGID)

# Compute the 'lastseen' display value (HH:MM:SS)
            if self.reception.lastseen:
                d = self.reception.Starttime - self.reception.lastseen
                lastseen = str(timedelta(d.days, d.seconds, 0))
            else:
                lastseen = '*Forever'
            self.reception.infocache = \
                "{time:s}: Sys={sys:.<16s}|Grp={grp:.<16s}|Chan={chn:.<16s}|Freq={frq:#9.4f}|C/D={ctc:>3s} last={last:>8s}". \
                    format(time=self.reception.Starttime.strftime(GLGMonitor._TIMEFMT),
                        sys=self.reception.System,
                        grp=self.reception.Group,
                        chn=self.reception.Channel,
                        frq=frq,
                        ctc=self.reception.CTCSS_DCS,
                        last=lastseen)
        self.monwin.putline("{info:s}| dur={dur}".format(
                dur=self.reception.Duration,
                info = self.reception.infocache),
            scroll = False)

    def parseResponse(self, glgresp):
        """Accept a scanner.formatter.Response object, decode it, set GLGMonitor values."""
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
        """Process a GLG response

        This is the main reoutine. It should be called repeatedly with a Scanner Response object."""
        self.__logger.debug("processing: %s, state: %s", glgresp, self.state)
        self.glgresp = glgresp
        self.parseResponse(self.glgresp)
        if self.isIdle:
            if self.isActive:
                self.createReception(self.glgresp)
        elif self.isReceiving:
            self.accumulateTime()
        elif self.isTimeout:
            timeExceeded = (glgresp.TIME - self.reception.lastActiveTime).total_seconds() > self.IDLETIME
            if timeExceeded:
                self.__logger.debug("Timeout: %s", self.reception.sys_id)
            if self.isActive or not timeExceeded:
                self.accumulateTime()
            elif timeExceeded:
                self.writeDatabase()
        else:
            raise RuntimeError("Invalid GLG monitor state: {}".format(self.state))
