'''State -- State control
'''

"""State constants"""

(_idle, _receiving, _timeout) = ('IDLE', 'RECEIVING', 'TIMEOUT')

import logging

class ReceivingState:

	(IDLE,  RECEIVING,  TIMEOUT) = (_idle , _receiving , _timeout)

	@property
	def isIdle(self):
		return self.state == ReceivingState.IDLE

	@property
	def isReceiving(self):
		return self.state == ReceivingState.RECEIVING

	@property
	def isTimeout(self):
		return self.state == ReceivingState.TIMEOUT

	@property
	def state(self):
		'''Reception state'''
		return self.__state

	__states = frozenset((IDLE, RECEIVING, TIMEOUT,))

	@state.setter
	def state(self, newstate):
		if newstate in ReceivingState.__states:
			if self.__state != newstate:
				self.__logger.debug("state: %s->%s", self.__state, newstate)
			self.__state = newstate
		else:
			raise ValueError('Invalid Receiving State: %s', newstate)

	def __init__(self, initialstate = None):
		self.__logger = logging.getLogger().getChild(__name__)
		self.__state = '*INIT*'
		self.state = initialstate if not initialstate is None else ReceivingState.IDLE

	def __str__(self):
		return self.__state

	def __repr__(self):
		return "{0}({0}.{1})".format(self.__class__.__name__, self.__state)

def _runTests():
	'''Testing code'''

	print("--State initialization and setting")
	mystate = ReceivingState()
	print("  Initial state is", mystate.state)
	for s in (ReceivingState.IDLE, ReceivingState.RECEIVING, ReceivingState.TIMEOUT):
		print("  Setting to:", s)
		mystate.state = s
		print("  Current state is", mystate.state)
	mystate = ReceivingState(ReceivingState.TIMEOUT)
	print("  Second initial state is", mystate)
	for s in (ReceivingState.IDLE, ReceivingState.RECEIVING, ReceivingState.TIMEOUT):
		print("  Setting to:", s)
		mystate.state = s
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
	if newstate != ReceivingState.TIMEOUT or not mystate.isTimeout:
		print('**ValueError test 2 failed. State: {}'.format(newstate))
	else:
		print('  ValueError test 2 complete.')

	print("--State checking pseudo attributes, initialization")
	testers = ((ReceivingState.IDLE, (True, False, False), 'Idle'), 
		(ReceivingState.RECEIVING, (False, True, False), 'Receiving'), 
		(ReceivingState.TIMEOUT, (False, False, True), 'Timeout')) 

	for test in testers:
		mystate = ReceivingState(test[0])
		tr = (mystate.isIdle, mystate.isReceiving, mystate.isTimeout)
		if test[1] == tr:
			print("  {} initial test OK".format(test[2]))
		else:
			print("**{} initial test FAILED: Received: {}, Expected: {}".format(test[2], tr, test[1]))

	print("--State checking pseudo attributes, setting")
	for test in testers:
		mystate.state = test[0]
		tr = (mystate.isIdle, mystate.isReceiving, mystate.isTimeout)
		if test[1] == tr:
			print("  {} set test OK".format(test[2]))
		else:
			print("**{} set test FAILED: Received: {}, Expected: {}".format(test[2], tr, test[1]))

if __name__ == '__main__':
	try:
		print("Running validation tests ...")
		_runTests()
		print("Tests complete ...")
	except Exception as e:
		print("Uncaught exception during tests.")
		raise
