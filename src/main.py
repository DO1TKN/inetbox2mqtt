# MIT License
#
# Copyright (c) 2022  Dr. Magnus Christ (mc0110)
#
# This is part of the wifimanager package
# 
import time
import lib.connect as connect

#sleep to give some boards time to initialize, for example Rpi Pico W
time.sleep(3)

import lib.connect as connect
w=connect.Wifi()

if w.run_mode():
    print("Normal mode activated - for chance to OS-mode type in terminal:")
    print(">>>import os")
    print(">>>os.remove('run_mode.dat'")    
    import truma_serv
else:
    print("OS mode activated")
    import web_os_run
    
