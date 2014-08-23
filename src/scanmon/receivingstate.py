'''State -- State control
'''

"""State constants"""

(_idle, _receiving, _timeout) = ('IDLE', 'RECEIVING', 'TIMEOUT')

class ReceivingState:

	(IDLE,  RECEIVING,  TIMEOUT) = (_idle , _receiving , _timeout)

	@property
	def isidle(self):
		return self.state == State.IDLE

	@property
	def isreceiving(self):
		return self.state == State.RECEIVING

	@property
	def istimeout(self):
		return self.state == State.TIMEOUT

	@property
	def state(self):
		'''Reception state'''
		return self._state

	_states = frozenset((IDLE, RECEIVING, TIMEOUT,))

	@state.setter
	def state(self, newstate):
		if newstate in State._states:
			self._state = newstate
		else:
			raise ValueError('Invalid State: %', newstate)

	def __init__(self, initialstate = None):
		self._state = initialstate if not initialstate is None else State.IDLE

if __name__ == '__main__':
	'''Testing code'''

	mystate = State()
	print("Initial state is", mystate.state)
	for s in (State.IDLE, State.RECEIVING, State.TIMEOUT):
		print("Setting to:", s)
		mystate.state = s
		print("Current state is", mystate.state)
