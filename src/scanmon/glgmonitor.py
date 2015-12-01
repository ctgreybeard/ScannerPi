"""GLGMonitor - Processing for GLG monitor

`Source <src/scanmon.glgmonitor.html>`__
"""

from datetime import timedelta

import decimal
import logging
import sqlite3
import requests
import threading
import queue
from urwid import WidgetPlaceholder, Text, Columns, Padding

# Import our private modules
from scanmon.receivingstate import ReceivingState
from scanmon.scanner.formatter import Response
from scanmon.scanner import Command

class Reception:
    """Holds information related to a single reception

    Args:
        glgresp (Response): Scanner response object
    """

    def __init__(self, glgresp):
        self.starttime = glgresp.TIME
        self.duration = 0
        self.system = glgresp.NAME1
        self.group = glgresp.NAME2
        self.channel = glgresp.NAME3
        self.frequency_tgid = glgresp.FRQ_TGID
        self.ctcss_dcs = glgresp.CTCSS_DCS
        self.modulation = glgresp.MOD
        self.attenuation = glgresp.ATT
        self.system_tag = glgresp.SYS_TAG
        self.channel_tag = glgresp.CHAN_TAG
        self.p25nac = glgresp.P25NAC
        self.last_active_time = self.starttime
        self.last_active_state = True
        self.lastseen = None
        self.info_widget = None
        self.duration_widget = None
        self.dur_widget = None
        self.infostring = ''

    @property
    def sys_id(self):
        """A simple identifier for the System-Group-Channel
        """

        return '-'.join((self.system, self.group, self.channel,))

    def __eq__(self, other):
        """Reception equality -- equal if System, Group, Channel, and Startime are equal
        """

        if isinstance(other, Reception):
            return self.sys_id == other.sys_id and self.starttime == other.starttime
        else:
            raise ValueError("Cannot equate Reception to something else.")

class Titler(threading.Thread):
    """Reads from the _title_queue and updates the Icecast title

    This is running as a thread because the http transaction may
    block.
    """

    _AUTH = ('admin', 'carroll')
    _URL = 'http://localhost:8000/admin/metadata'
    # TODO(admin@greybeard.org): Parameterize these

    _TITLEPARAMS = {
        'mount': '/scanner.ogg',
        'mode': 'updinfo',
    }

    def __init__(self):
        super().__init__()
        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self._requests_session = requests.Session()
        self._requests_session.auth = self._AUTH
        self._requests_session.params = self._TITLEPARAMS
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.WARNING)
        self._title_queue = queue.Queue()
        self.daemon = True
        self.name = "**Titler**"
        self._running = False

    def run(self):
        """Set up logging the loop on the input queue. When a title is posted update Icecast2.
        """

        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self._running = True
        self.__logger.info(type(self).__name__+': Running')

        while self._running:
            try:
                new_title = self._title_queue.get(timeout=1)
                if new_title is not None:
                    # Update the title if it is there
                    self.update_title(new_title)
                else:
                    # `None` is a stop request
                    self._running = False
            except queue.Empty:
                pass    # Empty is OK

        self.__logger.info(type(self).__name__+': Stopping')

    def stop(self):
        """Stop running the queue loop.
        """

        self.__logger.info(type(self).__name__+': Stop requested')
        self._running = False

    def put(self, new_title):
        """Put a new title into the input queue for pickup.
        """

        self.__logger.debug("title: " + new_title)
        self._title_queue.put(new_title)

    def update_title(self, title):
        """Update the Icecast title using the established session object.
        """

        self.__logger.debug("update_title: %s", title)

        try:
            result = self._requests_session.get(self._URL, params={'song': title})
            if result.status_code != requests.codes.ok:      # pylint: disable=no-member
                self.__logger.error('Title update request error (%d): %s',
                                    result.status_code,
                                    result.text)
        except requests.exceptions.RequestException:
            self.__logger.exception("Error in title update request")

