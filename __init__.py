#!/usr/bin/python
bl_info = {
    "name"        : "Server Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 6, 0),
    "blender"     : (2, 78, 0),
    "description" : "Render your scene on a remote server farm with this addon.",
    "location"    : "View3D > Tools > Render",
    "warning"     : "",
    "wiki_url"    : "",
    "tracker_url" : "",
    "category"    : "Render"}

import bpy, subprocess, telnetlib, sys, os, numpy, time, json, math
from bpy.types import (Menu, Panel, UIList, Operator, AddonPreferences, PropertyGroup)
from bpy.props import *

# Global variables
renderStatus        = {"animation":"None", "image":"None"}
killingStatus       = "None"
event_timer_len     = 0.1
projectPath         = ""
projectName         = ""
serverFilePath      = ""
serverPath_toRemote = ""
hostServerLogin     = ""
dumpLocation        = ""
renderType          = []
frameRangesDict     = {}
hostServer          = ""
servers             = ""
extension           = ""
username            = ""

def getLibraryPath():
    # Full path to "\addons\server_farm_client\" -directory
    paths = bpy.utils.script_paths("addons")

    libraryPath = 'assets'
    for path in paths:
        libraryPath = os.path.join(path, "server_farm_client_add-on")
        if os.path.exists(libraryPath):
            break

    if not os.path.exists(libraryPath):
        raise NameError('Did not find assets path from ' + libraryPath)
    return libraryPath

def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### BEGIN " + flagName + " ###\n"):
        nextLine = f.readline()
        numIters += 1
        if numIters >= 300:
            print("Unable to read with over 300 preceeding lines.")
            break

    # read following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### END " + flagName + " ###\n"):
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            print("Unable to read over 250 lines.")
            break

    return readLines

def importServerFiles():
    global hostServer
    global servers
    global extension
    global username

    libraryServersPath = os.path.join(getLibraryPath(), "servers")
    serverFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    username    = readFileFor(serverFile, "SSH USERNAME").replace("\"", "")
    hostServer  = readFileFor(serverFile, "HOST SERVER").replace("\"", "")
    extension   = readFileFor(serverFile, "EXTENSION").replace("\"", "")
    servers     = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))

def main():
    getLibraryPath()
    importServerFiles()
main()

class View3DPanel():
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

def setHostServerLogin():
    global hostServerLogin
    hostServerLogin = username + "@" + hostServer + extension

def setGlobalProjectVars():
    global projectPath
    global projectName
    global serverFilePath
    global serverPath_toRemote
    global dumpLocation

    projectPath         = bpy.path.abspath("//")
    projectName         = bpy.path.display_name_from_filepath(bpy.data.filepath)
    serverFilePath      = "/tmp/" + username + "/" + projectName + "/"
    serverPath_toRemote = serverFilePath + "toRemote/"
    dumpLocation        = projectPath + "render-dump/"
    setHostServerLogin()
    print(projectPath + projectName)

def checkNumAvailServers(scn=None):
    process = subprocess.Popen("ssh " + hostServerLogin + " 'blender_task.py -H'", stdout=subprocess.PIPE, shell=True)
    process.poll()
    while process.returncode == None:
        time.sleep(0.1)
        process.poll()
    line1 = process.stdout.readline().decode('ASCII').replace("\\n", "")
    line2 = process.stdout.readline().decode('ASCII').replace("\\n", "")
    available = json.loads(line1.replace("'", "\""))
    offline = json.loads(line2.replace("'", "\""))
    if scn != None:
         bpy.types.Scene.availableServers = StringProperty(name = "Available Servers")
         bpy.types.Scene.offlineServers = StringProperty(name = "Offline Servers")

         scn['availableServers'] = available
         scn['offlineServers'] = offline
         for a in bpy.context.screen.areas:
             a.tag_redraw()
         return
    return available

