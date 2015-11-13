"""
New Scanmon window based on urwid
"""

import logging
import urwid
import queue
from urwid import Columns, Text, Padding, Frame, WidgetPlaceholder, Pile, Filler, Divider, ListBox, SimpleListWalker, BoxAdapter, SimpleFocusListWalker, Edit, AttrMap
import time
import threading
import sys
import serial
from uuid import uuid4

class Monwin(urwid.MainLoop):
    """
    Main class for the window.

    Handles all display functions, command entry, monitors the scanner for input.
    """

    class CmdLine(urwid.WidgetWrap):
        """
        The command line input area.

        Posts any command entered to the command queue when Enter is pressed.
        """

        def __init__(self, cmdQueue):
            """
            Initialize the CmdLine class.

            Args:
                cmdQueue (Queue): the queue into which to put the entered comands.
            """
            self.logger = logging.getLogger(__name__)
            self.cmdQueue = cmdQueue
            super().__init__(Edit(caption=('green', "Cmd> "), wrap = 'clip'))

        def keypress(self, size, key):
            """
            Watch for the Enter key and post commands to the command queue.
            """

            try:
                keyret = self._w.keypress(size, key)
                if keyret == 'enter':
                    cmd = self._w.edit_text
                    self.logger.debug('keypress: Command: "{}"'.format(cmd))
                    self._w.set_edit_text('')
                    self.cmdQueue.put(cmd)
                    keyret = None
            except Exception as e:
                self.logger.exception('keypress error')

            return keyret

    class ScrollWin(urwid.WidgetWrap):
        """
        Main scrolling windows within the program window.

        These handle auto scrolling and mouse scrolling.
        """

        def __init__(self, title = None):
            """
            Initialize the ScrollWin.

            Args:
                title (str): Optional title string for the window header.
            """
            self.logger = logging.getLogger(__name__)
            self.scroller = ListBox(SimpleFocusListWalker([]))
            if title:
                self.frameTitle = Columns([('pack', Text('--')),('pack', Text(('wintitle', title))), Divider('-')])
            else:
                self.frameTitle = None
            return super().__init__(Frame(self.scroller, header = self.frameTitle))

        def append(self, wid):
            """
            Append a line to the indow contents.

            Args:
                wid (str, Widget, or tuple): The line to append to the window contents.
                    May be a plain string, an urwid Widget, or a tuple with an attributed string.
            """

            try:
                focusNow = self.scroller.focus_position
            except:
                focusNow = -1
            bottom = focusNow == len(self.scroller.body) - 1  # Bottom widget in focus?
            self.scroller.body.append(AttrMap(wid, None,
                {'NORM': 'NORMF',
                 'WARN': 'WARNF',
                 'ALERT': 'ALERTF',
                 'default': 'NORMF' }))
            if bottom:
                self.logger.debug('scrolling')
                self.scroller.set_focus(focusNow + 1, coming_from = 'above')
            else:
                self.logger.debug('skipping scrolling')

        def mouse_event(self, size, event, button, col, row, focus):

            focus_dir = None

            if button == 4.0:   # scroll wheel down
                focus_dir = -1
                from_dir = 'below'
                self.logger.debug('Scroll wheel down')
            elif button == 5.0: # scroll wheel up
                focus_dir = 1
                from_dir = 'above'
                self.logger.debug('Scroll wheel up')

            if focus_dir is not None:
                handled = True
                try:
                    newpos = self.scroller.focus_position + focus_dir
                    if newpos >= 0 and newpos < len(self.scroller.body):
                        self.scroller.change_focus(size, newpos, coming_from = from_dir)
                        self.logger.debug('newpos=%d', newpos)
                except IndexError:
                    self.logger.exception('OUCH! size={}, event={}, button={}, col={}, row={}, focus={}, dir={}'.format(size, event, button, col, row, focus, focus_dir))
                    self.append(Text('OUCH! size={}, event={}, button={}, col={}, row={}, focus={}, dir={}'.format(size, event, button, col, row, focus, focus_dir)))
            else:
                handled = self._w.mouse_event(size, event, button, col, row, focus)

            return handled

    def show_or_exit(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        elif key == 'enter':
            if self.widget.focus_position != 'footer':  # readjust focus if needed
                self.widget.focus_position = 'footer'
        else:
            self.resp.append(Text(repr(key)))

    def sendGLG(self):
        while True:
            if self.runGLG:
                self.logger.debug('Sending')
                self.scanner.write(b'GLG\r')
            time.sleep(5)

    def readScanner(self):
        self.logger.debug('Reading')
        while self.scanner.inWaiting() > 0:
            readIt = self.scanner.read(self.scanner.inWaiting())
            self.readBuf += readIt
            self.logger.debug('Scanner sent: ' + repr(self.readBuf))

        while b'\r' in self.readBuf:
            (rLine, sep, self.readBuf) = self.readBuf.partition(b'\r')
            rLine = rLine.decode(errors='ignore')
            self.putline('glg', rLine)
            self.logger.debug('Read scanner: ' + repr(rLine))

    def __init__(self, doCmdQueue):
        self.logger = logging.getLogger(__name__)
        self.mdl = Text('BCD996XT')
        self.ver = Text('Ver [checking...]')
        self.doCmdQueue = doCmdQueue
        self.threadID = threading.current_thread().ident
        header = Columns([
            ('weight', 60, Divider('-')),
            ('weight', 30, Padding(AttrMap(self.mdl, 'wintitle'), min_width = 10, align = 'left')),
            ('weight', 20, Divider('=')),
            ('weight', 30, Padding(AttrMap(self.ver, 'wintitle'), min_width = 10, align = 'right', width = 'pack')),
            ('weight', 60, Divider('-'))
            ])

        footer = Monwin.CmdLine(self.doCmdQueue)

        self.msg = Monwin.ScrollWin('Messages')
        self.glg = Monwin.ScrollWin('Channel Monitor')
        self.resp = Monwin.ScrollWin('Command Response')
        self.windows = {'msg': self.msg, 'glg': self.glg, 'resp': self.resp}

        body = Pile([
            ('weight', 5, self.msg),
            ('weight', 33, self.glg),
            ('weight', 11, self.resp)
            ])
        frame = Frame(body, header = header, footer = footer, focus_part = 'footer')
        palette = [
            ('wintitle', 'yellow', 'default', 'bold'),
            ('green', 'dark green', 'default', 'bold'),
            ('NORM', 'light gray', 'default', 'default'),
            ('NORMF', 'white', 'default', 'standout'),
            ('ALERT', 'light red', 'default', 'default'),
            ('ALERTF', 'standout,light red', 'default', 'standout'),
            ('WARN', 'light magenta', 'default', 'underline'),
            ('WARNF', 'standout,light magenta', 'default', 'standout,underline'),
            ('default', 'NORM'),
            ]
        super().__init__(frame, unhandled_input=self.show_or_exit, palette=palette)
        (screenCols, screenRows) = self.screen.get_cols_rows()
        glgRows = screenRows - (2 + 5 + 11)

        self.msg.append(Text(('NORM', 'Screen has {:d} rows and {:d} columns'.format(screenRows, screenCols))))
        self.msg.append(Text(('NORM', 'glg has {:d} rows'.format(glgRows))))

        self.scanner = serial.Serial(port='/dev/ttyUSB0', baudrate=115200)
        self.scanner.nonblocking()
        self.watch_file(self.scanner.fileno(), self.readScanner)
        self.logger.info("Watching scaner at file #%d", self.scanner.fileno())
        self.readBuf = b''
        self.runGLG = False
        glgThread = threading.Thread(target=self.sendGLG, name = 'sendGLG')
        glgThread.daemon = True
        glgThread.start()


    def _aPutline(self, mainLoop, userData):
        """Called via set_alarm_in when putline is called outside the main thread"""
        (window, message, *color) = userData
        color = color[0] if len(color)>0 else 'NORM'
        self.putline(window, message, color)

    def putline(self, window, message, color = 'NORM'):
        """Scroll the window and write the message on the bottom line.

        Positional parameters:
        window -- The name of the window("msg", "glg", "resp")
        message -- The message (a string, a tuple[attributed string(s)] or a Widget)

        Keyword parameters:
        color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
        """
        if self.threadID == threading.current_thread().ident:
            win = self.windows[window]
            if win is None:
                win = 'msg'

            try:
                self.logger.debug('window={}, message={}, color={}'.format(window, repr(message), color))
                if isinstance(message, urwid.Widget): # a Widget?
                    wid = message
                elif isinstance(message, str):        # a bare string gets color
                    wid = Text((color, message))
                else:
                    wid = Text(message)               # probably a tuple
                self.windows[window].append(wid)
            except Exception as e:
                self.logger.exception('exception:')
        else:
            self.logger.debug('redirect: "{}", "{}", "{}"'.format(window, message, color))
            self.set_alarm_in(0.0, self._aPutline, user_data = (window, message, color))

    def message(self, message, color = "WARN"):
        """Put a message in the message window

        Positional parameters:
        message -- The message (a string)

        Keyword parameters:
        color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
        """
        self.putline("msg", message, color)

    def _aSetText(self, mainLoop, userData):
            (wid, txt) = userData
            self.setText(wid, txt)

    def setText(self, wid, txt):
        if self.threadID == threading.current_thread().ident:
            self.logger.debug(txt)
            wid.set_text(txt)
        else:
            self.set_alarm_in(0.0, self._aSetText, (wid, txt))

    def doIt(self, f, data = None, time = 0.0):
        '''Called by other threads, schedules a method call for execution by mainLoop'''
        self.set_alarm_in(time, f, data)

    def doQuit(self, mainLoop = None, user_data = None):
        self.logger.warning('QUIT requested')
        if self.threadID == threading.current_thread().ident:
            raise urwid.ExitMainLoop
        else:
            self.set_alarm_in(0.1, self.doQuit)

    def doNothing(self, mainLoop, user_data):
        '''Does nothing useful except to waken the main loop to cause refreshes.
        I believe this works around a bug in urwid'''
        mainLoop.set_alarm_in(0.5, mainLoop.doNothing)

def _loopTest():
    dologger = logging.getLogger(__name__)
    dologger.info('starting')
    global _loopTestTime
    loopTestTime = "I'm not done yet!"
    dologger.debug(_loopTestTime)
    monwin.putline('msg', loopTestTime, 'WARN')
    now1 = time.time()
    time.sleep(5)
    now2 = time.time()
    loopTestTime = "_loopTest took {:5.3f} seconds".format(now2 - now1)
    monwin.putline('msg', loopTestTime, 'ALERT')
    monwin.setText(monwin.ver, 'Ver 2.3.4')

    dologger.info(_loopTestTime)

def _doCommands(monwin, queue):
    dologger = logging.getLogger(__name__)
    dologger.info('starting')
    while True:
        try:
            cmd = queue.get()
            dologger.info(repr(cmd))
            monwin.putline('resp', Text('CMD: {}'.format(cmd)))

            if cmd is None:
                dologger.info('quitting')
                break
            elif cmd == 'quit':
                monwin.doQuit()
            elif cmd == 'test':
                monwin.putline('resp', 'Testing ... 1 ... 2 ... 3 ...', 'WARN')
            elif cmd == 'stop':
                monwin.runGLG = False
            elif cmd == 'go':
                monwin.runGLG = True
            else:
                monwin.putline('resp', "I don't know how to " + repr(cmd), 'ALERT')
                dologger.error('Unknown command: ' + repr(cmd))
        except:
            dologger.exception('Exception')

# Run simulation for testing
if __name__ == '__main__':
    doCmdQueue = queue.Queue()
    fmt = '%(asctime)s -%(levelname)s- *%(threadName)s* %%%(funcName)s%% %(message)s'
    logging.basicConfig(filename='Monwin.log', filemode = 'w', level=logging.DEBUG, format = fmt)
    logger = logging.getLogger(__name__)
    now1 = time.time()

    monwin = Monwin(doCmdQueue)

    lt = threading.Thread(target=_loopTest, name = 'LoopTest')
    dc = threading.Thread(target=_doCommands, name = 'DoCommands', args = (monwin, doCmdQueue))
    monwin.doNothing(monwin, None)
    lt.start()
    dc.start()
    monwin.run()
    doCmdQueue.put(None)

    now2 = time.time()
    logger.info("That took {:5.3f} seconds".format(now2 - now1))
    dc.join()
    logging.shutdown()
