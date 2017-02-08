#!/usr/bin/env python

import bpy
import subprocess
import os
import json
import io
import time

from bpy.types import Operator
from bpy.props import *
from ..functions import *

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers through host server"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.refresh_num_available_servers"                           # unique identifier for buttons and menu items to reference.
    bl_label = "Refresh Available Servers"                                      # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def checkNumAvailServers(self):
        scn = bpy.context.scene
        command = "ssh -T -x {hostServerLogin} 'python {tempFilePath}blender_task -H --connection_timeout {timeout} --hosts_file {tempFilePath}servers.txt'".format(hostServerLogin=bpy.props.hostServerLogin, tempFilePath=scn.tempFilePath, timeout=str(scn.timeout))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        return process

    def updateAvailServerInfo(self):
        scn = bpy.context.scene

        line1 = self.process.stdout.readline().decode("ASCII").replace("\\n", "")
        line2 = self.process.stdout.readline().decode("ASCII").replace("\\n", "")
        available = json.loads(line1.replace("'", "\""))
        offline = json.loads(line2.replace("'", "\""))

        bpy.types.Scene.availableServers = StringProperty(name="Available Servers")
        bpy.types.Scene.offlineServers = StringProperty(name="Offline Servers")

        scn["availableServers"] = available
        scn["offlineServers"] = offline
        for a in bpy.context.screen.areas:
            a.tag_redraw()

    def modal(self, context, event):
        if event.type in {"ESC"}:
            self.cancel(context)
            self.report({"INFO"}, "Render process cancelled")
            return{"CANCELLED"}

        if event.type == "TIMER":
            self.process.poll()

            # if process finished and error thrown
            if self.process.returncode != 0 and self.process.returncode != None:
                handleError(self, "Process {curState}".format(curState=str(self.state-1)))
                return{"FINISHED"}

            # if process finished and no errors
            if self.process.returncode != None:
                # print("Process {curState} finished! (return code: {returnCode})".format(curState=str(self.state-1), returnCode=str(self.process.returncode)))

                # check the number of available servers through the host
                if self.state == 1:
                    self.process = self.checkNumAvailServers()
                    self.state += 1
                    return{"PASS_THROUGH"}

                elif self.state == 2:
                    self.updateAvailServerInfo()
                    scn = context.scene
                    self.report({"INFO"}, "Refresh process completed ({numAvailable} servers available)".format(numAvailable=str(len(scn['availableServers']))))
                    return{"FINISHED"}
                else:
                    self.report({"ERROR"}, "ERROR: Current state not recognized.")
                    return{"FINISHED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        print("\nRunning 'checkNumAvailServers' function...")
        scn = context.scene

        # format user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if not scn.tempFilePath.endswith("/"):
            scn.tempFilePath += "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial process
        self.state = 1 # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastTempFilePath != scn.tempFilePath:
            self.process = copyFiles()
            bpy.props.needsUpdating = False
            bpy.props.lastTempFilePath = scn.tempFilePath
        else:
            self.process = self.checkNumAvailServers()
            self.state += 1

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

    def averageFrames(self, scn):
        averageScriptPath = os.path.join(getLibraryPath(), "functions", "averageFrames.py")
        if scn.nameOutputFiles != "":
            self.nameOutputFiles = scn.nameOutputFiles
        else:
            self.nameOutputFiles = self.projectName
        runScriptCommand = "python {averageScriptPath} -p {renderDumpFolder} -n {nameOutputFiles}".format(averageScriptPath=averageScriptPath.replace(" ", "\\ "), renderDumpFolder=getRenderDumpFolder(), nameOutputFiles=self.nameOutputFiles)
        process = subprocess.Popen(runScriptCommand, shell=True)
        return process

    def modal(self, context, event):
        scn = context.scene

        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "PRESS":
            self.shift = True
        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"} and event.value == "RELEASE":
            self.shift = False

        if event.type in {"ESC"} and event.value == "PRESS":
            print("Process cancelled")
            setRenderStatus("image", "Finishing")
            if self.state[0] == 3:
                self.renderCancelled = True
                self.processes[0].kill()
                self.report({"INFO"}, "Render process cancelled. Fetching frames...")
            else:
                self.cancel(context)
                self.report({"INFO"}, "Render process cancelled")
                return{"CANCELLED"}

        elif self.state[0] < 4 and event.type in {"P"} and self.shift and not self.processes[1]:
            self.report({"INFO"}, "Preparing render preview...")
            self.processes[1] = getFrames(self.projectName, not self.previewed)
            self.state[1] = 4

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
                            return{"FINISHED"}
                        elif not self.previewed:
                            self.report({"INFO"}, "No render files found on host server")
                            return{"FINISHED"}
                        else:
                            pass
                    # handle unidentified errors
                    elif self.processes[i].returncode > 1:
                        setRenderStatus("image", "ERROR")

                        # define self.errorSource string
                        if not self.state[i] == 3:
                            self.errorSource = "Process " + str(self.state[i]-1)
                        else:
                            self.errorSource = "blender_task"

                        handleError(self, self.errorSource, i)
                        return{"FINISHED"}

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
                        jobsPerFrame = scn.maxSamples // self.sampleSize
                        if jobsPerFrame > 100:
                            self.report({"ERROR"}, "Max Samples / Samples > 100. Try increasing samples or lowering max samples.")
                            setRenderStatus("image", "ERROR")
                            return{"CANCELLED"}
                        self.processes[i] = renderFrames(str([self.curFrame]), self.projectName, jobsPerFrame)
                        self.state[i] += 1
                        setRenderStatus("image", "Rendering...")
                        return{"PASS_THROUGH"}

                    # get rendered frames from remote servers and archive old render files
                    elif self.state[i] == 3:
                        if self.processes[1] and self.processes[1].returncode == None:
                            self.processes[1].kill()
                        self.state[i] += 1
                        self.processes[0] = getFrames(self.projectName, not self.previewed)
                        if not self.renderCancelled:
                            setRenderStatus("image", "Finishing...")
                        return{"PASS_THROUGH"}

                    # average the rendered frames if there are new frames to average
                    elif self.state[i] == 4:
                        # only average if there are new frames to average
                        numLastRenderedFiles = self.numRenderedFiles
                        self.numRenderedFiles = getNumRenderedFiles("image")
                        if numLastRenderedFiles != self.numRenderedFiles:
                            self.processes[i] = self.averageFrames(scn)
                        self.state[i] += 1
                        return{'PASS_THROUGH'}

                    elif self.state[i] == 5:
                        self.numSamples = self.sampleSize * getNumRenderedFiles("image")
                        if i == 0:
                            setRenderStatus("image", "Complete!")
                            self.report({"INFO"}, "Render completed at {numSamples} samples! View the rendered image in your UV/Image_Editor".format(numSamples=str(self.numSamples)))
                        else:
                            # open preview image in UV/Image_Editor
                            context.area.type = "IMAGE_EDITOR"
                            averaged_image_filepath = os.path.join(bpy.path.abspath("//"), "render-dump", "{projectName}_average{extension}".format(projectName=self.projectName, extension=bpy.props.imExtension))
                            bpy.ops.image.open(filepath=averaged_image_filepath)
                            bpy.ops.image.reload()
                            self.processes[1] = False
                            self.previewed = True
                            previewString = "Render preview loaded ({numSamples} samples)".format(numSamples=str(self.numSamples))
                            self.report({"INFO"}, previewString)
                            print(previewString)
                        appendViewable("image")
                        removeViewable("animation")
                        if i == 0:
                            return{"FINISHED"}
                    else:
                        self.report({"ERROR"}, "ERROR: Current state not recognized.")
                        setRenderStatus("image", "ERROR")
                        return{"FINISHED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        scn = context.scene

        #for testing purposes only (saves unsaved file as 'unsaved_file.blend')
        if self.projectName == "":
            self.projectName = "unsaved_file"
            bpy.ops.wm.save_mainfile(filepath="{tempLocalDir}{projectName}.blend".format(tempLocalDir=scn.tempLocalDir, projectName=self.projectName))

        # ensure no other render processes are running
        runningStatus = ["Rendering...", "Preparing files..."]
        if getRenderStatus("image") in runningStatus or getRenderStatus("animation") in runningStatus:
            self.report({"WARNING"}, "Render in progress...")
            return{"FINISHED"}

        print("\nRunning sendFrame function...")

        # ensure the job won't break the script
        if not jobIsValid("image", self):
            return{"FINISHED"}

        # format user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if not scn.tempFilePath.endswith("/"):
            scn.tempFilePath += "/"

        # set the file extension for use with 'open image' button
        bpy.props.imExtension = scn.render.file_extension

        # Store current sample size for use in computing render results
        if scn.cycles.progressive == "PATH":
            self.sampleSize = scn.cycles.samples
            if scn.cycles.use_square_samples:
                self.sampleSize = self.sampleSize**2
        else:
            self.sampleSize = scn.cycles.aa_samples
            if scn.cycles.use_square_samples:
                self.sampleSize = self.sampleSize**2

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        self.stdout = None
        self.stderr = None
        self.shift = False
        self.renderCancelled = False
        self.numSuccessFrames = 0
        self.finishedFrames = 0
        self.previewed = False
        self.numSamples = 0
        self.numRenderedFiles = 0
        self.curFrame = scn.frame_current
        self.processes = [copyProjectFile(self.projectName), False]
        self.state = [1, 0]  # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastTempFilePath != scn.tempFilePath:
            bpy.props.needsUpdating = False
            bpy.props.lastTempFilePath = scn.tempFilePath
        else:
            self.state[0] += 1

        setRenderStatus("image", "Preparing files...")
        setRenderStatus("animation", "None")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        for j in range(len(self.processes)):
            if self.processes[j]:
                self.processes[j].kill()

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
            print("Process cancelled")
            setRenderStatus("animation", "Cancelled")
            if self.state[0] == 3:
                self.renderCancelled = True
                self.processes[0].kill()
                self.report({"INFO"}, "Render process cancelled. Fetching frames...")
            else:
                self.cancel(context)
                self.report({"INFO"}, "Render process cancelled")
                return{"CANCELLED"}

        elif self.state[0] < 4 and event.type in {"P"} and self.shift and not self.processes[1]:
            self.report({"INFO"}, "Checking render status...")
            self.processes[1] = getFrames(self.projectName, not self.statusChecked)
            self.state[1] = 4

        if event.type == "TIMER":
            numIters = 1
            if self.processes[1]:
                numIters += 1
            for i in range(numIters):
                self.processes[i].poll()

                if self.processes[i].returncode != None:
                    # handle rsync error of no output files found on server
                    if self.state[i] in [4, 5] and self.processes[i].returncode == 23:
                        if i == 1 and not self.statusChecked:
                            self.report({"WARNING"}, "No render files found - try again in a moment")
                            self.processes[1] = False
                            self.state[1] = -1
                            break
                        elif self.renderCancelled and not self.statusChecked:
                            self.report({"INFO"}, "Process cancelled - No output images found on host server")
                            return{"FINISHED"}
                        elif not self.statusChecked:
                            self.report({"INFO"}, "No render files found on host server")
                            return{"FINISHED"}
                        else:
                            pass
                    # handle unidentified errors
                    elif self.processes[i].returncode > 1:
                        setRenderStatus("animation", "ERROR")

                        # define self.errorSource string
                        if not self.state[i] == 3:
                            self.errorSource = "Process {state}".format(state=str(self.state[i]-1))
                        else:
                            self.errorSource = "blender_task"

                        handleError(self, self.errorSource, i)
                        return{"FINISHED"}

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
                        # initializes self.frameRangesDict (returns False if frame range invalid)
                        if not setFrameRangesDict(self):
                            setRenderStatus("animation", "ERROR")
                            return{"FINISHED"}
                        expandedFrameRange = expandFrames(json.loads(self.frameRangesDict["string"]))
                        self.processes[i] = renderFrames(str(expandedFrameRange), self.projectName)
                        bpy.props.animFrameRange = expandedFrameRange
                        setRenderStatus("animation", "Rendering...")
                        self.state[i] += 1
                        return{"PASS_THROUGH"}

                    # get rendered frames from remote servers and archive old render files
                    elif self.state[i] == 3:
                        if self.processes[1] and self.processes[1].returncode == None:
                            self.processes[1].kill()
                        self.state[0] += 1
                        self.processes[0] = getFrames(self.projectName, not self.statusChecked)
                        if not self.renderCancelled:
                            setRenderStatus("animation", "Finishing...")
                        return{"PASS_THROUGH"}

                    elif self.state[i] == 4:
                        if scn.nameOutputFiles != "":
                            self.fileName = scn.nameOutputFiles
                        else:
                            self.fileName = self.projectName
                        numCompleted = getNumRenderedFiles("animation", self.fileName)
                        if numCompleted > 0:
                            viewString = " - View rendered frames in '//render-dump/'"
                        else:
                            viewString = ""
                        self.report({"INFO"}, "Render completed for {numCompleted}/{numSent} frames{viewString}".format(numCompleted=numCompleted, numSent=len(bpy.props.animFrameRange), viewString=viewString))
                        appendViewable("animation")
                        if i == 1:
                            self.processes[1] = False
                            self.statusChecked = True
                        else:
                            setRenderStatus("animation", "Complete!")
                            return{"FINISHED"}
                    else:
                        self.report({"ERROR"}, "ERROR: Current state not recognized.")
                        setRenderStatus("animation", "ERROR")
                        return{"FINISHED"}

        return{"PASS_THROUGH"}

    def execute(self, context):# ensure no other animation render processes are running
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        scn = context.scene

        #for testing purposes only (saves unsaved file as 'unsaved_file.blend')
        if self.projectName == "":
            self.projectName = "unsaved_file"
            bpy.ops.wm.save_mainfile(filepath="{tempLocalDir}{projectName}.blend".format(tempLocalDir=scn.tempLocalDir, projectName=self.projectName))

        # ensure no other render processes are running
        runningStatus = ["Rendering...", "Preparing files..."]
        if getRenderStatus("image") in runningStatus or getRenderStatus("animation") in runningStatus:
            self.report({"WARNING"}, "Render in progress...")
            return{"FINISHED"}

        print("\nRunning sendAnimation function...")

        # ensure the job won't break the script
        if not jobIsValid("animation", self):
            return{"FINISHED"}

        # format user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if not scn.tempFilePath.endswith("/"):
            scn.tempFilePath += "/"

        # set the file extension for use with 'open animation' button
        bpy.props.animExtension = bpy.context.scene.render.file_extension

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

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
        self.processes = [copyProjectFile(self.projectName), False]
        self.state = [1, 0]  # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastTempFilePath != scn.tempFilePath:
            bpy.props.needsUpdating = False
            bpy.props.lastTempFilePath = scn.tempFilePath
        else:
            self.state[0] += 1

        setRenderStatus("animation", "Preparing files...")
        setRenderStatus("image", "None")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        for j in range(len(self.processes)):
            if self.processes[j]:
                self.processes[j].kill()

class openRenderedImageInUI(Operator):
    """Open rendered image"""                                                   # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.open_rendered_image"                                     # unique identifier for buttons and menu items to reference.
    bl_label = "Open Rendered Image"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        # open rendered image
        context.area.type = "IMAGE_EDITOR"
        averaged_image_filepath = os.path.join(bpy.path.abspath("//"), "render-dump", "{projectName}_average{extension}".format(projectName=self.projectName, extension=bpy.props.imExtension))
        bpy.ops.image.open(filepath=averaged_image_filepath)
        bpy.ops.image.reload()

        return{"FINISHED"}

class openRenderedAnimationInUI(Operator):
    """Open rendered animation"""                                               # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.open_rendered_animation"                                 # unique identifier for buttons and menu items to reference.
    bl_label = "Open Rendered Animation"                                        # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.


    def execute(self, context):
        self.frameRangesDict = buildFrameRangesString(context.scene.frameRanges)
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)

        # change contexts
        lastAreaType = context.area.type
        context.area.type = "CLIP_EDITOR"

        # opens first frame of image sequence (blender imports full sequence)
        openedFile = False
        image_sequence_filepath = "{dumpFolder}/".format(dumpFolder=getRenderDumpFolder())
        for frame in bpy.props.animFrameRange:
            try:
                image_filename = "{projectName}_{frame}{extension}".format(projectName=self.projectName, frame=str(frame).zfill(4), extension=bpy.props.animExtension)
                bpy.ops.clip.open(directory=image_sequence_filepath, files=[{"name":image_filename}])
                openedFile = True
                break
            except:
                pass
        if openedFile:
            bpy.ops.clip.reload()
        else:
            context.area.type = lastAreaType
            self.report({"ERROR"}, "Could not open rendered animation. View files in file browser in the following folder: '<project_folder>/render-dump'.")

        return{"FINISHED"}

class editRemoteServersDict(Operator):
    """Edit the remote servers dictionary in a text editor"""                   # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.edit_servers_dict"                                       # unique identifier for buttons and menu items to reference.
    bl_label = "Edit Remote Servers"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        context.area.type = "TEXT_EDITOR"
        try:
            libraryServersPath = os.path.join(getLibraryPath(), "servers")
            bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "remoteServers.txt"))
            self.report({"INFO"}, "Opened 'remoteServers.txt'")
            bpy.props.requiredFileRead = True
            bpy.props.needsUpdating = True
        except:
            self.report({"ERROR"}, "ERROR: Could not open 'remoteServers.txt'. If the problem persists, try reinstalling the add-on.")
        return{"FINISHED"}

