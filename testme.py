#!/usr/bin/python
# -*- coding: utf-8 -*-

# Ensure that the script is not run with python 2.x
import sys
if (sys.version_info.major < 3)
    exit('shnake library is not compatible with python < 3')

# Make sure the script is not imported
try: from __main__ import __file__
except: exit('./testme.py cannot be imported !')

# import local shnake dependencies that are not installed on the system
import dependencies


#### UNIT-TEST ####
import shnake
cmdrun = shnake.Parser()

if len(sys.argv) > 1:
    file = open('/tmp/parse.test')
else:
    file = None

result = cmdrun(file)


### Start shell interface
#import ui.interface
#interface = ui.interface.Cmd()
#interface.interpret("foo\\\nbar")
#
#interface.cmdloop()