# def checkNumAvailServers(scn=None):
#     hosts       = []
#     unreachable = []
#     for groupName in servers:
#         for host in servers[groupName]:
#             try:
#                 tn = telnetlib.Telnet(host + extension,22,.4)
#                 hosts.append(host)
#             except:
#                 unreachable.append(host)
#
#     if scn != None:
#         bpy.types.Scene.availableServers = StringProperty(name = "Available Servers")
#         bpy.types.Scene.offlineServers   = StringProperty(name = "Offline Servers")
#         scn['availableServers'] = hosts
#         scn['offlineServers']   = unreachable
#         for a in bpy.context.screen.areas:
#             a.tag_redraw()
#         return
#     else:
#         return hosts

def jobIsValid(jobType):
    if projectName == "":
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: You have not saved your project file. Please save it before attempting to render."}
    elif " " in projectName:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER ABORTED: Please remove ' ' (spaces) from the project file name."}
    elif bpy.context.scene.camera is None:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: No camera in scene."}
    elif jobType == "image":
        if bpy.context.scene.render.image_settings.color_mode == 'BW':
            return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: 'BW' color mode not currently supported. Supported modes: ['RGB', 'RGBA']"}
        if bpy.context.scene.cycles.progressive == 'PATH':
            samples = bpy.context.scene.cycles.samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 10:
                return {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at " + str(samples) + " samples. Try 10 or more samples for a more accurate render."}
            else:
                return {"valid":True, "errorType":None, "errorMessage":None}
        elif bpy.context.scene.cycles.progressive == 'BRANCHED_PATH':
            samples = bpy.context.scene.cycles.aa_samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 5:
                return {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at " + str(samples) + " AA samples. Try 5 or more AA samples for a more accurate render."}
            else:
                return {"valid":True, "errorType":None, "errorMessage":None}
        else:
            return {"valid":True, "errorType":None, "errorMessage":None}
    else:
        return {"valid":True, "errorType":None, "errorMessage":None}

def cleanLocalDirectoryForGetFrames():
    print("verifying local directory...")
    mkdirCommand = "mkdir -p " + dumpLocation + "backups/"
    subprocess.call(mkdirCommand, shell=True)

    print("cleaning up local directory...")
    rsyncCommand = "rsync --remove-source-files --exclude='" + projectName + "_average.*' " + dumpLocation + "* " + dumpLocation + "backups/"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def getFrames():
    print("verifying remote directory...")
    mkdirCommand = "ssh " + hostServerLogin + " 'mkdir -p " + serverFilePath + ";'"
    subprocess.call(mkdirCommand, shell=True)

    print("copying files from server...\n")
    rsyncCommand = "rsync --remove-source-files --exclude='*.blend' '" + hostServerLogin + ":" + serverFilePath + "results/*' '" + dumpLocation + "'"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def averageFrames():
    averageScriptPath = os.path.join(getLibraryPath(), "scripts", "averageFrames.py")
    runScriptCommand = "python " + averageScriptPath.replace(" ", "\\ ") + " -p " + projectPath + " -n " + projectName
    print(runScriptCommand)
    process = subprocess.Popen(runScriptCommand, shell=True)
    return process

def buildFrameRangesString(frameRanges):
    frameRangeList = frameRanges.replace(" ", "").split(",")
    newFrameRangeList = []
    invalidDict = { "valid":False, "string":None }
    for string in frameRangeList:
        try:
            newInt = int(string)
            if newInt not in newFrameRangeList:
                newFrameRangeList.append(newInt)
        except:
            if "-" in string:
                newString = string.split("-")
                if len(newString) > 2:
                    return invalidDict
                try:
                    newInt1 = int(newString[0])
                    newInt2 = int(newString[1])
                    if newInt1 <= newInt2:
                        newFrameRangeList.append([newInt1,newInt2])
                    else:
                        return invalidDict
                except:
                    return invalidDict
            else:
                return invalidDict
    return { "valid":True, "string":str(newFrameRangeList).replace(" ","") }

def cleanLocalDirectoryForRenderFrames():
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(copy=True)

    print("verifying remote directory...")
    sshCommand = "ssh " + hostServerLogin + " 'mkdir -p " + serverPath_toRemote + "'"
    print(sshCommand)
    subprocess.call(sshCommand, shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    rsyncCommand = "rsync -a --copy-links --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServerLogin + ":" + serverPath_toRemote + "'"
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def copyPythonPreferencesFile():
    rsyncCommand = "rsync -a --include=blender_p.py --exclude='*' '" + os.path.join(getLibraryPath(), "scripts") + "/' '" + hostServerLogin + ":" + serverPath_toRemote + "'"
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def writeServersFile():
    f = open(os.path.join(getLibraryPath(), "servers", "servers.txt"), "w")
    # define serversToUse
    scn = bpy.context.scene
    if(scn.serverGroups == "All Servers"):
        serversToUse = servers
    else:
        serversToUse = {}
        serversToUse[scn.serverGroups] = servers[scn.serverGroups]
    print(serversToUse)
    f.write("### BEGIN REMOTE SERVERS DICTIONARY ###\n")
    f.write(str(serversToUse).replace("'", "\"") + "\n")
    f.write("### END REMOTE SERVERS DICTIONARY ###\n")
    return

def copyRemoteServersFile():
    writeServersFile()
    rsyncCommand = "rsync -a --include=servers.txt --exclude='*' '" + os.path.join(getLibraryPath(), "servers") + "/' '" + hostServerLogin + ":" + serverPath_toRemote + "'"
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def renderFrames(frameRange):
    # run blender command to render given range from the remote server
    renderCommand = "ssh " + hostServerLogin + " 'blender_task.py -p -n " + projectName + " -l " + frameRange + " --hosts_file " + serverPath_toRemote + "servers.txt --local_sync " + serverPath_toRemote + "'"
    process = subprocess.Popen(renderCommand, shell=True)
    # To see output from 'blender_task.py', add the -p tag to the 'blender_task.py' call above
    print("Process sent to remote servers!\n")
    return process

def setRenderStatus(key, status):
    global renderStatus
    renderStatus[key] = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getRenderStatus(key):
    return renderStatus[key]

def setKillingStatus(status):
    global killingStatus
    killingStatus = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getKillingStatus():
    return killingStatus

def killAllBlender():
    setKillingStatus("running...")
    killScriptPath = os.path.join(getLibraryPath(), "scripts", "killAllBlender.py")
    runScriptCommand = "python " + killScriptPath.replace(" ", "\\ ") + " -s '" + str(checkNumAvailServers()).replace(" ","").replace("'","\"") + "' -e " + extension + " -u " + username
    print(runScriptCommand)
    process = subprocess.Popen(runScriptCommand, stdout=subprocess.PIPE, shell=True)
    return process

def appendViewable(typeOfRender):
    global renderType
    if(typeOfRender not in renderType):
        renderType.append(typeOfRender)

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers via telnet"""  # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.refresh_num_available_servers"  # unique identifier for buttons and menu items to reference.
    bl_label   = "Refresh Available Servers"            # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        setHostServerLogin()
        checkNumAvailServers(context.scene)
        return {'FINISHED'}

class sendFrameToRenderFarm(Operator):
    """Render current frame on remote servers"""            # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_frame_on_servers"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Current Frame"                     # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Render process cancelled")
            print("Process cancelled")
            setRenderStatus("image", "Cancelled")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()

            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished!\n")

                # copy python preferences file to host server
                if(self.state == 1):
                    print("Copying python preferences file to host server...")
                    self.process = copyPythonPreferencesFile()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # copy servers text file to host server
                elif(self.state == 2):
                    print("Copying servers text file to host server...")
                    self.process = copyRemoteServersFile()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process at current frame
                elif(self.state == 3):
                    self.process = renderFrames("[" + str(self.curFrame) + "]")
                    self.state += 1
                    setRenderStatus("image", "Rendering...")
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                elif(self.state == 4):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("image", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 5):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # average the rendered frames
                elif(self.state == 6):
                    print("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}

                elif(self.state == 7):
                    self.report({'INFO'}, "Render completed! View the rendered image in your UV/Image_Editor")
                    setRenderStatus("image", "Complete!")
                    appendViewable("image")
                    return{'FINISHED'}
                else:
                    self.report({'ERROR'}, "ERROR: Current state not recognized.")
                    setRenderStatus("image", "ERROR")
                    return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):
        # ensure no other image render processes are running
        if(getRenderStatus("image") in ["Rendering...", "Preparing files..."]):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}

        # init global project variables
        setGlobalProjectVars()

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("image")
        if jobValidityDict["errorType"] != None:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
        else:
            self.report({'INFO'}, "Rendering current frame on " + str(len(context.scene['availableServers'])) + " servers.")
        if not jobValidityDict["valid"]:
            return{'FINISHED'}

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        self.curFrame = context.scene.frame_current
        self.process = cleanLocalDirectoryForRenderFrames()
        self.state   = 1  # initializes state for modal

        setRenderStatus("image", "Preparing files...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class sendAnimationToRenderFarm(Operator):
    """Render animation on remote servers"""            # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_animation_on_servers"    # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Animation"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def modal(self, context, event):
        scn = context.scene

        if event.type in {'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Render process cancelled")
            print("Process cancelled")
            setRenderStatus("animation", "Cancelled")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()

            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished!\n")

                # copy python preferences file to host server
                if(self.state == 1):
                    print("Copying python preferences file to host server...")
                    self.process = copyPythonPreferencesFile()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # copy servers text file to host server
                elif(self.state == 2):
                    print("Copying servers text file to host server...")
                    self.process = copyRemoteServersFile()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process from the defined start and end frames
                elif(self.state == 3):
                    if scn.frameRanges == "":
                        self.process = renderFrames("[[" + str(self.startFrame) + "," + str(self.endFrame) + "]]")
                    else:
                        global frameRangesDict
                        frameRangesDict = buildFrameRangesString(scn.frameRanges)
                        if(frameRangesDict["valid"]):
                            self.process = renderFrames(frameRangesDict["string"])
                        else:
                            self.report({'ERROR'}, "ERROR: Invalid frame ranges given.")
                            setRenderStatus("animation", "ERROR")
                            return{'FINISHED'}
                    setRenderStatus("animation", "Rendering...")
                    self.state += 1
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                elif(self.state == 4):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("animation", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 5):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state +=1
                    return{'PASS_THROUGH'}

                elif(self.state == 6):
                    self.report({'INFO'}, "Render completed! View the rendered animation in '//render/'")
                    setRenderStatus("animation", "Complete!")
                    appendViewable("animation")
                    return{'FINISHED'}
                else:
                    self.report({'ERROR'}, "ERROR: Current state not recognized.")
                    setRenderStatus("animation", "ERROR")
                    return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):# ensure no other animation render processes are running
        if(getRenderStatus("animation") in ["Rendering...","Preparing files..."]):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}

        # init global project variables
        setGlobalProjectVars()

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("animation")
        if not jobValidityDict["valid"]:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
            return{'FINISHED'}

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        self.startFrame = context.scene.frame_start
        self.endFrame   = context.scene.frame_end
        self.process    = cleanLocalDirectoryForRenderFrames()
        self.state      = 1   # initializes state for modal

        self.report({'INFO'}, "Rendering animation on " + str(len(context.scene['availableServers'])) + " servers.")
        setRenderStatus("animation", "Preparing files...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class getRenderedFrames(Operator):
    """Get rendered frames from host server"""          # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.get_rendered_frames"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Get Rendered Frames"                  # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def modal(self, context, event):
        self.process.poll()

        if self.process.returncode != None:
            print("Process " + str(self.state) + " finished!\n")
            self.report({'INFO'}, "'Get Frames' process complete.")

            return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):
        # init global project variables
        setGlobalProjectVars()

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("animation")
        if not jobValidityDict["valid"]:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
            return{'FINISHED'}

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        cleanLocalDirectoryForGetFrames()

        # start initial render process
        self.process    = getFrames()
        self.state      = 1                 # initializes state for modal
        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

# class averageRenderedFrames(Operator):
#     """Average pixels in rendered frames"""                 # blender will use this as a tooltip for menu items and buttons.
#     bl_idname  = "scene.average_frames"                     # unique identifier for buttons and menu items to reference.
#     bl_label   = "Average Rendered Frames"                  # display name in the interface.
#     bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.
#
#     def modal(self, context, event):
#         self.process.poll()
#
#         if self.process.returncode != None:
#             print("Process " + str(self.state) + " finished!\n")
#             self.report({'INFO'}, "Frame averaging process complete.")
#
#             return{'FINISHED'}
#
#         return{'PASS_THROUGH'}
#
#     def execute(self, context):
#         # init global project variables
#         setGlobalProjectVars()
#
#         # ensure the job won't break the script
#         jobValidityDict = jobIsValid("animation")
#         if not jobValidityDict["valid"]:
#             self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
#             return{'FINISHED'}
#
#         # create timer for modal
#         wm = context.window_manager
#         self._timer = wm.event_timer_add(event_timer_len, context.window)
#         wm.modal_handler_add(self)
#
#         # start initial render process
#         self.process    = averageFrames()
#         self.state      = 1                 # initializes state for modal
#
#         return{'RUNNING_MODAL'}
#
#     def cancel(self, context):
#         wm = context.window_manager
#         wm.event_timer_remove(self._timer)
#         self.process.kill()
#
#     def execute(self, context):
#         averageFrames()
#         return{'FINISHED'}

class openRenderedImageInUI(Operator):
    """Open rendered image"""                                       # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.open_rendered_image"                            # unique identifier for buttons and menu items to reference.
    bl_label   = "Open Rendered Image"    # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                   # enable undo for the operator.

    def execute(self, context):
        # open rendered image
        context.area.type = 'IMAGE_EDITOR'
        averaged_image_filepath = projectPath + "render-dump/" + projectName + "_average.tga"
        bpy.ops.image.open(filepath=averaged_image_filepath)
        bpy.ops.image.reload()

        return{'FINISHED'}

class openRenderedAnimationInUI(Operator):
    """Open rendered animation"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.open_rendered_animation"  # unique identifier for buttons and menu items to reference.
    bl_label   = "Open Rendered Animation"        # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}             # enable undo for the operator.

    def execute(self, context):
        # open rendered image
        context.area.type = 'CLIP_EDITOR'
        image_sequence_filepath = projectPath + "render-dump/"
        if context.scene.frameRanges == "":
            fs = context.scene.frame_start
        else:
            if frameRangesDict["valid"]:
                fr = json.loads(frameRangesDict["string"])[0]
                if type(fr) == list:
                    fs = fr[0]
                else:
                    fs = fr
            else:
                self.report({'ERROR'}, "ERROR: Invalid frame ranges given.")
                return{'FINISHED'}

        # zero pad the value
        if fs < 10:
            fs = "000" + str(fs)
        elif fs < 100:
            fs = "00" + str(fs)
        elif fs < 1000:
            fs = "0" + str(fs)

        image_filename = projectName + "_" + fs + ".tga"
        print("Opening frame: " + image_filename)
        bpy.ops.clip.open(directory=image_sequence_filepath, files=[{"name":image_filename}])
        bpy.ops.clip.reload()

        return{'FINISHED'}

class editRemoteServersDict(Operator):
    """Edit the remote servers dictionary in a text editor"""                       # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.edit_servers_dict"                                          # unique identifier for buttons and menu items to reference.
    bl_label   = "Edit Remote Servers"                                              # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                               # enable undo for the operator.

    def execute(self, context):
        context.area.type = 'TEXT_EDITOR'
        try:
            libraryServersPath = os.path.join(getLibraryPath(), "servers")
            bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "remoteServers.txt"))
            self.report({'INFO'}, "Opened 'remoteServers.txt'")
        except:
            self.report({'ERROR'}, "ERROR: Could not open 'remoteServers.txt'")
        return{'FINISHED'}

class commitEdits(Operator):
    """Press this button to commit changes made to remote/host servers"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.commit_edits"                                          # unique identifier for buttons and menu items to reference.
    bl_label   = "Commit Edits"                                                # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                          # enable undo for the operator.

    def execute(self, context):
        importServerFiles()
        return{'FINISHED'}

class killBlender(Operator):
    """Kill all blender processes on all remote servers"""              # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.kill_blender"                                   # unique identifier for buttons and menu items to reference.
    bl_label   = "Kill All Blender Processes"     # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                   # enable undo for the operator.

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Kill process cancelled")
            print("Process cancelled")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()

            if self.process.returncode != None:
                self.report({'INFO'}, "Kill All Blender Process Finished!")
                setKillingStatus("Finished")
                return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start killAllBlender process
        self.process = killAllBlender()

        self.report({'INFO'}, "Killing blender processes on " + str(len(context.scene['availableServers'])) + " servers...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class drawRenderOnServersPanel(View3DPanel, Panel):
    bl_label    = "Render on Servers"
    bl_idname   = "VIEW3D_PT_tools_render_on_servers"
    bl_context  = "objectmode"
    bl_category = "Render"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        imRenderStatus = getRenderStatus("image")
        animRenderStatus = getRenderStatus("animation")

        # Available Servers Info
        col = layout.column(align=True)
        row = col.row(align=True)
        availableServerString = 'Available Servers: ' + str(len(scn['availableServers'])) + " / " + str(len(scn['availableServers']) + len(scn['offlineServers']))
        row.operator("scene.refresh_num_available_servers", text=availableServerString, icon="FILE_REFRESH")

        # Render Buttons
        row = col.row(align=True)
        row.alignment = 'EXPAND'
        row.active = len(scn['availableServers']) > 0
        row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
        row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scn, "serverGroups")

        # Render Status Info
        if(imRenderStatus != "None" and animRenderStatus != "None"):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label('Render Status (cf): ' + imRenderStatus)
            row = col.row(align=True)
            row.label('Render Status (a):  ' + animRenderStatus)
        elif(imRenderStatus != "None"):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label('Render Status: ' + imRenderStatus)
        elif(animRenderStatus != "None"):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label('Render Status: ' + animRenderStatus)


        # display buttons to view render(s)
        row = layout.row(align=True)
        if   "image"   in renderType:
            row.operator("scene.open_rendered_image", text="View Image", icon="FILE_IMAGE")
        if "animation" in renderType:
            row.operator("scene.open_rendered_animation", text="View Animation", icon="FILE_MOVIE")

    def invoke(self, context, layout):
        checkNumAvailServers(context.scene)
        return{'RUNNING_MODAL'}

class drawSamplesPanel(View3DPanel, Panel):
    bl_label    = "Sampling (Single Frame)"
    bl_idname   = "VIEW3D_PT_sampling"
    bl_context  = "objectmode"
    bl_category = "Render"

    def calcSamples(self, scn, squared, category, multiplier):
        if squared:
            category = category**2
        result = math.floor(multiplier*category*len(scn['availableServers']))
        return result


    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Basic Render Samples Info
        col = layout.column(align=True)
        row = col.row(align=True)

        if not context.scene.cycles.progressive == 'BRANCHED_PATH':
            sampleSize = scn.cycles.samples
            if(scn.cycles.use_square_samples):
                sampleSize = sampleSize**2
            if sampleSize < 10:
                row.label('Samples: Too few samples')
            else:
                row.label("Samples: " + str(math.floor(sampleSize*len(scn['availableServers']))))
        else:
            # find AA sample size first (this affects other sample sizes)
            aaSampleSize = scn.cycles.aa_samples
            squared = False
            if(scn.cycles.use_square_samples):
                squared = True
                aaSampleSize = aaSampleSize**2

            # calculate sample sizes for single frame renders on available servers
            aa    = self.calcSamples(scn, squared, aaSampleSize, 1)
            diff  = self.calcSamples(scn, squared, scn.cycles.diffuse_samples, aaSampleSize)
            glos  = self.calcSamples(scn, squared, scn.cycles.glossy_samples, aaSampleSize)
            tran  = self.calcSamples(scn, squared, scn.cycles.transmission_samples, aaSampleSize)
            ao    = self.calcSamples(scn, squared, scn.cycles.ao_samples, aaSampleSize)
            meshL = self.calcSamples(scn, squared, scn.cycles.mesh_light_samples, aaSampleSize)
            sub   = self.calcSamples(scn, squared, scn.cycles.subsurface_samples, aaSampleSize)
            vol   = self.calcSamples(scn, squared, scn.cycles.volume_samples, aaSampleSize)

            row = col.row(align=True)
            if(aaSampleSize < 5):
                row.label('AA: Too few samples')
            else:
                row.label('AA:')
                row.label(str(aa))
                row = col.row(align=True)
                row.label('Diffuse:')
                row.label(str(diff))
                row = col.row(align=True)
                row.label('Glossy:')
                row.label(str(glos))
                row = col.row(align=True)
                row.label('Transmission:')
                row.label(str(tran))
                row = col.row(align=True)
                row.label('AO:')
                row.label(str(ao))
                row = col.row(align=True)
                row.label('Mesh Light:')
                row.label(str(meshL))
                row = col.row(align=True)
                row.label('Subsurface:')
                row.label(str(sub))
                row = col.row(align=True)
                row.label('Volume:')
                row.label(str(vol))

class drawFrameRangePanel(View3DPanel, Panel):
    bl_label    = "Frame Range"
    bl_idname   = "VIEW3D_PT_frame_range"
    bl_context  = "objectmode"
    bl_category = "Render"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scn, "frameRanges")

class drawServersPanel(View3DPanel, Panel):
    bl_label    = "Servers"
    bl_idname   = "VIEW3D_PT_servers"
    bl_context  = "objectmode"
    bl_category = "Render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("scene.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")
        row = col.row(align=True)
        row.operator("scene.commit_edits", text="Commit Edits", icon="FILE_REFRESH")

class drawAdminOptionsPanel(View3DPanel, Panel):
    bl_label    = "Admin Tasks"
    bl_idname   = "VIEW3D_PT_tools_admin_options"
    bl_context  = "objectmode"
    bl_category = "Render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        killingStatus = getKillingStatus()

        # Render Buttons
        col = layout.column(align=True)
        col.active = len(scn['availableServers']) > 0
        row = col.row(align=True)
        row.operator("scene.get_rendered_frames", text="Get Frames", icon="LOAD_FACTORY")
        #row = col.row(align=True)
        #row.operator("scene.average_frames", text="Average Frames", icon="RENDERLAYERS")

        row = col.row(align=True)
        row = col.row(align=True)
        row.operator("scene.kill_blender", text="Kill All Blender Processes", icon="CANCEL")

        # Killall Blender Status
        if(killingStatus != "None"):
            row = col.row(align=True)
            if killingStatus == "Finished":
                row.label('Blender processes killed!')
            else:
                row.label('Killing blender on remote servers...')

def register():
    # initialize check box for displaying render sampling details
    bpy.types.Scene.boolTool = BoolProperty(
        name="Show Details",
        description="Display details for render sample settings",
        default = False)

    # initialize frame range string text box
    bpy.types.Scene.frameRanges = StringProperty(
        name = "Frames")

    groupNames = [("All Servers","All Servers","Render on all servers")]
    for groupName in servers:
        junkList = [groupName,groupName,"Render only servers on this group"]
        groupNames.append(tuple(junkList))
    print(groupNames)
    bpy.types.Scene.serverGroups = EnumProperty(
        attr="serverGroups",
        name="Servers",
        description="Choose which hosts to use for render processes",
        items=groupNames,
        default='All Servers')

    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.boolTool
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.serverGroups

if __name__ == "__main__":
    register()

print("'sendToRenderFarm' Script Loaded")
