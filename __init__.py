#!/usr/bin/python
bl_info = {
    "name"        : "Server Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 6, 1),
    "blender"     : (2, 78, 0),
    "description" : "Render your scene on a remote server farm with this addon.",
    "location"    : "View3D > Tools > Render",
    "warning"     : "Relatively stable but still work in progress",
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
    serverFilePath      = projectName + "/"
    serverPath_toRemote = serverFilePath + "toRemote/"
    dumpLocation        = projectPath + "render-dump/"
    setHostServerLogin()
    print(projectPath + projectName)

def checkNumAvailServers(scn):
    command = "ssh " + hostServerLogin + " 'python " + scn.tempFilePath + "blender_task.py -H --hosts_file " + scn.tempFilePath + "servers.txt'"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    #process = subprocess.Popen(command, shell=True)
    return process

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

def getFrames(scn):
    print("verifying remote directory...")
    mkdirCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + serverFilePath + ";'"
    subprocess.call(mkdirCommand, shell=True)

    print("copying files from server...\n")
    rsyncCommand = "rsync --remove-source-files --exclude='*.blend' '" + hostServerLogin + ":" + scn.tempFilePath + serverFilePath + "results/*' '" + dumpLocation + "'"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def averageFrames():
    averageScriptPath = os.path.join(getLibraryPath(), "scripts", "averageFrames.py")
    runScriptCommand = "python " + averageScriptPath.replace(" ", "\\ ") + " -p " + projectPath + " -n " + projectName
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

def cleanLocalDirectoryForRenderFrames(scn):
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(copy=True)

    print("verifying remote directory...")
    sshCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + serverPath_toRemote + "'"
    subprocess.call(sshCommand, shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    rsyncCommand = "rsync --copy-links -rqa --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServerLogin + ":" + scn.tempFilePath + serverPath_toRemote + "'"
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def copyFiles(scn):
    rsyncCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + "'; rsync -a '" + os.path.join(getLibraryPath(), "to_host_server") + "/' '" + hostServerLogin + ":" + scn.tempFilePath + "'"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def writeServersFile():
    f = open(os.path.join(getLibraryPath(), "to_host_server", "servers.txt"), "w")
    # define serversToUse
    scn = bpy.context.scene
    if(scn.serverGroups == "All Servers"):
        serversToUse = servers
    else:
        serversToUse = {}
        serversToUse[scn.serverGroups] = servers[scn.serverGroups]
    f.write("### BEGIN REMOTE SERVERS DICTIONARY ###\n")
    f.write(str(serversToUse).replace("'", "\"") + "\n")
    f.write("### END REMOTE SERVERS DICTIONARY ###\n")
    return

def renderFrames(frameRange, scn):
    # run blender command to render given range from the remote server
    renderCommand = "ssh " + hostServerLogin + " 'python " + scn.tempFilePath + "blender_task.py -p -n " + projectName + " -l " + frameRange + " --hosts_file " + scn.tempFilePath + "servers.txt --local_sync " + scn.tempFilePath + serverPath_toRemote + "'"
    process = subprocess.Popen(renderCommand, shell=True)
    print("Process sent to remote servers!\n")
    return process

def setRenderStatus(key, status):
    global renderStatus
    renderStatus[key] = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getRenderStatus(key):
    return renderStatus[key]

def appendViewable(typeOfRender):
    global renderType
    if(typeOfRender not in renderType):
        renderType.append(typeOfRender)

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers through host server""" # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.refresh_num_available_servers"          # unique identifier for buttons and menu items to reference.
    bl_label   = "Refresh Available Servers"                    # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                           # enable undo for the operator.

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Render process cancelled")
            print("Process cancelled")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()

            if self.process.returncode != 0 and self.process.returncode != None:
                # errorMessage = str(self.process.stdout.readline(),'utf-8')
                # print(errorMessage)
                # self.report({'ERROR'}, errorMessage)
                self.report({'ERROR'}, "There was an error. See terminal for details...")
                return{'FINISHED'}
            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished! (return code: " + str(self.process.returncode) + ")\n")

                # check the number of available servers through the host
                if(self.state == 1):
                    print("Running 'checkNumAvailServers' function...")
                    self.process = checkNumAvailServers(context.scene)
                    self.state += 1
                    return{'PASS_THROUGH'}

                elif(self.state == 2):
                    scn = context.scene

                    line1 = self.process.stdout.readline().decode('ASCII').replace("\\n", "")
                    line2 = self.process.stdout.readline().decode('ASCII').replace("\\n", "")
                    available = json.loads(line1.replace("'", "\""))
                    offline = json.loads(line2.replace("'", "\""))

                    bpy.types.Scene.availableServers = StringProperty(name = "Available Servers")
                    bpy.types.Scene.offlineServers = StringProperty(name = "Offline Servers")

                    scn['availableServers'] = available
                    scn['offlineServers'] = offline
                    for a in context.screen.areas:
                        a.tag_redraw()
                    self.report({'INFO'}, "Refresh process completed")
                    return{'FINISHED'}
                else:
                    self.report({'ERROR'}, "ERROR: Current state not recognized.")
                    return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):

        setHostServerLogin()
        writeServersFile()

        # verify user input for tempFilePath string
        scn = context.scene
        scn.tempFilePath.replace(" ", "_")
        if scn.tempFilePath[-1] != "/":
            scn.tempFilePath = scn.tempFilePath + "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start initial process
        print("Copying project files...")
        self.process = copyFiles(scn)
        self.state   = 1  # initializes state for modal

        self.report({'INFO'}, "Refreshing available servers...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

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

            if self.process.returncode != None and self.process.returncode > 1:
                # errorMessage = str(self.process.stdout.readline(),'utf-8')
                # print(errorMessage)
                # self.report({'ERROR'}, errorMessage)
                self.report({'ERROR'}, "There was an error. See terminal for details...")
                setRenderStatus("image", "ERROR")
                return{'FINISHED'}
            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished! (return code: " + str(self.process.returncode) + ")\n")

                # copy files to host server
                if(self.state == 1):
                    print("Copying files to host server...")
                    self.process = copyFiles(context.scene)
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process at current frame
                elif(self.state == 2):
                    self.process = renderFrames("[" + str(self.curFrame) + "]", context.scene)
                    self.state += 1
                    setRenderStatus("image", "Rendering...")
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                elif(self.state == 3):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("image", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 4):
                    print("Fetching render files...")
                    self.process = getFrames(context.scene)
                    self.state += 1
                    return{'PASS_THROUGH'}

                # average the rendered frames
                elif(self.state == 5):
                    print("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}

                elif(self.state == 6):
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
        scn = context.scene

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
            self.report({'INFO'}, "Rendering current frame on " + str(len(scn['availableServers'])) + " servers.")
        if not jobValidityDict["valid"]:
            return{'FINISHED'}

        # verify user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if scn.tempFilePath[-1] != "/":
            scn.tempFilePath = scn.tempFilePath + "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        writeServersFile()
        self.curFrame = context.scene.frame_current
        self.process = cleanLocalDirectoryForRenderFrames(scn)
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

            if self.process.returncode != None and self.process.returncode > 1:
                # errorMessage = str(self.process.stdout.readline(),'utf-8')
                # print(errorMessage)
                # self.report({'ERROR'}, errorMessage)
                self.report({'ERROR'}, "There was an error. See terminal for details...")
                setRenderStatus("animation", "ERROR")
                return{'FINISHED'}
            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished! (return code: " + str(self.process.returncode) + ")\n")

                # copy files to host server
                if(self.state == 1):
                    print("Copying files to host server...")
                    self.process = copyFiles(context.scene)
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process from the defined start and end frames
                elif(self.state == 2):
                    if scn.frameRanges == "":
                        self.process = renderFrames("[[" + str(self.startFrame) + "," + str(self.endFrame) + "]]", context.scene)
                    else:
                        global frameRangesDict
                        frameRangesDict = buildFrameRangesString(scn.frameRanges)
                        if(frameRangesDict["valid"]):
                            self.process = renderFrames(frameRangesDict["string"], context.scene)
                        else:
                            self.report({'ERROR'}, "ERROR: Invalid frame ranges given.")
                            setRenderStatus("animation", "ERROR")
                            return{'FINISHED'}
                    setRenderStatus("animation", "Rendering...")
                    self.state += 1
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                elif(self.state == 3):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("animation", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 4):
                    print("Fetching render files...")
                    self.process = getFrames(context.scene)
                    self.state +=1
                    return{'PASS_THROUGH'}

                elif(self.state == 5):
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
        scn = context.scene

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

        # verify user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if scn.tempFilePath[-1] != "/":
            scn.tempFilePath = scn.tempFilePath + "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(event_timer_len, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        writeServersFile()
        self.startFrame = context.scene.frame_start
        self.endFrame   = context.scene.frame_end
        self.process    = cleanLocalDirectoryForRenderFrames(scn)
        self.state      = 1   # initializes state for modal

        self.report({'INFO'}, "Rendering animation on " + str(len(scn['availableServers'])) + " servers.")
        setRenderStatus("animation", "Preparing files...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

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

class drawRenderOnServersPanel(View3DPanel, Panel):
    bl_label    = "Render on Servers"
    bl_idname   = "VIEW3D_PT_tools_render_on_servers"
    bl_context  = "objectmode"
    bl_category = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine != 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label("Please switch to Cycles")
        else:
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

class drawSamplingPanel(View3DPanel, Panel):
    bl_label    = "Sampling (Single Frame)"
    bl_idname   = "VIEW3D_PT_sampling"
    bl_context  = "objectmode"
    bl_category = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def calcSamples(self, scn, squared, category, multiplier):
        if squared:
            category = category**2
        result = math.floor(multiplier*category*len(scn['availableServers']))
        return result

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
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
    # def menu_draw(self, context):
    #     layout = self.layout
    #     scn = context.scene
    #
    #     if scn.render.engine == 'CYCLES' and not scn.cycles.progressive == 'BRANCHED_PATH':
    #         # Basic Render Samples Info
    #         col = layout.column(align=True)
    #         row = col.row(align=True)
    #         sampleSize = scn.cycles.samples
    #         if(scn.cycles.use_square_samples):
    #             sampleSize = sampleSize**2
    #         if sampleSize < 10:
    #             row.label('Too few samples')
    #         else:
    #             row.label("Total Samples: " + str(math.floor(sampleSize*len(scn['availableServers']))))
    #
    # bpy.types.CyclesRender_PT_sampling.append(menu_draw)

class drawFrameRangePanel(View3DPanel, Panel):
    bl_label    = "Frame Range"
    bl_idname   = "VIEW3D_PT_frame_range"
    bl_context  = "objectmode"
    bl_category = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scn, "frameRanges")

class drawServersPanel(View3DPanel, Panel):
    bl_label    = "Servers"
    bl_idname   = "VIEW3D_PT_servers"
    bl_context  = "objectmode"
    bl_category = "Render"
    bl_options = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scn, "tempFilePath")
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("scene.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")
            row = col.row(align=True)
            row.operator("scene.commit_edits", text="Commit Edits", icon="FILE_REFRESH")

def more_menu_options(self, context):
    layout = self.layout
    layout.separator()

    layout.operator("sendFrameToRenderFarm", text="Render Image on Servers", icon='RENDER_STILL')
    layout.operator("sendAnimationToRenderFarm", text="Render Image on Servers", icon='RENDER_ANIMAITON')

# store keymaps here to access after registration
addon_keymaps = []

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_render.append(more_menu_options)

    # initialize check box for displaying render sampling details
    bpy.types.Scene.boolTool = BoolProperty(
        name="Show Details",
        description="Display details for render sample settings",
        default = False)

    # initialize frame range string text box
    bpy.types.Scene.frameRanges = StringProperty(
        name = "Frames")

    # initialize frame range string text box
    bpy.types.Scene.tempFilePath = StringProperty(
                        name = "Path",
                        description="File path on host server (temporary storage location)",
                        maxlen = 128,
                        default = "/tmp/renderFarm/")

    # initialize server groups enum property
    groupNames = [("All Servers","All Servers","Render on all servers")]
    for groupName in servers:
        junkList = [groupName,groupName,"Render only servers on this group"]
        groupNames.append(tuple(junkList))
    bpy.types.Scene.serverGroups = EnumProperty(
        attr="serverGroups",
        name="Servers",
        description="Choose which hosts to use for render processes",
        items=groupNames,
        default='All Servers')

    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new(sendFrameToRenderFarm.bl_idname, 'F12', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new(sendAnimationToRenderFarm.bl_idname, 'F12', 'PRESS', ctrl=True, shift=True)
    kmi = km.keymap_items.new(refreshNumAvailableServers.bl_idname, 'R', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new(editRemoteServersDict.bl_idname, 'E', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new(commitEdits.bl_idname, 'C', 'PRESS', ctrl=True, alt=True)
    addon_keymaps.append(km)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(more_menu_options)
    del bpy.types.Scene.boolTool
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.serverGroups

    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    # clear the list
    addon_keymaps.clear()

if __name__ == "__main__":
    register()

print("'sendToRenderFarm' Script Loaded")
