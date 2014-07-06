#!/usr/bin/env python3

from scanner.formatter import Response

GLG = 'GLG,0463.0000,FM,0,0,Public Safety,EMS MED Channels,Med 1,1,0,NONE,NONE,NONE'
GLG2 = 'GLG,,,,,,,,,,,,'
STS = 'STS,011000,        ����    ,,Fairfield County,,FAPERN VHF      ,, 154.1000 C151.4,,S0:12-*5*7*9-   ,,GRP----5-----   ,,1,0,0,0,0,0,5,GREEN,1'

for t in (GLG, GLG2, STS):
	v = Response(t)
	print("{} dict: {}".format(t[:3], v.__dict__))
	print('{} str={}'.format(t[:3], v.__str__()))
	print('---')
