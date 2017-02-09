# README

Scripts and associated files for rendering from Blender files on CSE remote servers (Blender version: 2.78a)

## Server Farm Client Add-On:
  * Features:
      * Clean UI for sending frames to servers and viewing them within Blender
      * Mid-render previews/status updates available with 'SHIFT + P'
      * Abort render ('ESC')
      * NOTE: Files are auto-packed into the .blend file with each render process
  * Required local python modules:
      * bpy, subprocess, telnetlib, sys, io os, numpy, time, json, math, fnmatch, pillow
  * Required packages:
      * Local: rsync, curl
      * Host Server: rsync
      * Client Servers: blender
  * Future improvements:
      * Remove restriction from using spaces in project name
      * Get all keyboard shortcuts worked out
      * Handle known errors
          * Detect when SSH keys have not been set up
          * Detect when required packages have not been installed on servers (see 'which' command)
          * Detect if you've run out of disk space
      * Optimize default render settings
      * Don't pack files into the blend file?
      * 'blender_task' module
          * Integrate max server load functionality to set cap on how many frames will be rendered
          * If servers available, re-render current jobs until one is finished, then kill the rest
          * Re-render failed frames automatically
          * Handle known errors (see 'Handle known errors' list above)
          * Send tiles to the various servers based on computer speed
