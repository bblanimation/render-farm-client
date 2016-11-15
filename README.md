# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.78a)

## Server Farm Client Add-On:
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
      * Detect when SSH keys have not been set up
      * Detect if you've run out of disk space
  * For documentation
      * Let them know that all external files are packed into the .blender
  * Imports:
      * bpy, subprocess, telnetlib, sys, os, numpy, time, json, math
      * ./servers/remoteServers.txt


## Server-side improvements to be made:
* Add elapsed time to 'render completed successfully!' message
* Give user some sort of status for the render (e.g. 5% done)
* Notify user when an individual file has been rendered
* Optimize default render settings
* Re-render failed frames automatically
* fix this line: rsync pull: mkdir -p /tmp/cgearhar/DeleteMe *ADD /render/ HERE* ;rsync -atu --remove-source-files cgearhar@cse10309:/tmp/cgearhar/DeleteMe/render/DeleteMe* /tmp/cgearhar/DeleteMe/.
* Detect when SSH keys have not been set up
* Detect when necessary packages have not been installed on remote servers
* Detect if you've run out of disk space
