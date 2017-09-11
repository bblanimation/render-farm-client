# README

Blender add-on for distributing render jobs to remote servers (Blender version: 2.78b)

## Render Farm Client Add-On:
  * Features:
      * Clean UI for sending frames to servers and viewing them within Blender
      * Mid-render previews/status updates available with 'SHIFT + P'
      * Abort render with 'ESC'
      * Full support for Cycles Render Engine (support for Blender Internal/Game 'animation' renders only - current frame render jobs processed locally)
      * NOTE: Files are auto-packed into the .blend file with each render process
  * System Requirements:
      * Operating System (local and remote):
          * Linux
          * Mac OS X
      * Required packages:
          * Local: rsync
          * Host Server: rsync, python
          * Client Servers: blender
  * Future improvements:
      * Handle known errors
          * Detect when required packages have not been installed on servers (see 'which' command)
          * Detect if you've run out of disk space
      * Don't pack files into the blend file?
      * 'blender_task' module
          * Integrate max server load functionality to set cap on how many frames will be rendered
          * Re-render failed frames automatically
          * Handle known errors (ssh keys, necessary packages not installed, run out of disk space, etc.)
          * Send tiles to the various servers based on computer speed
