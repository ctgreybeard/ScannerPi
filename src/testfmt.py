# -*- coding: utf-8 -*-
"""A test program for scanner.formatter

Some example response strings are run through the formatter and the results printed.

"""

if __name__ == '__main__':
    from scanner.formatter import Response

    GLG = 'GLG,0463.0000,FM,0,0,Public Safety,EMS MED Channels,Med 1,1,0,NONE,NONE,NONE'
    GLG2 = 'GLG,,,,,,,,,,,,'
    STS = 'STS,011000,        ????    ,,Fairfield County,,FAPERN VHF      ,, 154.1000 C151.4,,S0:12-*5*7*9-   ,,GRP----5-----   ,,1,0,0,0,0,0,5,GREEN,1'
    TST = 'TST,ONE,TWO,THREE,FOUR,FIVE'
    UNK = 'UNK,Some ,,,Unknown,   Response, that,we,can,handle,,OK?,,'

    for t in (GLG, GLG2, STS, TST, UNK):
        v = Response(t)
        cmd = v.CMD
        print("{} dict: {}".format(cmd, v.__dict__))
        print('{} str={}'.format(cmd, v.__str__()))
        print('{} NONEXIST={}'.format(cmd, v.NONEXIST))
        try:
            print('{} nonexist={}'.format(cmd, v.nonexist))
        except AttributeError:
            print("{} nonexist doesn't exist (as it should be)".format(cmd))
        print("---")
