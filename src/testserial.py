#!/usr/bin/env python3

# Test some ideas for the scanner

from scanner import Scanner
from time import sleep

s = Scanner()

print("We have our scanner:", s)

print("Writing a simple GLG command")
s.writeline('GLG')
print("Retrieving the rsponse")
print(s.readline())

print("Now send a command with decoded response")

print(s.command("GLG"))

# Run a loop for a minute (more or less)
print("Looping for 5 receptions. Use ^C if it's taking too long.")
t = 0
try:
	while t < 5:
		r = s.command("GLG")
		if r.val['NAME1']:
			print("Sys={NAME1}, Group={NAME2}, Chan={NAME3}, Sql={SQL}, Mut={MUT}, Time={time}".format(time=r.time, **r.val))
			t += 1
		sleep(1)
except KeyboardInterrupt:
	print("\nOK, quitting the loop")
finally:
	print("Loop done...")
