# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.77)

## FEATURES:

* "Server Farm Client" Add-On for Blender
    * Features:
        * Clean UI for sending frames to servers and viewing them within Blender

    * Future improvements:
        * write instructions in './servers/hostServer.txt' and './servers/remoteServers.txt'
        * don't rely on scripts that run on python 2 (averageFrames)
        * go through and remove any part of the code that is customized to my computer
        * implement killAll Blender process into plugin (currently called via subprocess)
        * flush self.report() statements so that they appear when they are called
        * complete listed TODOs
        * refactor
    * Imports:
        * bpy, subprocess, telnetlib, sys, os, numpy, time, json, math
        * /servers/*

* $ python render.py [options]
    * Code is highly outdated.
    * Features:
        * interactive menu
        * sendToRenderFarm
        * getRenderFilesFromServer
    * Future improvements:
        * use ssh redirect so that I can access asahel remotely
        * open last used file to main menu automatically
        * notify when a frame has been rendered
        * integrate 'sendSpecificFiles.py', 'iterateThruAvailServers.py', 'fetchFromServers.py', and 'killBlenderOnAvailServers.py' into interactive menu.
        * improve '-v' settings. Right now, random things print in verbose. This could be much more helpful if carfully examined.
        * add user input for samples and size %
        * maybe refactor some of the functions in this code into external scripts?
        * refactor directory defaults to an external 'txt' document.
        * implement menu system into blender with a plugin
        * implement single-frame distributed processing
            * multiple renders at low (seeded) sampling averaged out.
            * render many portions of the whole frame at the full sample size.
    * Imports:
        * subprocess, sys
    * Options:
        * -v  // verbose (this option isn't too helpful yet...)
        * -t  // performs render in testing mode; no render processes will be queued
        * -r  // when opening a new file, the script will search recursively through ~/filmmaking/ for all files matching '<wildcard>.blend'


* $ python sendSpecificFiles [options] {framesList}
    * Takes argument {framesList}: list of frames to render
        * accepts ranges (e.g. [10-20]
        * examples: [5,7,25,33,39] _or_ [1-10] _or_ [1-5,10-20,35]
    * Future improvements: don't hard-code project file (allow for user input)
    * Imports:
        * CSE_HOSTS.txt
        * subprocess, sys, telnetlib, ast
    * Options:
        * -t  // performs render in testing mode; no render processes will be queued


* $ python killBlenderOnAvailServers.py
    * KILLALL blender processes on  _available hosts_ in CSE\_HOSTS.txt.
    * Good for clearing old, unwanted blender processes that are slowing down the CSE hosts.
    * __DANGER__: This will kill ALL blender processes on ALL available hosts. Use with caution.
    * Imports:
        * CSE_HOSTS.txt
        * subprocess, sys, telnetlib, ast


* $ python iterateThruAvailServers.py
    * Opens terminal for each available host one by one, in case I need to run commands or check something on all servers.
    * Imports:
        * CSE_HOSTS.txt
        * subprocess, sys, telnetlib, ast



## Server-side improvements to be made:
* Add elapsed time to 'render completed successfully!' message
* Give user some sort of status for the render (e.g. 5% done)
* Notify user when an individual file has been rendered
* Optimize default render settings
* Re-render failed frames automatically
* Currently doesn’t read blender\_p.py
* fix this line: rsync pull: mkdir -p /tmp/cgearhar/DeleteMe *ADD /render/ HERE* ;rsync -atu --remove-source-files cgearhar@cse10309:/tmp/cgearhar/DeleteMe/render/DeleteMe* /tmp/cgearhar/DeleteMe/.
