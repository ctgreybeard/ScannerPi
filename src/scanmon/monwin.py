"""
New Scanmon window based on urwid
"""

import logging
import urwid
from urwid import \
    AttrMap,\
    Columns,\
    Divider,\
    Edit,\
    Frame,\
    ListBox,\
    Padding,\
    Pile,\
    SimpleFocusListWalker,\
    Text
import time
import threading

def _do_nothing(main_loop, user_data):
    """Does nothing useful except to waken the main loop to cause refreshes.

    I believe this works around a bug in urwid. Rescedules itslef ever 0.5 seconds to
    keep things alive.

    Args:
        main_loop (urwid.main_loop): Standard args for set_alarm method
        user_data (object): Standard args for set_alarm method
    """

    del user_data
    main_loop.set_alarm_in(0.5, _do_nothing)

class Monwin(urwid.MainLoop):
    """Main class for the window.

    Handles all display functions, command entry, monitors the scanner for input.
    """

    class CmdLine(urwid.WidgetWrap):
        """The command line input area.

        Posts any command entered to the command queue when Enter is pressed.

        Args:
            cmd_queue (Queue): the queue into which to put the entered comands.
        """

        def __init__(self, cmd_queue):
            """Initialize the CmdLine class.
            """

            self.__logger = logging.getLogger(__name__)
            self.cmd_queue = cmd_queue
            super().__init__(Edit(caption=('green', "Cmd> "), wrap='clip'))

        def keypress(self, size, key):
            """Watch for the Enter key and post commands to the command queue.

            Args:
                size (widget size): See *Widget.render()* for details
                key (str): a single keystrove value

            Returns:
                *None* if the key was handled or *key* otherwise
            """

            keyret = self._w.keypress(size, key)
            if keyret == 'enter':
                cmd = self._w.edit_text
                self.__logger.debug('keypress: Command: "%s"', cmd)
                self._w.set_edit_text('')
                self.cmd_queue(cmd)
                keyret = None

            return keyret

    class ScrollWin(urwid.WidgetWrap):
        """
        Main scrolling windows within the program window.

        These handle auto scrolling and mouse scrolling.

        Args:
            title (str): Optional title string for the window header.
        """

        def __init__(self, title=None):
            """Initialize the ScrollWin.
            """

            self.__logger = logging.getLogger(__name__)
            self.scroller = ListBox(SimpleFocusListWalker([]))
            if title:
                self.frame_title = Columns([('pack', Text('--')),
                                            ('pack', Text(('wintitle', title))),
                                            Divider('-')])
            else:
                self.frame_title = None
            super().__init__(Frame(self.scroller, header=self.frame_title))

        def append(self, wid):
            """Append a line to the indow contents.

            Args:
                wid (str, Widget, or tuple): The line to append to the window contents.
                    May be a plain string, an urwid Widget, or a tuple with an attributed string.
            """

            try:
                focus_now = self.scroller.focus_position
            except IndexError:
                focus_now = -1
            bottom = focus_now == len(self.scroller.body) - 1  # Bottom widget in focus?
            self.scroller.body.append(AttrMap(wid, None,        # pylint: disable=no-member
                                              {'NORM': 'NORMF',
                                               'WARN': 'WARNF',
                                               'ALERT': 'ALERTF',
                                               'default': 'NORMF'}))
            if bottom:
                self.__logger.debug('scrolling')
                self.scroller.set_focus(focus_now + 1, coming_from='above')
            else:
                self.__logger.debug('skipping scrolling')

        def mouse_event(self, size, event, button, col, row, focus):
            """Handle mouse events that happen within the window.

            Args:
                size (widget size): See *Widget.render()* for details

                event (str): Values such as :code:`'mouse press'`

                button (int): 1 through 5 for press events,
                    often 0 for release events (which button was released is often not known)

                col (int): Column of the event, 0 is the left edge of this widget

                row (int): Row of the event, 0 it the top row of this widget

                focus (bool): Set to True if this widget or one of its children is in focus
            """

            focus_dir = None

            if button == 4.0:   # scroll wheel down
                focus_dir = -1
                from_dir = 'below'
                self.__logger.debug('Scroll wheel down')
            elif button == 5.0: # scroll wheel up
                focus_dir = 1
                from_dir = 'above'
                self.__logger.debug('Scroll wheel up')

            if focus_dir is not None:
                handled = True
                try:
                    newpos = self.scroller.focus_position + focus_dir
                    if newpos >= 0 and newpos < len(self.scroller.body):
                        self.scroller.change_focus(size, newpos, coming_from=from_dir)
                        self.__logger.debug('newpos=%d', newpos)
                except IndexError:
                    msg = 'OUCH! size={}, event={}, button={}, col={}, row={}, focus={}, dir={}'.format(size, event, button, col, row, focus, focus_dir)
                    self.__logger.exception(msg)
                    self.append(Text(msg))
            else:
                handled = self._w.mouse_event(size, event, button, col, row, focus)

            return handled

    def show_or_exit(self, key):
        """Responds to unhandled key presses.

        Responds to keys as follows:

        * :code:`'q'` or :code:`'Q'`: Exits the system via :code:`raise urwid.ExitMainLoop()`
        * :code:`'enter'`: Reset focus to the command input area
        * Anything else: Display a message

        Args:
            key (str): The unhandled key value

        Returns:
            True in all cases except when the exception is raised.
        """

        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        elif key == 'enter':
            if self.widget.focus_position != 'footer':  # readjust focus if needed
                self.widget.focus_position = 'footer'
        else:
            self.resp.append(Text(repr(key)))

        return True

    def __init__(self):
        self.__logger = logging.getLogger(__name__)
        self.mdl = Text('[checking...]')
        self.ver = Text('[checking...]')
        self.thread_id = threading.get_ident()
        header = Columns([
            ('weight', 60, Divider('-')),
            ('weight', 30, Padding(AttrMap(self.mdl, 'wintitle'),
                                   min_width=10, align='left')),
            ('weight', 20, Divider('=')),
            ('weight', 30, Padding(AttrMap(self.ver, 'wintitle'),
                                   min_width=10, align='right', width='pack')),
            ('weight', 60, Divider('-'))
            ])

        footer = Monwin.CmdLine(self.dispatch_command)

        self.msg = Monwin.ScrollWin('Messages')
        self.glg = Monwin.ScrollWin('Channel Monitor')
        self.resp = Monwin.ScrollWin('Command Response')
        self.windows = {'msg': self.msg, 'glg': self.glg, 'resp': self.resp}

        body = Pile([
            ('weight', 5, self.msg),
            ('weight', 33, self.glg),
            ('weight', 11, self.resp)
            ])
        frame = Frame(body, header=header, footer=footer, focus_part='footer')
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
        (screen_cols, screen_rows) = self.screen.get_cols_rows()
        glg_rows = screen_rows - (2 + 5 + 11)

        self.msg.append(Text(('NORM',
            'Screen has {:d} rows and {:d} columns'.format(screen_rows, screen_cols))))
        self.msg.append(Text(('NORM', 'glg has {:d} rows'.format(glg_rows))))

    def _alarm_putline(self, main_loop, user_data):
        """Called via set_alarm_in when putline is called outside the main thread

        Receives the arguments from set_alarm and re-calls putline on the
        main thread.

        Args:
            main_loop (urwid.main_loop): Standard args for set_alarm method
            user_data (object): Standard args for set_alarm method
        """

        del main_loop    # unused
        (window, message, *color) = user_data

        try:
            color = color[0]
        except IndexError:
            color = 'NORM'

        self.putline(window, message, color)

    def putline(self, window, message, color='NORM'):
        """Scroll the window and write the message on the bottom line.

        Positional parameters:
        window -- The name of the window("msg", "glg", "resp")
        message -- The message (a string, a tuple[attributed string(s)] or a Widget)

        Keyword parameters:
        color -- The color of the message("NORM", "ALERT", "WARN", "GREEN")
        """

        if self.thread_id == threading.get_ident():
            if not window in ('msg', 'glg', 'resp'):
                window = 'msg'

            self.__logger.debug('window=%s, message=%s, color=%s', window, repr(message), color)
            if isinstance(message, urwid.Widget): # a Widget?
                wid = message
            elif isinstance(message, str):        # a bare string gets color
                wid = Text((color, message))
            else:
                wid = Text(message)               # probably a tuple

            self.windows[window].append(wid)

        else:
            self.__logger.debug('redirect: "%s", "%s", "%s"', window, message, color)
            self.set_alarm_in(0.0, self._alarm_putline, user_data=(window, message, color))

    def alert(self, message):
        """Display an ALERT message in the message window.

        Args:
            message (str): Alert message to display.

        .. TODO:: Sound an alarm??
        """

        self.message(message, color="ALERT")

    def message(self, message, color="WARN"):
        """Put a message in the message window

        Args:
            message (str): The message
            color (str): The color of the message("NORM", "ALERT", "WARN", "GREEN")
        """

        self.putline("msg", message, color)

    def _alarm_set_widget_text(self, main_loop, user_data):
        """set_alarm target methos for set_widget_text.

        Receives the arguments from set_alarm and re-calls set_widget_text on the
        main thread.

        Args:
            main_loop (urwid.main_loop): Standard args for set_alarm method
            user_data (object): Standard args for set_alarm method
        """

        del main_loop    # unused
        (wid, txt) = user_data
        self.set_widget_text(wid, txt)

    def set_widget_text(self, wid, txt):
        """Performs set_widget_text for the supplied widget.

        Will schedule the set_widget_text on the main thread if called from a different thread.

        Args:
            wid (urwid.Widget): The target Widget
            txt (str): The text to apply to the Widget
        """

        if self.thread_id == threading.get_ident():
            self.__logger.debug(txt)
            wid.set_widget_text(txt)
        else:
            self.set_alarm_in(0.0, self._alarm_set_widget_text, (wid, txt))

    def do_it(self, callback, data=None, delay_time=0.0):
        """Called by other threads, schedules a method call for execution by main_loop

        Args:
            callback (function): Function or methos to schedule
            data (object): Passed to function by set_alarm
            delay_time (float): Delay time in seconds
        """

        self.set_alarm_in(delay_time, callback, data)

    def do_quit(self, main_loop=None, user_data=None):
        """Raise urwid.ExitMainLoop to stop the system

        Checks the current thread ID and reschedules itself on the main thread if necessary.

        Args:
            main_loop (urwid.MailLoop): Not used
            user_data (object): Not used
        """

        del main_loop, user_data # unused
        self.__logger.warning('QUIT requested')
        if self.thread_id == threading.get_ident():
            raise urwid.ExitMainLoop
        else:
            self.set_alarm_in(0.1, self.do_quit)

    def dispatch_command(self, inputstr):
        """Dummy routine. Must be overridden by the subclass.

        Posts an ALERT to the window.
        """

        del inputstr    # unused
        self.alert("IMPLEMENTATION ERROR. Commands not available.")



# Run simulation for testing
if __name__ == '__main__':
    def main():
        """Testing routine
        """

        def loop_test():
            """A simple thread test
            """

            dologger = logging.getLogger(__name__)
            dologger.info('starting')
            loop_test_time = "I'm not done yet!"
            dologger.debug(loop_test_time)
            monwin.putline('msg', loop_test_time, 'WARN')
            now_start = time.time()
            time.sleep(5)
            now_stop = time.time()
            loop_test_time = "loop test took {:5.3f} seconds".format(now_stop - now_start)
            monwin.alert(loop_test_time)
            monwin.set_widget_text(monwin.ver, 'Ver 2.3.4')

            dologger.info(loop_test_time)

        fmt = '%(asctime)s -%(levelname)s- *%(threadName)s* %%%(funcName)s%% %(message)s'
        logging.basicConfig(filename='Monwin.log', filemode='w', level=logging.DEBUG, format=fmt)
        logger = logging.getLogger(__name__)
        now1 = time.time()

        monwin = Monwin()

        loop_test = threading.Thread(target=loop_test, name='LoopTest')
        _do_nothing(monwin, None)
        loop_test.start()
        monwin.run()

        logger.info("That took %5.3f seconds", time.time() - now1)
        logging.shutdown()

    main()
