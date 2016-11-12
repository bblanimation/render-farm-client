#!/usr/bin/python
bl_info = {
    "name"        : "Server Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 4, 6),
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
renderStatus    = {"animation":"None", "image":"None"}
killingStatus   = "None"
projectPath     = ""
projectName     = ""
serverFilePath  = ""
dumpLocation    = ""
renderType      = []
frameRangesDict = {}
hostServer      = ""
servers         = ""
extension       = ""

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

def importServerFiles():
    global hostServer
    global servers
    global extension
    libraryServersPath = os.path.join(getLibraryPath(), "servers")

    hsFile = open(os.path.join(libraryServersPath, "hostServer.txt"),"r")
    rsFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    # TODO: Refactor the following lines of code.

    # skip lines leading up to '### BEGIN SERVERS DICTIONARY ###'
    nextLine = rsFile.readline()
    numIters = 0
    while(nextLine != "### BEGIN SERVERS DICTIONARY ###\n"):
        nextLine = rsFile.readline()
        numIters += 1
        if numIters >= 10:
            print("Sorry, you must have deleted the line containing the opening flag")
            break

    # read following lines leading up to '### END SERVERS DICTIONARY ###'
    nextLine = rsFile.readline()
    numIters = 0
    while(nextLine != "### END SERVERS DICTIONARY ###\n"):
        servers += nextLine.replace(" ", "").replace("\n", "")
        nextLine = rsFile.readline()
        numIters += 1
        if numIters >= 100:
            print("Sorry, you either deleted the line containing the ending flag, or there were over 100 new lines in your server declaration.")
            break

    servers = json.loads(servers.replace("\t", ""))

    # skip lines leading up to '### BEGIN EXTENSION ###'
    nextLine = rsFile.readline()
    numIters = 0
    while(nextLine != "### BEGIN EXTENSION ###\n"):
        nextLine = rsFile.readline()
        numIters += 1
        if numIters >= 10:
            print("Sorry, you must have deleted the line containing the opening flag")
            break

    # read following lines leading up to '### END EXTENSION ###'
    nextLine = rsFile.readline()
    numIters = 0
    while(nextLine != "### END EXTENSION ###\n"):
        extension += nextLine.replace(" ", "").replace("\n", "").replace("\"", "")
        nextLine = rsFile.readline()
        numIters += 1
        if numIters >= 100:
            print("Sorry, you either deleted the line containing the ending flag, or there were over 100 new lines in your server declaration.")
            break

    # skip lines leading up to '### BEGIN HOST SERVER STRING ###'
    nextLine = hsFile.readline()
    numIters = 0
    while(nextLine != "### BEGIN HOST SERVER STRING ###\n"):
        nextLine = hsFile.readline()
        numIters += 1
        if numIters >= 10:
            print("Sorry, you must have deleted the line containing the opening flag")
            break

    # read following lines leading up to '### END HOST SERVER STRING ###'
    nextLine = hsFile.readline()
    numIters = 0
    while(nextLine != "### END HOST SERVER STRING ###\n"):
        hostServer += nextLine.replace(" ", "").replace("\n", "").replace("\"", "")
        nextLine = hsFile.readline()
        numIters += 1
        if numIters >= 100:
            print("Sorry, you either deleted the line containing the ending flag, or there were over 100 new lines in your server declaration.")
            break

def main():
    getLibraryPath()
    importServerFiles()
main()

class View3DPanel():
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

def setGlobalProjectVars():
    global projectPath
    global projectName
    global serverFilePath
    global dumpLocation

    projectPath    = bpy.path.abspath("//")
    projectName    = bpy.path.display_name_from_filepath(bpy.data.filepath)
    serverFilePath = "/tmp/cgearhar/" + projectName + "/"
    dumpLocation   = projectPath + "render-dump/"
    print(projectPath)
    print(projectName)

def checkNumAvailServers(scn):
    bpy.types.Scene.availableServers = StringProperty(name = "Available Servers")
    bpy.types.Scene.offlineServers   = StringProperty(name = "Offline Servers")

    hosts       = []
    unreachable = []
    for groupName in servers:
        for host in servers[groupName]:
            try:
                tn = telnetlib.Telnet(host + extension,22,.4)
                hosts.append(host)
            except:
                unreachable.append(host)

    scn['availableServers'] = hosts
    scn['offlineServers']   = unreachable

    for a in bpy.context.screen.areas:
        a.tag_redraw()

    return

def jobIsValid(jobType, availableServers):
    if availableServers == 0:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: Unable to connect to remote servers."}
    elif projectName == "":
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: You have not saved your project file. Please save it before attempting to render."}
    elif " " in projectName:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER ABORTED: Please remove ' ' (spaces) from the project file name."}
    elif bpy.context.scene.camera is None:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: No camera in scene."}
    elif not bpy.context.scene.render.image_settings.color_mode == 'RGB':
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: Due to current lack of functionality, this script only runs with 'RGB' color mode."}
    elif not bpy.context.scene.cycles.progressive == 'BRANCHED_PATH':
        return {"valid":False, "errorType":"WARNING", "errorMessage":"RENDER ABORTED: Please use the 'Branched Path Tracing' sampling option for an accurate threaded render."}
    else:
        return {"valid":True, "errorType":None, "errorMessage":None}

def cleanLocalDirectoryForGetFrames():
    print("verifying local directory...")
    subprocess.call("mkdir -p " + dumpLocation + "backups/", shell=True)

    print("cleaning up local directory...")
    process = subprocess.Popen("rsync --remove-source-files --exclude='" + projectName + "_average.*' " + dumpLocation + "* " + dumpLocation + "backups/", stdout=subprocess.PIPE, shell=True)
    return process

def getFrames():
    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    print("copying files from server...\n")
    process = subprocess.Popen("rsync --remove-source-files --exclude='*.blend' '" + hostServer + ":" + serverFilePath + "*' '" + dumpLocation + "'", stdout=subprocess.PIPE, shell=True)
    return process

def averageFrames():
    process = subprocess.Popen("python ~/my_scripts/averageFrames.py " + projectPath + " " + projectName, stdout=subprocess.PIPE, shell=True)
    return process

def buildFrameRangesString(frameRanges):
    #frameRanges = "1,3,10-13, 20"
    frameRanges = frameRanges.replace(" ", "")
    #frameRanges = "1,3,10-13,20"
    frameRangeList = frameRanges.split(",")
    #frameRangeList = ["1","3","10-13","20"]
    newFrameRangeList = []
    for string in frameRangeList:
        try:
            newInt = int(string)
            if newInt not in newFrameRangeList:
                newFrameRangeList.append(newInt)
        except:
            if "-" in string:
                newString = string.split("-")
                if len(newString) > 2:
                    return { "valid":False, "string":None }
                try:
                    newInt1 = int(newString[0])
                    newInt2 = int(newString[1])
                    if newInt1 <= newInt2:
                        newFrameRangeList.append([newInt1,newInt2])
                    else:
                        return { "valid":False, "string":None }
                except:
                    return { "valid":False, "string":None }
            else:
                return { "valid":False, "string":None }
    return { "valid":True, "string":str(newFrameRangeList).replace(" ","") }

def cleanLocalDirectoryForRenderFrames():
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(copy=True)

    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    process = subprocess.Popen("rsync -a --copy-links --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServer + ":" + serverFilePath + "'", shell=True)
    return process

def renderFrames(frameRange):
    # run blender command to render given range from the remote server
    print("opening connection to " + hostServer + "...")
    process = subprocess.Popen("ssh " + hostServer + " 'nohup blender_task.py -n " + projectName + " -l " + frameRange + " &'", shell=True)
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
    process = subprocess.Popen("python ~/my_scripts/killAllBlender.py", stdout=subprocess.PIPE, shell=True)
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

                # start render process at current frame
                if(self.state == 1):
                    self.process = renderFrames("[" + str(self.curFrame) + "]")
                    self.state += 1
                    setRenderStatus("image", "Rendering...")
                    return{'PASS_THROUGH'}

                # prepare local dump location, and move previous files to backup subdirectory
                if(self.state == 2):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("image", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 3):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}

                # average the rendered frames
                elif(self.state == 4):
                    print("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}

                elif(self.state == 5):
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
        checkNumAvailServers(context.scene)

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("image", len(context.scene['availableServers']))
        if not jobValidityDict["valid"]:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
            return{'FINISHED'}

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        # start initial render process
        self.curFrame = context.scene.frame_current
        self.process = cleanLocalDirectoryForRenderFrames()
        self.state   = 1  # initializes state for modal

        self.report({'INFO'}, "Rendering current frame on " + str(len(context.scene['availableServers'])) + " servers.")
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

                # start render process from the defined start and end frames
                if(self.state == 1):
                    if scn.frameRanges == "":
                        self.process = renderFrames("[" + str(self.startFrame) + "-" + str(self.endFrame) + "]")
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
                if(self.state == 2):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    setRenderStatus("animation", "Finishing...")
                    return{'PASS_THROUGH'}

                # get rendered frames from remote servers
                elif(self.state == 3):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state +=1
                    return{'PASS_THROUGH'}

                elif(self.state == 4):
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
        checkNumAvailServers(context.scene)

        # ensure the job won't break the script
        jobValidityDict = jobIsValid("animation", len(context.scene['availableServers']))
        if not jobValidityDict["valid"]:
            self.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
            return{'FINISHED'}

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
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

    def execute(self, context):
        cleanLocalDirectoryForGetFrames()
        getFrames()
        return{'FINISHED'}

class averageRenderedFrames(Operator):
    """Average pixels in rendered frames"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.average_frames"                     # unique identifier for buttons and menu items to reference.
    bl_label   = "Average Rendered Frames"                  # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.

    def execute(self, context):
        averageFrames()
        return{'FINISHED'}

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
        print(image_filename)
        bpy.ops.clip.open(directory=image_sequence_filepath, files=[{"name":image_filename}])

        return{'FINISHED'}

class editRemoteServersDict(Operator):
    """Edit the remote servers dictionary in a text editor"""                       # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.edit_servers_dict"                                          # unique identifier for buttons and menu items to reference.
    bl_label   = "Edit Remote Servers"                                              # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                               # enable undo for the operator.

    def execute(self, context):
        context.area.type = 'TEXT_EDITOR'
        libraryServersPath = os.path.join(getLibraryPath(), "servers")
        bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "remoteServers.txt"))
        return{'FINISHED'}

class editHostServer(Operator):
    """Change the external host server in a text editor"""   # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.edit_host_server_string"             # unique identifier for buttons and menu items to reference.
    bl_label   = "Edit Host Server"                          # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                        # enable undo for the operator.

    def execute(self, context):
        context.area.type = 'TEXT_EDITOR'
        libraryServersPath = os.path.join(getLibraryPath(), "servers")
        bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "hostServer.txt"))
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
        self._timer = wm.event_timer_add(0.1, context.window)
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


    my_bool = BoolProperty(
        name="Enable or Disable",
        description="Display details for final calculated render samples",
        default = False
        )

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

        # Render Status Info
        if(imRenderStatus != "None" and animRenderStatus != "None"):
            row = col.row(align=True)
            row.label('Render Status (cf): ' + imRenderStatus)
            row = col.row(align=True)
            row.label('Render Status (a):  ' + animRenderStatus)
        elif(imRenderStatus != "None"):
            row = col.row(align=True)
            row.label('Render Status: ' + imRenderStatus)
        elif(animRenderStatus != "None"):
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
    bl_label    = "Sampling"
    bl_idname   = "VIEW3D_PT_sampling"
    bl_context  = "objectmode"
    bl_category = "Render"

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
            if sampleSize < 8:
                row.label('Samples: Too few samples')
            else:
                row.label("Samples: " + str(math.floor(sampleSize*len(scn['availableServers']) * 2 / 3)) + " (Switch to 'Branched Path Tracing')")
        else:
            # find AA sample size first (this affects other sample sizes)
            aaSampleSize = scn.cycles.aa_samples
            squared = False
            if(scn.cycles.use_square_samples):
                squared = True
                aaSampleSize = aaSampleSize**2

            # Show/Hide Details Checkbox
            #row.prop(scn, "boolTool")

            # Shown/Hidden Details
            #if(scn.boolTool):
            if(squared):
                aa    = math.floor(aaSampleSize*len(scn['availableServers']) * 2 / 3)
                diff  = math.floor(aaSampleSize*(scn.cycles.diffuse_samples**2)*len(scn['availableServers']) * 2 / 3)
                glos  = math.floor(aaSampleSize*(scn.cycles.glossy_samples**2)*len(scn['availableServers']) * 2 / 3)
                tran  = math.floor(aaSampleSize*(scn.cycles.transmission_samples**2)*len(scn['availableServers']) * 2 / 3)
                ao    = math.floor(aaSampleSize*(scn.cycles.ao_samples**2)*len(scn['availableServers']) * 2 / 3)
                meshL = math.floor(aaSampleSize*(scn.cycles.mesh_light_samples**2)*len(scn['availableServers']) * 2 / 3)
                sub   = math.floor(aaSampleSize*(scn.cycles.subsurface_samples**2)*len(scn['availableServers']) * 2 / 3)
                vol   = math.floor(aaSampleSize*(scn.cycles.volume_samples**2)*len(scn['availableServers']) * 2 / 3)
            else:
                aa    = math.floor(aaSampleSize*len(scn['availableServers']) * 2 / 3)
                diff  = math.floor(aaSampleSize*(scn.cycles.diffuse_samples)*len(scn['availableServers']) * 2 / 3)
                glos  = math.floor(aaSampleSize*(scn.cycles.glossy_samples)*len(scn['availableServers']) * 2 / 3)
                tran  = math.floor(aaSampleSize*(scn.cycles.transmission_samples)*len(scn['availableServers']) * 2 / 3)
                ao    = math.floor(aaSampleSize*(scn.cycles.ao_samples)*len(scn['availableServers']) * 2 / 3)
                meshL = math.floor(aaSampleSize*(scn.cycles.mesh_light_samples)*len(scn['availableServers']) * 2 / 3)
                sub   = math.floor(aaSampleSize*(scn.cycles.subsurface_samples)*len(scn['availableServers']) * 2 / 3)
                vol   = math.floor(aaSampleSize*(scn.cycles.volume_samples)*len(scn['availableServers']) * 2 / 3)

            row = col.row(align=True)
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
        row.operator("scene.edit_host_server_string", text="Edit Host Server", icon="TEXT")
        row = col.row(align=True)
        row.operator("scene.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")

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
        col.alignment = 'EXPAND'
        row = col.row(align=True)
        row.active = len(scn['availableServers']) > 0
        row.operator("scene.get_rendered_frames", text="Get Frames", icon="EXTERNAL_DATA")
        row.operator("scene.average_frames", text="Average Frames", icon="SEQ_CHROMA_SCOPE")

        row.separator()

        row = col.row(align=True)
        row.active = len(scn['availableServers']) > 0
        row.operator("scene.kill_blender", text="Kill All Blender Processes", icon="CANCEL")

        # Killall Blender Status
        if(killingStatus != "None"):
            row = col.row(align=True)
            if killingStatus == "Finished":
                row.label('<placeholder> Blender processes killed!')
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

    # initialize host server string text box
    bpy.types.Scene.hostServer = StringProperty(
        name = "Host Server")

    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.boolTool
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.hostServer

if __name__ == "__main__":
    register()

print("'sendToRenderFarm' Script Loaded")
