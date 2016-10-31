# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.77)

## FEATURES:

* $ python render.py [options]
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
        * -r  // when opening a new file, the script will search recursively through ~/filmmaking/ for all files matching '*.blend'


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


* $ python fetchFromServers.py
    * Fetches render files directly from the host servers (bypassing asahel)
    * This is useful if render failed, but some render files were completed and stored in the hosts' /tmp/ folders
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
* Add user input for samples and size %
* Notify user when an individual file has been rendered
* Sync files one by one (in case of host failure)
* Fix unknown host failures bugs found when running overnight
* Optimize default render settings
* Re-render failed frames automatically
* Quit blender if process aborted