class GLGMonitor(ReceivingState):
    """Class to hold monitoring info for GLG monitoring.

    Usually only one instance is necessary.
    After initialization call process repeatedly to perform the monitoring."""

    IDLETIME = 11.0 # 11 seconds between transmissions is a new transmission
    TAGNONE = -1    # System and Channel tag NONE
    _TIMEFMT = '%H:%M:%S'
    _EPOCH = 3600 * 24 * 356    # A year of seconds (sort of ...)
    _DEFTITLE = "Bethel/Danbury, CT Fire/EMS Scanner"

    @property
    def sys_id(self):
        """Get the unique ID for this System/Group/Channel combination
        """
        if self.is_active:
            return '-'.join((self.system_name, self.group_name, self.channel_name))
        else:
            return None

    @property
    def is_active(self):
        """Get the transmission status.

        Checks the Squelch, returns True on open Squelch"""
        return self.squelch

    def __init__(self, monwin, args=None):
        """Initialize the instance"""
        super().__init__()
# Set up logging
        self.__logger = logging.getLogger(__name__).getChild(type(self).__name__)
        self.__logger.info(type(self).__name__+': Initializing')
        self.lastid = ''
        self.lastactive = 1.0
        self.squelch = False
        self.reception = None
        self.state = GLGMonitor.IDLE
        self.idletime = GLGMonitor.IDLETIME

        if args and hasattr(args, 'timeout') and args.timeout is not None:
            self.__logger.info("Timeout override: %s", args.timeout)
            try:
                self.idletime = float(args.timeout)
            except ValueError:
                self.__logger.error("Invalid timeout argument: %s", args.timeout)

        if (args and
                hasattr(args, 'database') and
                args.database is not None and
                len(args.database) > 0):
            self.__initdb__(args.database)
        else:
            self.__initdb__(':memory:')

        self.title_updater = Titler()
        self.title_updater.start()
        self.title_updater.put(GLGMonitor._DEFTITLE)     # Default idle title
        #self.__logger.setLevel(logging.ERROR)    # Keep the info logging until we get started

        # Set some instance variables that we need later
        self.monwin = monwin
        self.running = False
        self.send_count = 0
        self.attenuation = None
        self.channel_name = None
        self.channel_tag = None
        self.ctcss_dcs = None
        self.frequency_tgid = None
        self.glgresp = None
        self.group_name = None
        self.modulation = None
        self.mute = False
        self.p25nac = None
        self.receive_time = None
        self.system_name = None
        self.system_tag = None

        # Set up the idle Text widget
        self.idle_widget = Text(('green', '\u2026Idle\u2026'))
        self.current_widget = None
        self.scroll_win()

    def __initdb__(self, database):
        """Initialize the database for storing Receptions and tracking lastseen."""
        try:
            self.database = database
            self.__logger.info("Using database: %s", self.database)
            self.dbconn = sqlite3.connect(self.database,
                                          detect_types=sqlite3.PARSE_DECLTYPES,
                                          isolation_level=None)
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
            self.dbconn.execute("""CREATE TEMPORARY TABLE IF NOT EXISTS LastSeen
                ("System" TEXT,
                 "Group" TEXT,
                 "Channel" TEXT,
                 "LastTime" timestamp)""")
        except sqlite3.Error:
            self.__logger.exception("Error initializing database")
            raise

        # Build the lastseen table from the database
        try:
            self.dbconn.execute("""INSERT INTO LastSeen ("System", "Group", "Channel", "LastTime")
                SELECT "System", "Group", "Channel", MAX("Starttime") FROM "Reception"
                    GROUP BY "System", "Group", "Channel" """)
        except sqlite3.Error:
            self.__logger.exception("Error populating lastseen table")
            raise

    def create_reception(self, glgresp):
        """Create a Reception instance

        Args:
            glgresp (Response): Scanner response object

        Returns:
            Reception
        """

        self.__logger.debug("new Reception-%s", self.sys_id)
        self.state = GLGMonitor.RECEIVING
        reception = Reception(glgresp)
        curs = self.dbconn.execute('SELECT "LastTime" FROM "LastSeen" '
                                   'WHERE "System" == :system '
                                   'AND "Group" == :group '
                                   'AND "Channel" == :channel', reception.__dict__)

        row = curs.fetchone()
        if row:
            reception.lastseen = row['LastTime']
            dbupdate = """UPDATE LastSeen SET LastTime = :starttime
                WHERE "System" = :system AND "Group" = :group AND "Channel" = :channel"""
        else:
            reception.lastseen = None
            dbupdate = """INSERT INTO LastSeen ("System", "Group", "Channel", "LastTime")
                VALUES (:system, :group, :channel, :starttime)"""

        self.dbconn.execute(dbupdate, reception.__dict__)
        self.write_win(reception)
        return reception

    def accumulate_time(self):
        """Accumulate time in the current reception, set state.

        Time acculumates while the response is Active.
        During the timeout period time is not accumulated unless the same system becomes active;
        at that time the elapsed idle time is included in the reception.
        If the system times out or another system comes active during the
        timeout period then the idle time is not accumulated.
        """
        samesystem = self.sys_id == self.reception.sys_id
        self.__logger.debug("system: %s, samesystem: %s, active: %s",
                            self.sys_id, samesystem, self.is_active)

        if self.reception.last_active_state or samesystem:
            self.reception.duration = (self.receive_time - self.reception.starttime).seconds
            self.write_win(self.reception)

        self.reception.last_active_state = self.is_active

        if self.is_active:
            self.state = GLGMonitor.RECEIVING
            if samesystem:
                self.reception.last_active_time = self.receive_time
            else:
                self.write_database()
        else:
            self.state = GLGMonitor.TIMEOUT

    def write_database(self):
        """Write database record, set state"""
        self.__logger.debug("system: %s", self.reception.sys_id)

        if self.reception:
            try:
                dbwrite = """INSERT INTO "Reception"
                    ("Starttime", "Duration", "System", "Group", "Channel", "Frequency_TGID", "CTCSS_DCS",
                     "Modulation", "Attenuation", "SystemTag", "ChannelTag", "P25NAC") VALUES
                    (:starttime, :duration, :system, :group, :channel, :frequency_tgid, :ctcss_dcs,
                     :modulation, :attenuation, :system_tag, :channel_tag, :p25nac)"""
                self.dbconn.execute(dbwrite, self.reception.__dict__)
            except sqlite3.Error:
                self.__logger.exception("Error writing Reception to database")
                raise
        else:
            self.__logger.error("Cannot write database if no Reception exists!")

        self.scroll_win()
        self.title_updater.put(GLGMonitor._DEFTITLE)     # Default idle title

        if self.is_active:
            self.reception = self.create_reception(self.glgresp)
            self.state = GLGMonitor.RECEIVING
        else:
            self.reception = None
            self.state = GLGMonitor.IDLE

    def scroll_win(self, widget=None):
        """Scroll the output window.

        Args:
            widget (urwid.Widget): The widget to display, default is the idle Widget.

        References:
            self.current_widget

        Creates a new WidgetPlaceholder containing the supplied widget or
        idle_widget.
        """

        self.__logger.debug("")

        if widget is None:
            widget = self.idle_widget

        self.current_widget = WidgetPlaceholder(widget)

        self.monwin.putline('glg', self.current_widget)

    def write_win(self, reception):
        """Write the current reception info to the window
        """

        self.__logger.debug("system: %s", reception.sys_id)

        if not reception.dur_widget:
            # Compute the static information string once and cache it
            reception.dur_widget = Text(str(reception.duration))

            # Compute the frequency or 'NaN'
            with decimal.localcontext() as lctx:
                lctx.traps[decimal.InvalidOperation] = False
                frq = decimal.Decimal(reception.frequency_tgid)

            # Compute the 'lastseen' display value (HH:MM:SS)
            if reception.lastseen:
                delta = reception.starttime - reception.lastseen
                lastseen = str(timedelta(delta.days, delta.seconds, 0))
            else:
                lastseen = '*Forever'

            reception.infostring = (
                '{time:s}: '
                'Sys={sys:.<16s}|'
                'Grp={grp:.<16s}|'
                'Chan={chn:.<16s}|'
                'Freq={frq:#9.4f}|'
                'C/D={ctc:>3s} '
                'last={last:>8s}|'
                'dur=').format(time=reception.starttime.strftime(GLGMonitor._TIMEFMT),
                               sys=reception.system,
                               grp=reception.group,
                               chn=reception.channel,
                               frq=float(frq),
                               ctc=reception.ctcss_dcs,
                               last=lastseen)

            self.title_updater.put("{sys}|{grp}|{chan}".format(
                sys=reception.system,
                grp=reception.group,
                chan=reception.channel))

            self.current_widget.original_widget = Columns(
                [('pack', Text(reception.infostring)),
                 Padding(reception.dur_widget)])

        else:   # Update the existing duration
            reception.dur_widget.set_text(str(self.reception.duration))

    def parse_response(self, glgresp):
        """Accept a scanner.formatter.Response object, decode it, set GLGMonitor values.

        Args:
            glgresp (Response): scanner Response object
        """

        assert isinstance(glgresp, Response)
        assert glgresp.CMD == 'GLG'

        self.__logger.debug('Parsing Response(%s)', glgresp.display(glgresp))

        self.receive_time = glgresp.TIME
        self.system_name = glgresp.NAME1
        self.group_name = glgresp.NAME2
        self.channel_name = glgresp.NAME3
        self.frequency_tgid = glgresp.FRQ_TGID
        self.ctcss_dcs = glgresp.CTCSS_DCS
        self.modulation = glgresp.MOD
        self.attenuation = glgresp.ATT == '1'

        if glgresp.SYS_TAG and glgresp.SYS_TAG != 'NONE':
            self.system_tag = int(glgresp.SYS_TAG)
        else:
            self.system_tag = GLGMonitor.TAGNONE

        if glgresp.CHAN_TAG and glgresp.CHAN_TAG != 'NONE':
            self.channel_tag = int(glgresp.CHAN_TAG)
        else:
            self.channel_tag = GLGMonitor.TAGNONE

        self.p25nac = glgresp.P25NAC
        self.squelch = glgresp.SQL == '1'
        self.mute = glgresp.MUT == '1'

    def process(self, glgcmd, glgresp):
        """Process a GLG response

        Args:
            glgcmd (Command): The Command sent to the scanner
            glgresp (Response): The scanner's response

        This is the main routine. It should be called repeatedly with a Scanner Response object.
        """

        del glgcmd  # unused

        self.__logger.debug("processing: %s, state: %s", glgresp, self.state)
        self.glgresp = glgresp
        self.parse_response(self.glgresp)

        if self.is_idle:
            if self.is_active:
                self.reception = self.create_reception(self.glgresp)

        elif self.is_receiving:
            self.accumulate_time()

        elif self.is_timeout:
            time_exceeded = (glgresp.TIME -
                             self.reception.last_active_time).total_seconds() > self.idletime

            if time_exceeded:
                self.__logger.debug("Timeout: %s", self.reception.sys_id)

            if self.is_active or not time_exceeded:
                self.accumulate_time()

            elif time_exceeded:
                self.write_database()

        else:
            raise RuntimeError("Invalid GLG monitor state: {}".format(self.state))

        self.send_count -= 1

        if self.send_count < 0:
            self.__logger.warning("GLG Monitor send count less than zero: %d", self.send_count)
            self.send_count = 0

        if self.send_count == 0 and self.running:
            self.delay_glg()

        # Always return False, we watch all GLG responses
        return False

    def delay_glg(self, delay=0.5):
        """Set a delayed GLG command.

        Args:
            delay (float): Delay in seconds. Default 0.5.
        """

        self.monwin.set_alarm_in(delay, self.send_glg)

    def send_glg(self, mainloop, user_data):
        """Send a GLG command to the scanner with a callback.

        Args:
            mainloop (urwid.mainloop): The urwid mainloop instance (not used)
            user_data (object): The user data set with the alarm (not used)
        """

        del mainloop, user_data

        self.monwin.scanner.send_command(Command('GLG', callback=self.process))
        self.send_count += 1

    def start(self):
        """Start monitoring.
        """

        self.running = True
        if self.send_count == 0:
            self.send_glg(self.monwin, None)

    def stop(self):
        """Stop monitoring.
        """

        self.running = False

