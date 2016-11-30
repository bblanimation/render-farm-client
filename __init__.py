#!/usr/bin/python
bl_info = {
    "name"        : "Server Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 6, 2),
    "blender"     : (2, 78, 0),
    "description" : "Render your scene on a remote server farm with this addon.",
    "location"    : "View3D > Tools > Render",
    "warning"     : "Relatively stable but still work in progress",
    "wiki_url"    : "",
    "tracker_url" : "",
    "category"    : "Render"}

import bpy, subprocess, os, time, json
from bpy.types import Operator
from bpy.props import *
from . import ui

hostServerLogin = ""
servers         = ""

def getLibraryPath():
    # Full path to "\addons\server_farm_client\" -directory
    paths = bpy.utils.script_paths("addons")

    libraryPath = 'assets'
    for path in paths:
        libraryPath = os.path.join(path, "server_farm_client_add_on")
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

def setupServerVars():
    # Variable definitions
    libraryServersPath = os.path.join(getLibraryPath(), "servers")
    serverFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    # Set SSH login information for host server
    global hostServerLogin
    username    = readFileFor(serverFile, "SSH USERNAME").replace("\"", "")
    hostServer  = readFileFor(serverFile, "HOST SERVER").replace("\"", "")
    extension   = readFileFor(serverFile, "EXTENSION").replace("\"", "")
    hostServerLogin = username + "@" + hostServer + extension

    # Set server dictionary
    global servers
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))

# Initialize server and hostServerLogin variables
setupServerVars()

def jobIsValid(jobType, projectName):
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

def cleanLocalDirectoryForGetFrames(projectName):
    dumpLocation = bpy.path.abspath("//") + "render-dump/"

    print("verifying local directory...")
    mkdirCommand = "mkdir -p " + dumpLocation + "backups/"
    subprocess.call(mkdirCommand, shell=True)

    print("cleaning up local directory...")
    rsyncCommand = "rsync --remove-source-files --exclude='" + projectName + "_average.*' " + dumpLocation + "* " + dumpLocation + "backups/"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def getFrames(projectName):
    dumpLocation = bpy.path.abspath("//") + "render-dump/"
    scn = bpy.context.scene

    print("copying files from server...\n")
    rsyncCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + projectName + "/;'; rsync --remove-source-files --exclude='*.blend' '" + hostServerLogin + ":" + scn.tempFilePath + projectName + "/results/*' '" + dumpLocation + "'"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
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

