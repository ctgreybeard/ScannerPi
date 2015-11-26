"""Holds the state of the receiving stream.

`Source <src/scanmon.receivingstate.html>`_
"""

import logging

class ReceivingState:
    """Holds the state of the receiving stream.

    Args:
        initialstate (str): Initial state of reception. Optional, defaults to IDLE.
    """

    (IDLE, RECEIVING, TIMEOUT) = ('IDLE', 'RECEIVING', 'TIMEOUT')

    __states = frozenset((IDLE, RECEIVING, TIMEOUT,))

    @property
    def is_idle(self):
        """Receiving state is idle.
        """
        return self.state == ReceivingState.IDLE

    @property
    def is_receiving(self):
        """Receiving state is receiving.
        """
        return self.state == ReceivingState.RECEIVING

    @property
    def is_timeout(self):
        """Receiving state is timeout.
        """
        return self.state == ReceivingState.TIMEOUT

    @property
    def state(self):
        """Reception state
        """
        return self.__state

    @state.setter
    def state(self, newstate):
        """Set reception state.
        """
        if newstate in ReceivingState.__states:
            if self.__state != newstate:
                self.__logger.debug("state: %s->%s", self.__state, newstate)
            self.__state = newstate
        else:
            raise ValueError('Invalid Receiving State: %s', newstate)

    def __init__(self, initialstate=None):
        self.__logger = logging.getLogger().getChild(__name__)
        self.__state = '*INIT*'
        self.state = ReceivingState.IDLE if initialstate is None else initialstate

    def __str__(self):
        return self.__state

    def __repr__(self):
        return "{0}({0}.{1})".format(self.__class__.__name__, self.__state)

def _run_tests():
    """Testing code
    """

    # pylint: disable=too-many-branches
    print("--State initialization and setting")
    mystate = ReceivingState()
    print("  Initial state is", mystate.state)

    for state in (ReceivingState.IDLE, ReceivingState.RECEIVING, ReceivingState.TIMEOUT):
        print("  Setting to:", state)
        mystate.state = state
        print("  Current state is", mystate.state)

    mystate = ReceivingState(ReceivingState.TIMEOUT)
    print("  Second initial state is", mystate)

    for state in (ReceivingState.IDLE, ReceivingState.RECEIVING, ReceivingState.TIMEOUT):
        print("  Setting to:", state)
        mystate.state = state
        print("  Current state is", mystate)

    print("--Bad state checking, initialization")
    mystate = None

    try:
        mystate = ReceivingState('Wrong')
    except ValueError:
        print('  Test bad state exception 1 OK')

    if mystate is not None:
        print('**ValueError test 1 failed. State: {}'.format(mystate))
    else:
        print('  ValueError test 1 complete.')

    print("--Bad state checking, setting")
    try:
        mystate = ReceivingState()
        mystate.state = ReceivingState.TIMEOUT
        mystate.state = 'SomethingElse'
    except ValueError:
        print('  Test bad state exception 2 OK')

    newstate = mystate.state
    if newstate != ReceivingState.TIMEOUT or not mystate.is_timeout:
        print('**ValueError test 2 failed. State: {}'.format(newstate))
    else:
        print('  ValueError test 2 complete.')

    print("--State checking pseudo attributes, initialization")
    testers = ((ReceivingState.IDLE, (True, False, False), 'Idle'),
               (ReceivingState.RECEIVING, (False, True, False), 'Receiving'),
               (ReceivingState.TIMEOUT, (False, False, True), 'Timeout'))

    for test in testers:
        mystate = ReceivingState(test[0])
        testr = (mystate.is_idle, mystate.is_receiving, mystate.is_timeout)
        if test[1] == testr:
            print("  {} initial test OK".format(test[2]))
        else:
            print("**{} initial test FAILED: Received: {}, Expected: {}".\
                  format(test[2], testr, test[1]))

    print("--State checking pseudo attributes, setting")
    for test in testers:
        mystate.state = test[0]
        testr = (mystate.is_idle, mystate.is_receiving, mystate.is_timeout)
        if test[1] == testr:
            print("  {} set test OK".format(test[2]))
        else:
            print("**{} set test FAILED: Received: {}, Expected: {}".\
                  format(test[2], testr, test[1]))

if __name__ == '__main__':
    try:
        print("Running validation tests ...")
        _run_tests()
        print("Tests complete ...")
    except Exception:
        print("Uncaught exception during tests.")
        raise