class listMissingFrames(Operator):
    """List the output files missing from the render-dump folder"""             # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.list_frames"                                              # unique identifier for buttons and menu items to reference.
    bl_label = "List Missing Frames"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        scn = context.scene
        if scn.nameOutputFiles != "":
            self.fileName = scn.nameOutputFiles
        else:
            self.fileName = bpy.path.display_name_from_filepath(bpy.data.filepath)

        # initializes self.frameRangesDict (returns False if frame range invalid)
        if not setFrameRangesDict(self):
            return{"FINISHED"}

        # list all missing files from start frame to end frame in render-dump location
        missingFrames = listMissingFiles(self.fileName, self.frameRangesDict["string"])
        if len(missingFrames) > 0:
            self.report({"INFO"}, "Missing frames: {missingFrames}".format(missingFrames=missingFrames))
        else:
            self.report({"INFO"}, "All frames accounted for!")

        return{"FINISHED"}

class setToMissingFrames(Operator):
    """Set frame range to frames missing from the render-dump folder"""         # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.set_to_missing_frames"                                   # unique identifier for buttons and menu items to reference.
    bl_label = "Set to Missing Frames"                                          # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        scn = context.scene

        # set the name of the files to the project name or custom name defined in advanced settings
        if scn.nameOutputFiles != "":
            self.fileName = scn.nameOutputFiles
        else:
            self.fileName = bpy.path.display_name_from_filepath(bpy.data.filepath)

        # initializes self.frameRangesDict (returns False if frame range invalid)
        if not setFrameRangesDict(self):
            return{"FINISHED"}

        # list all missing files from start frame to end frame in render-dump location
        scn.frameRanges = listMissingFiles(self.fileName, self.frameRangesDict["string"])

        return{"FINISHED"}
