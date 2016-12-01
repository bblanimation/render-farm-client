# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.78a)

## Server Farm Client Add-On:
  * Features:
      * Clean UI for sending frames to servers and viewing them within Blender

  * Future improvements:
      * don't rely on scripts that run on python 2 (averageFrames)
      * flush self.report() statements so that they appear when they are called from a modal context
      * Comment code well
      * Detect when SSH keys have not been set up
      * Detect if you've run out of disk space
      * Don't pack files into the blend file
  * For documentation
      * Let them know that all external files are packed into the .blender
  * Required python modules:
      * bpy, subprocess, telnetlib, sys, os, numpy, time, json, math
  * Required local packages:
      * rsync, curl

## Server-side improvements to be made:
* Give user some sort of status for the render (e.g. 5% done)
* Optimize default render settings
* Re-render failed frames automatically
* Detect when SSH keys have not been set up
* Detect when necessary packages have not been installed on remote servers (rsync, blender)
* Detect if you've run out of disk space
* Speed up ssh/rsync editing the daemon to remove unnecessary speed bumps, and other optimizations