def cleanLocalDirectoryForRenderFrames(projectName):
    scn = bpy.context.scene
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(copy=True)

    print("verifying remote directory...")
    sshCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + projectName + "/toRemote/'"
    subprocess.call(sshCommand, shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    rsyncCommand = "rsync --copy-links -rqa --include=" + projectName + ".blend --exclude='*' '" + bpy.path.abspath("//") + "' '" + hostServerLogin + ":" + scn.tempFilePath + projectName + "/toRemote/'"
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def copyFiles():
    scn = bpy.context.scene
    rsyncCommand = "ssh " + hostServerLogin + " 'mkdir -p " + scn.tempFilePath + "'; rsync -a '" + os.path.join(getLibraryPath(), "to_host_server") + "/' '" + hostServerLogin + ":" + scn.tempFilePath + "'"
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def writeServersFile(serverDict):
    f = open(os.path.join(getLibraryPath(), "to_host_server", "servers.txt"), "w")
    # define serversToUse
    scn = bpy.context.scene
    if(scn.serverGroups == "All Servers"):
        serversToUse = serverDict
    else:
        serversToUse = {}
        serversToUse[scn.serverGroups] = serverDict[scn.serverGroups]
    f.write("### BEGIN REMOTE SERVERS DICTIONARY ###\n")
    f.write(str(serversToUse).replace("'", "\"") + "\n")
    f.write("### END REMOTE SERVERS DICTIONARY ###\n")

def renderFrames(frameRange, projectName):
    scn = bpy.context.scene
    # run blender command to render given range from the remote server
    renderCommand = "ssh " + hostServerLogin + " 'python " + scn.tempFilePath + "blender_task.py -p -n " + projectName + " -l " + frameRange + " --hosts_file " + scn.tempFilePath + "servers.txt --local_sync " + scn.tempFilePath + projectName + "/toRemote/'"
    process = subprocess.Popen(renderCommand, shell=True)
    print("Process sent to remote servers!\n")
    return process

def setRenderStatus(key, status):
    bpy.context.scene.renderStatus[key] = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getRenderStatus(key):
    return bpy.context.scene.renderStatus[key]

def appendViewable(typeOfRender):
    scn = bpy.context.scene
    if(typeOfRender not in scn.renderType):
        scn.renderType.append(typeOfRender)

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers through host server""" # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.refresh_num_available_servers"          # unique identifier for buttons and menu items to reference.
    bl_label   = "Refresh Available Servers"                    # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                           # enable undo for the operator.

    def checkNumAvailServers(self):
        scn = bpy.context.scene
        command = "ssh " + hostServerLogin + " 'python " + scn.tempFilePath + "blender_task.py -H --hosts_file " + scn.tempFilePath + "servers.txt'"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        #process = subprocess.Popen(command, shell=True)
        return process

    def updateAvailServerInfo(self):
        scn = bpy.context.scene

        line1 = self.process.stdout.readline().decode('ASCII').replace("\\n", "")
        line2 = self.process.stdout.readline().decode('ASCII').replace("\\n", "")
        available = json.loads(line1.replace("'", "\""))
        offline = json.loads(line2.replace("'", "\""))

        bpy.types.Scene.availableServers = StringProperty(name = "Available Servers")
        bpy.types.Scene.offlineServers = StringProperty(name = "Offline Servers")

        scn['availableServers'] = available
        scn['offlineServers'] = offline
        for a in bpy.context.screen.areas:
            a.tag_redraw()

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
                    self.process = self.checkNumAvailServers()
                    self.state += 1
                    return{'PASS_THROUGH'}

                elif(self.state == 2):
                    self.updateAvailServerInfo()
                    self.report({'INFO'}, "Refresh process completed")
                    return{'FINISHED'}
                else:
                    self.report({'ERROR'}, "ERROR: Current state not recognized.")
                    return{'FINISHED'}

        return{'PASS_THROUGH'}

    def execute(self, context):
        writeServersFile(servers)

        # verify user input for tempFilePath string
        scn = context.scene
        scn.tempFilePath.replace(" ", "_")
        if scn.tempFilePath[-1] != "/":
            scn.tempFilePath = scn.tempFilePath + "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial process
        print("Copying project files...")
        self.process = copyFiles()
        self.state   = 1  # initializes state for modal

        self.report({'INFO'}, "Refreshing available servers...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class sendFrame(Operator):
    """Render current frame on remote servers"""            # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_frame_on_servers"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Current Frame"                     # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.


    def averageFrames(self):
        averageScriptPath = os.path.join(getLibraryPath(), "scripts", "averageFrames.py")
        runScriptCommand = "python " + averageScriptPath.replace(" ", "\\ ") + " -p " + bpy.path.abspath("//") + " -n " + self.projectName
        process = subprocess.Popen(runScriptCommand, shell=True)
        return process

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
                    self.process = copyFiles()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process at current frame
                elif(self.state == 2):
                    self.process = renderFrames("[" + str(self.curFrame) + "]", self.projectName)
                    self.state += 1
                    setRenderStatus("image", "Rendering...")
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                elif(self.state == 3):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames(self.projectName)
                    self.state += 1
                    setRenderStatus("image", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 4):
                    print("Fetching render files...")
                    self.process = getFrames(self.projectName)
                    self.state += 1
                    return{'PASS_THROUGH'}

                # average the rendered frames
                elif(self.state == 5):
                    print("Averaging frames...")
                    self.process = self.averageFrames()
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
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        scn = context.scene

        # ensure no other image render processes are running
        if(getRenderStatus("image") in ["Rendering...", "Preparing files..."]):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("image", self.projectName)
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
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        writeServersFile(servers)
        self.curFrame = context.scene.frame_current
        self.process = cleanLocalDirectoryForRenderFrames(self.projectName)
        self.state   = 1  # initializes state for modal

        setRenderStatus("image", "Preparing files...")

        return{'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class sendAnimation(Operator):
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
                    self.process = copyFiles()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # start render process from the defined start and end frames
                elif(self.state == 2):
                    if scn.frameRanges == "":
                        self.process = renderFrames("[[" + str(self.startFrame) + "," + str(self.endFrame) + "]]", self.projectName)
                    else:
                        self.frameRangesDict = buildFrameRangesString(scn.frameRanges)
                        if(self.frameRangesDict["valid"]):
                            self.process = renderFrames(self.frameRangesDict["string"], self.projectName)
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
                    self.process = cleanLocalDirectoryForGetFrames(self.projectName)
                    self.state += 1
                    setRenderStatus("animation", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 4):
                    print("Fetching render files...")
                    self.process = getFrames(self.projectName)
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
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        scn = context.scene

        if(getRenderStatus("animation") in ["Rendering...","Preparing files..."]):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("animation", self.projectName)
        if not jobValidityDict["valid"]:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
            return{'FINISHED'}

        # verify user input for tempFilePath string
        scn.tempFilePath.replace(" ", "_")
        if scn.tempFilePath[-1] != "/":
            scn.tempFilePath = scn.tempFilePath + "/"

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        writeServersFile(servers)
        self.startFrame = context.scene.frame_start
        self.endFrame   = context.scene.frame_end
        self.process    = cleanLocalDirectoryForRenderFrames(self.projectName)
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
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        # open rendered image
        context.area.type = 'IMAGE_EDITOR'
        averaged_image_filepath = bpy.path.abspath("//") + "render-dump/" + self.projectName + "_average.tga"
        bpy.ops.image.open(filepath=averaged_image_filepath)
        bpy.ops.image.reload()

        return{'FINISHED'}

class openRenderedAnimationInUI(Operator):
    """Open rendered animation"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.open_rendered_animation"  # unique identifier for buttons and menu items to reference.
    bl_label   = "Open Rendered Animation"        # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}             # enable undo for the operator.


    def execute(self, context):
        self.frameRangesDict = buildFrameRangesString(context.scene.frameRanges)
        self.projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        # open rendered image
        context.area.type = 'CLIP_EDITOR'
        image_sequence_filepath = bpy.path.abspath("//") + "render-dump/"
        if context.scene.frameRanges == "":
            fs = context.scene.frame_start
        else:
            if self.frameRangesDict["valid"]:
                fr = json.loads(self.frameRangesDict["string"])[0]
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

        image_filename = self.projectName + "_" + fs + ".tga"
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
        setupServerVars()
        print("Edits committed")
        self.report({'INFO'}, "Edits committed")
        return{'FINISHED'}

def more_menu_options(self, context):
    layout = self.layout
    layout.separator()

    layout.operator("sendFrame", text="Render Image on Servers", icon='RENDER_STILL')
    layout.operator("sendAnimation", text="Render Image on Servers", icon='RENDER_ANIMAITON')

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

    bpy.types.Scene.renderType = []
    bpy.types.Scene.renderStatus = {"animation":"None", "image":"None"}

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
    kmi = km.keymap_items.new("scene.render_frame_on_servers", 'F12', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new("scene.render_animation_on_servers", 'F12', 'PRESS', ctrl=True, shift=True)
    kmi = km.keymap_items.new("scene.refresh_num_available_servers", 'R', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new("scene.edit_servers_dict", 'E', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new("scene.commit_edits", 'C', 'PRESS', ctrl=True, alt=True)
    addon_keymaps.append(km)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(more_menu_options)
    del bpy.types.Scene.boolTool
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.tempFilePath
    del bpy.types.Scene.renderType
    del bpy.types.Scene.renderStatus
    del bpy.types.Scene.serverGroups

    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    # clear the list
    addon_keymaps.clear()

if __name__ == "__main__":
    register()

print("'server_farm_client_add_on' Script Loaded")
