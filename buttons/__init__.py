"""
Copyright (C) 2017 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# system imports
import bpy
import io
import json
import os
import subprocess
import time

from bpy.types import Operator
from bpy.props import *
from ..functions import *
from ..functions.averageFrames import *
from ..functions.jobIsValid import *

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers through host server"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.refresh_num_available_servers"                           # unique identifier for buttons and menu items to reference.
    bl_label = "Refresh Available Servers"                                      # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def checkNumAvailServers(self):
        scn = bpy.context.scene
        command = "ssh -T -oStrictHostKeyChecking=no -x {login} 'python {remotePath}blender_task -H --connection_timeout {timeout} --hosts_file {remotePath}servers.txt'".format(login=bpy.props.serverPrefs["login"], remotePath=bpy.props.serverPrefs["path"], timeout=scn.timeout)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        return process

    def updateAvailServerInfo(self):
        scn = bpy.context.scene

        line1 = self.process.stdout.readline().decode("ASCII").replace("\\n", "")
        line2 = self.process.stdout.readline().decode("ASCII").replace("\\n", "")
        available = json.loads(line1.replace("'", "\""))
        offline = json.loads(line2.replace("'", "\""))

        scn.availableServers = len(available)
        scn.offlineServers = len(offline)
        for a in bpy.context.screen.areas:
            a.tag_redraw()

    def modal(self, context, event):
        if event.type in {"ESC"}:
            self.report({"INFO"}, "Refresh process cancelled")
            self.cancel(context)
            return{"CANCELLED"}

        if event.type == "TIMER":
            self.process.poll()

            # if python not found on host server
            if self.process.returncode == 127 and self.state == 2:
                self.report({"ERROR"}, "python not installed on host server")
                self.cancel(context)
                return{"CANCELLED"}

            # if process finished and unknown error thrown
            if self.process.returncode != 0 and self.process.returncode != None:
                handleError(self, "Process {curState}".format(curState=str(self.state-1)))
                self.cancel(context)
                return{"CANCELLED"}

            # if process finished and no errors
            if self.process.returncode != None:
                # print("Process {curState} finished! (return code: {returnCode})".format(curState=str(self.state-1), returnCode=str(self.process.returncode)))

                # check number of available servers via host server
                if self.state == 1:
                    bpy.props.needsUpdating = False
                    self.state += 1
                    self.process = self.checkNumAvailServers()
                    return{"PASS_THROUGH"}

                elif self.state == 2:
                    self.updateAvailServerInfo()
                    scn = context.scene
                    self.report({"INFO"}, "Refresh process completed ({num} servers available)".format(num=str(scn.availableServers)))
                    return{"FINISHED"}
                else:
                    self.report({"ERROR"}, "ERROR: Current state not recognized.")
                    return{"FINISHED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        print("\nRunning 'checkNumAvailServers' function...")
        scn = context.scene

        # start initial process
        self.state = 1 # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastServerGroup != scn.serverGroups:
            bpy.props.lastServerGroup = scn.serverGroups
            updateStatus = updateServerPrefs()
            if not updateStatus["valid"]:
                self.report({"ERROR"}, updateStatus["errorMessage"])
                return{"CANCELLED"}
            self.process = copyFiles()
            bpy.props.lastRemotePath = bpy.props.serverPrefs["path"]
        else:
            self.process = self.checkNumAvailServers()
            self.state += 1

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        self.report({"INFO"}, "Refreshing available servers...")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class sendFrame(Operator):
    """Render current frame on remote servers"""                                # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.render_frame_on_servers"                                 # unique identifier for buttons and menu items to reference.
    bl_label = "Render Current Frame"                                           # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def modal(self, context, event):
        scn = context.scene

        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "PRESS":
            self.shift = True
        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "RELEASE":
            self.shift = False

        if event.type in {"ESC"} and event.value == "PRESS":
            if self.state[0] == 3:
                self.renderCancelled = True
                self.processes[0].kill()
                setRenderStatus("image", "Finishing...")
                self.report({"INFO"}, "Render process cancelled. Fetching frames...")
            else:
                self.report({"INFO"}, "Render process cancelled")
                setRenderStatus("image", "Cancelled")
                self.cancel(context)
                return{"CANCELLED"}

        elif event.type in {"P"} and self.shift and not self.processes[1]:
            if self.state[0] == 3:
                self.report({"INFO"}, "Preparing render preview...")
                self.processes[1] = getFrames(self.projectName, True)
                self.state[1] = 4
            elif self.state[0] < 3:
                self.report({"WARNING"}, "Files are still transferring - try again in a moment")


        if event.type == "TIMER":
            numIters = 1
            if self.processes[1]:
                numIters += 1
            for i in range(numIters):
                self.processes[i].poll()

                if self.processes[i].returncode != None:
                    # handle rsync error of no output files found on server
                    if self.state[i] in [4, 5] and self.processes[i].returncode == 23:
                        if i == 1 and not self.previewed:
                            self.report({"WARNING"}, "No render files found - try again in a moment")
                            self.processes[1] = False
                            self.state[1] = -1
                            break
                        elif self.renderCancelled and not self.previewed:
                            self.report({"INFO"}, "Process cancelled - No output images found on host server")
                            setRenderStatus("image", "Cancelled")
                            self.cancel(context)
                            return{"CANCELLED"}
                        elif not self.previewed:
                            self.report({"INFO"}, "No render files found on host server")
                            return{"FINISHED"}
                        else:
                            pass
                    # handle python not found on host error
                    elif self.processes[i].returncode == 127 and self.state[i] == 3:
                        self.report({"ERROR"}, "python and/or rsync not installed on host server")
                        setRenderStatus("image", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}
                    # handle unidentified errors
                    elif self.processes[i].returncode > 1:
                        setRenderStatus("image", "ERROR")

                        # define self.errorSource string
                        if not self.state[i] == 3:
                            self.errorSource = "Processes[{i}] at state {state}".format(i=i, state=str(self.state[i]))
                        else:
                            self.errorSource = "blender_task"

                        handleError(self, self.errorSource, i)
                        setRenderStatus("image", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}

                    # handle and report errors for 'blender_task' process
                    elif self.processes[i].returncode == 1 and self.state[i] == 3:
                        handleBTError(self, i)

                    # if no errors, print process finished!
                    # print("Process {curState} finished! (return code: {returnCode})".format(curState=str(self.state[i]-1), returnCode=str(self.processes[i].returncode)))

                    # copy files to host server
                    if self.state[i] == 1:
                        self.processes[i] = copyFiles()
                        self.state[i] += 1
                        return{"PASS_THROUGH"}

                    # start render process at current frame
                    elif self.state[i] == 2:
                        bpy.props.needsUpdating = False
                        jobsPerFrame = scn.maxSamples // self.sampleSize
                        self.processes[i] = renderFrames(str([bpy.props.imFrame]), self.projectName, jobsPerFrame)
                        self.state[i] += 1
                        setRenderStatus("image", "Rendering...")
                        return{"PASS_THROUGH"}

                    # get rendered frames from remote servers and archive old render files
                    elif self.state[i] == 3:
                        if self.processes[1] and self.processes[1].returncode == None:
                            self.processes[1].kill()
                        self.state[i] += 1
                        self.processes[0] = getFrames(self.projectName, True)
                        if not self.renderCancelled:
                            setRenderStatus("image", "Finishing...")
                        return{"PASS_THROUGH"}

                    # average the rendered frames if there are new frames to average
                    elif self.state[i] == 4:
                        # only average if there are new frames to average
                        numRenderedFiles = getNumRenderedFiles("image", [bpy.props.imFrame], None)
                        if numRenderedFiles > 0:
                            averaged = True
                            aveName = averageFrames(self, bpy.props.nameImOutputFiles)
                            if aveName != None:
                                bpy.props.nameAveragedImage = aveName
                            else:
                                averaged = False
                        else:
                            averaged = False
                        # calculate number of samples represented in averaged image
                        self.numSamples = self.sampleSize * self.avDict["numFrames"]
                        if i == 0:
                            setRenderStatus("image", "Complete!")
                            if bpy.data.images.find(bpy.props.nameAveragedImage) >= 0:
                                # open rendered image in any open 'IMAGE_EDITOR' windows
                                for area in context.screen.areas:
                                    if area.type == "IMAGE_EDITOR":
                                        area.spaces.active.image = bpy.data.images[bpy.props.nameAveragedImage]
                                        break
                            self.report({"INFO"}, "Render completed at {num} samples! View the rendered image in your UV/Image_Editor".format(num=str(self.numSamples)))
                        else:
                            if bpy.data.images.find(bpy.props.nameAveragedImage) >= 0:
                                # open preview image in UV/Image_Editor
                                changeContext(context, "IMAGE_EDITOR")
                                for area in context.screen.areas:
                                    if area.type == "IMAGE_EDITOR":
                                        area.spaces.active.image = bpy.data.images[bpy.props.nameAveragedImage]
                                        self.previewed = True
                                        break
                            self.processes[1] = False
                            previewString = "Render preview loaded ({num} samples)".format(num=str(self.numSamples))
                            self.report({"INFO"}, previewString)
                        appendViewable("image")
                        removeViewable("animation")
                        if i == 0:
                            if self.renderCancelled:
                                setRenderStatus("image", "Cancelled")
                                self.cancel(context)
                                return{"CANCELLED"}
                            else:
                                return{"FINISHED"}
                    else:
                        self.report({"ERROR"}, "ERROR: Current state not recognized.")
                        setRenderStatus("image", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath).replace(" ", "_")
        scn = context.scene

        if scn.render.engine != "CYCLES":
            self.report({"INFO"}, "Rendering on local machine (switch to cycles to render current frame on remote servers).")
            context.area.type = "IMAGE_EDITOR"
            bpy.ops.render.render(use_viewport=True)
            context.area.spaces.active.image = bpy.data.images["Render Result"]
            return{"FINISHED"}

        # for testing purposes only (saves unsaved file as 'unsaved_file.blend')
        if self.projectName == "":
            self.projectName = "unsaved_file"
            bpy.ops.wm.save_mainfile(filepath="{tempLocalDir}{projectName}.blend".format(tempLocalDir=scn.tempLocalDir, projectName=self.projectName))

        # ensure no other render processes are running
        if getRenderStatus("image") in getRunningStatuses() or getRenderStatus("animation") in getRunningStatuses():
            self.report({"WARNING"}, "Render in progress...")
            return{"CANCELLED"}
        elif scn.availableServers == 0:
            self.report({"WARNING"}, "No servers available. Try refreshing.")
            return{"CANCELLED"}

        # ensure the job won't break the script
        if not jobIsValid("image", self):
            return{"CANCELLED"}

        print("\nRunning sendFrame function...")

        # set the file extension for use with 'open image' button
        bpy.props.imExtension = scn.render.file_extension

        # Store current sample size for use in computing render results
        self.sampleSize = scn.samplesPerFrame

        # start initial render process
        self.stdout = None
        self.stderr = None
        self.shift = False
        self.renderCancelled = False
        self.numSuccessFrames = 0
        self.finishedFrames = 0
        self.previewed = False
        self.numSamples = 0
        self.avDict = {"array":False, "numFrames":0}
        self.averageIm = None
        bpy.props.nameImOutputFiles = getNameOutputFiles()
        bpy.props.imFrame = scn.frame_current
        self.state = [1, 0]  # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastServerGroup != scn.serverGroups:
            bpy.props.lastServerGroup = scn.serverGroups
            updateStatus = updateServerPrefs()
            if not updateStatus["valid"]:
                self.report({"ERROR"}, updateStatus["errorMessage"])
                return{"CANCELLED"}
            bpy.props.lastRemotePath = bpy.props.serverPrefs["path"]
        else:
            self.state[0] += 1
        self.processes = [copyProjectFile(self.projectName, scn.compress), False]

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        setRenderStatus("image", "Preparing files...")
        setRenderStatus("animation", "None")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        print("process cancelled")
        cleanupCancelledRender(self, context, bpy.types.Scene.killPython)

class sendAnimation(Operator):
    """Render animation on remote servers"""                                    # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.render_animation_on_servers"                             # unique identifier for buttons and menu items to reference.
    bl_label = "Render Animation"                                               # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def modal(self, context, event):
        scn = context.scene

        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "PRESS":
            self.shift = True
        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "RELEASE":
            self.shift = False

        if event.type in {"ESC"} and event.value == "PRESS":
            if self.state[0] == 3:
                self.renderCancelled = True
                self.processes[0].kill()
                setRenderStatus("animation", "Finishing...")
                self.report({"INFO"}, "Render process cancelled. Fetching frames...")
            else:
                self.report({"INFO"}, "Render process cancelled")
                setRenderStatus("animation", "Cancelled")
                self.cancel(context)
                return{"CANCELLED"}

        elif event.type in {"P"} and self.shift and not self.processes[1]:
            if self.state[0] == 3:
                self.report({"INFO"}, "Checking render status...")
                self.processes[1] = getFrames(self.projectName, not self.statusChecked, self.expandedFrameRange)
                self.state[1] = 4
            elif self.state[0] < 3:
                self.report({"WARNING"}, "Files are still transferring - try again in a moment")

        if event.type == "TIMER":
            numIters = 1
            if self.processes[1]:
                numIters += 1
            for i in range(numIters):
                self.processes[i].poll()

                if self.processes[i].returncode != None:
                    # handle rsync error of no output files found on server
                    if self.state[i] == 4 and self.processes[i].returncode == 23:
                        if i == 1 and not self.statusChecked:
                            self.report({"WARNING"}, "No render files found - try again in a moment")
                            self.processes[1] = False
                            self.state[1] = -1
                            break
                        elif self.renderCancelled and not self.statusChecked:
                            self.report({"INFO"}, "Process cancelled - No output images found on host server")
                            setRenderStatus("animation", "Cancelled")
                            self.cancel(context)
                            return{"CANCELLED"}
                        elif not self.statusChecked:
                            self.report({"INFO"}, "No render files found on host server")
                            setRenderStatus("animation", "Complete!")
                            return{"FINISHED"}
                        else:
                            pass
                    # handle python not found on host error
                    elif self.processes[i].returncode == 127 and self.state[i] == 3:
                        self.report({"ERROR"}, "python and/or rsync not installed on host server")
                        setRenderStatus("animation", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}
                    # handle unidentified errors
                    elif self.processes[i].returncode > 1:
                        setRenderStatus("animation", "ERROR")

                        # define self.errorSource string
                        if not self.state[i] == 3:
                            self.errorSource = "Processes[{i}] at state {state}".format(i=i, state=str(self.state[i]))
                        else:
                            self.errorSource = "blender_task"

                        handleError(self, self.errorSource, i)
                        setRenderStatus("animation", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}

                    # handle and report errors for 'blender_task' process
                    elif self.processes[i].returncode == 1 and self.state[i] == 3 and self.processes[i].stderr:
                        handleBTError(self, i)

                    # if no errors, print process finished!
                    # print("Process {curState} finished! (return code: {returnCode})".format(curState=str(self.state[i]-1), returnCode=str(self.processes[i].returncode)))

                    # copy files to host server
                    if self.state[i] == 1:
                        self.processes[i] = copyFiles()
                        self.state[i] += 1
                        return{"PASS_THROUGH"}

                    # start render process from the defined start and end frames
                    elif self.state[i] == 2:
                        bpy.props.needsUpdating = False
                        self.processes[i] = renderFrames(str(self.expandedFrameRange), self.projectName)
                        setRenderStatus("animation", "Rendering...")
                        self.state[i] += 1
                        return{"PASS_THROUGH"}

                    # get rendered frames from remote servers and archive old render files
                    elif self.state[i] == 3:
                        if self.processes[1] and self.processes[1].returncode == None:
                            self.processes[1].kill()
                        self.state[0] += 1
                        self.processes[0] = getFrames(self.projectName, not self.statusChecked, self.expandedFrameRange)
                        if not self.renderCancelled:
                            setRenderStatus("animation", "Finishing...")
                        return{"PASS_THROUGH"}

                    elif self.state[i] == 4:
                        numCompleted = getNumRenderedFiles("animation", self.expandedFrameRange, getNameOutputFiles())
                        if numCompleted > 0:
                            viewString = " - View rendered frames in render dump folder"
                        else:
                            viewString = ""
                        self.report({"INFO"}, "Render completed for {numCompleted}/{numSent} frames{viewString}".format(numCompleted=numCompleted, numSent=len(bpy.props.animFrameRange), viewString=viewString))
                        appendViewable("animation")
                        if i == 1:
                            self.processes[1] = False
                            self.statusChecked = True
                        elif self.renderCancelled:
                            setRenderStatus("animation", "Complete!")
                            self.cancel(context)
                            return{"CANCELLED"}
                        else:
                            setRenderStatus("animation", "Complete!")
                            return{"FINISHED"}
                    else:
                        self.report({"ERROR"}, "ERROR: Current state not recognized.")
                        setRenderStatus("animation", "ERROR")
                        self.cancel(context)
                        return{"CANCELLED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath).replace(" ", "_")
        scn = context.scene

        # for testing purposes only (saves unsaved file as 'unsaved_file.blend')
        if self.projectName == "":
            self.projectName = "unsaved_file"
            bpy.ops.wm.save_mainfile(filepath="{tempLocalDir}{projectName}.blend".format(tempLocalDir=scn.tempLocalDir, projectName=self.projectName))

        # ensure no other render processes are running
        if getRenderStatus("image") in getRunningStatuses() or getRenderStatus("animation") in getRunningStatuses():
            self.report({"WARNING"}, "Render in progress...")
            return{"CANCELLED"}
        elif scn.availableServers == 0:
            self.report({"WARNING"}, "No servers available. Try refreshing.")
            return{"CANCELLED"}

        print("\nRunning sendAnimation function...")

        # ensure the job won't break the script
        if not jobIsValid("animation", self):
            return{"CANCELLED"}

        # initializes self.frameRangesDict (returns reports error if frame range is invalid)
        if not setFrameRangesDict(self):
            setRenderStatus("animation", "ERROR")
            return{"CANCELLED"}
        # store expanded results in 'expandedFrameRange'
        self.expandedFrameRange = expandFrames(json.loads(self.frameRangesDict["string"]))
        # restrict length of frame range string to 50000 characters
        if len(str(self.expandedFrameRange)) > 75000:
            self.report({"ERROR"}, "ERROR: Frame range too large (maximum character count after conversion to ints list: 75000)")
            return{"CANCELLED"}

        # set the file extension and frame range for use with 'open animation' button
        bpy.props.animExtension = bpy.context.scene.render.file_extension
        bpy.props.animFrameRange = self.expandedFrameRange

        # start initial render process
        self.stdout = None
        self.stderr = None
        self.shift = False
        self.renderCancelled = False
        self.numFailedFrames = 0
        self.startFrame = context.scene.frame_start
        self.endFrame = context.scene.frame_end
        self.numFrames = str(int(scn.frame_end) - int(scn.frame_start))
        self.statusChecked = False
        self.state = [1, 0] # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastServerGroup != scn.serverGroups:
            bpy.props.lastServerGroup = scn.serverGroups
            updateStatus = updateServerPrefs()
            if not updateStatus["valid"]:
                self.report({"ERROR"}, updateStatus["errorMessage"])
                return{"CANCELLED"}
        else:
            self.state[0] += 1
        self.processes = [copyProjectFile(self.projectName, scn.compress), False]

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        setRenderStatus("animation", "Preparing files...")
        setRenderStatus("image", "None")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        print("process cancelled")
        cleanupCancelledRender(self, context, bpy.types.Scene.killPython)

class openRenderedImageInUI(Operator):
    """Open rendered image"""                                                   # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.open_rendered_image"                                     # unique identifier for buttons and menu items to reference.
    bl_label = "Open Rendered Image"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        if bpy.data.images.find(bpy.props.nameAveragedImage) >= 0:
            # open rendered image in UV/Image_Editor
            changeContext(context, "IMAGE_EDITOR")
            for area in context.screen.areas:
                if area.type == "IMAGE_EDITOR":
                    area.spaces.active.image = bpy.data.images[bpy.props.nameAveragedImage]
        elif bpy.props.nameAveragedImage != "":
            self.report({"ERROR"}, "Image could not be found: '{nameAveragedImage}'".format(nameAveragedImage=bpy.props.nameAveragedImage))
            return{"CANCELLED"}
        else:
            self.report({"WARNING"}, "No rendered images could be found")
            return{"CANCELLED"}

        return{"FINISHED"}

class openRenderedAnimationInUI(Operator):
    """Open rendered animation"""                                               # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.open_rendered_animation"                                 # unique identifier for buttons and menu items to reference.
    bl_label = "Open Rendered Animation"                                        # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.


    def execute(self, context):
        self.frameRangesDict = buildFrameRangesString(context.scene.frameRanges)

        # change contexts
        lastAreaType = changeContext(context, "CLIP_EDITOR")

        # opens first frame of image sequence (blender imports full sequence)
        openedFile = False
        self.renderDumpFolder = getRenderDumpFolder()
        image_sequence_filepath = "{dumpFolder}/".format(dumpFolder=self.renderDumpFolder)
        for frame in bpy.props.animFrameRange:
            try:
                image_filename = "{fileName}_{frame}{extension}".format(fileName=getNameOutputFiles(), frame=str(frame).zfill(4), extension=bpy.props.animExtension)
                bpy.ops.clip.open(directory=image_sequence_filepath, files=[{"name":image_filename}])
                openedFile = image_filename
                openedFrame = frame
                break
            except:
                pass
        if openedFile:
            bpy.ops.clip.reload()
            bpy.data.movieclips[openedFile].frame_start = frame
        else:
            changeContext(context, lastAreaType)
            self.report({"ERROR"}, "Could not open rendered animation. View files in file browser in the following folder: '{renderDumpFolder}'.".format(renderDumpFolder=self.renderDumpFolder))

        return{"FINISHED"}

class editRemoteServersDict(Operator):
    """Edit the remote servers dictionary in a text editor"""                   # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.edit_servers_dict"                                       # unique identifier for buttons and menu items to reference.
    bl_label = "Edit Remote Servers"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        changeContext(context, "TEXT_EDITOR")
        try:
            libraryServersPath = os.path.join(getLibraryPath(), "servers")
            bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "remoteServers.txt"))
            self.report({"INFO"}, "Opened 'remoteServers.txt'")
            bpy.props.needsUpdating = True
        except:
            self.report({"ERROR"}, "ERROR: Could not open 'remoteServers.txt'. If the problem persists, try reinstalling the add-on.")
        return{"FINISHED"}

class listMissingFrames(Operator):
    """List the output files missing from the render dump folder"""             # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.list_frames"                                              # unique identifier for buttons and menu items to reference.
    bl_label = "List Missing Frames"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        scn = context.scene

        # initializes self.frameRangesDict (returns False if frame range invalid)
        if not setFrameRangesDict(self):
            return{"FINISHED"}

        # list all missing files from start frame to end frame in render dump folder
        missingFrames = listMissingFiles(getNameOutputFiles(), self.frameRangesDict["string"])
        if len(missingFrames) > 0:
            self.report({"INFO"}, "Missing frames: {missingFrames}".format(missingFrames=missingFrames))
        else:
            self.report({"INFO"}, "All frames accounted for!")

        return{"FINISHED"}

class setToMissingFrames(Operator):
    """Set frame range to frames missing from the render dump folder"""         # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.set_to_missing_frames"                                   # unique identifier for buttons and menu items to reference.
    bl_label = "Set to Missing Frames"                                          # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        scn = context.scene

        # initializes self.frameRangesDict (returns False if frame range invalid)
        if not setFrameRangesDict(self):
            return{"FINISHED"}

        # list all missing files from start frame to end frame in render dump location
        scn.frameRanges = listMissingFiles(getNameOutputFiles(), self.frameRangesDict["string"])

        return{"FINISHED"}
