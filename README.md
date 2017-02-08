# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.78a)

## Server Farm Client Add-On:
  * Features:
      * Clean UI for sending frames to servers and viewing them within Blender

  * Future improvements:
      * Detect when SSH keys have not been set up
      * Detect if you've run out of disk space
      * Don't pack files into the blend file
  * For documentation
      * Let them know that all external files are packed into the .blend
  * Required python modules:
      * bpy, subprocess, telnetlib, sys, io os, numpy, time, json, math, fnmatch
  * Required local packages:
      * rsync, curl
  * Required packages on host server:
      * rsync, numpy, pillow
  * Required packages on client servers:
      * blender

## Server-side improvements to be made:
* Optimize default render settings
* Re-render failed frames automatically
* Detect when SSH keys have not been set up
* Detect when necessary packages have not been installed on remote servers (rsync, blender)
* Detect if you've run out of disk space
* Send tiles to the various servers based on computer speed
