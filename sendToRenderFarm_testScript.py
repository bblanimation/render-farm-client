import bpy, subprocess, telnetlib, sys, os, numpy, time, json, math
from bpy.types import (Menu, Panel, UIList, Operator, AddonPreferences, PropertyGroup)
from bpy.props import *

renderStatus   = {"animation":"None", "image":"None"}
killingStatus  = "None"
projectPath    = bpy.path.abspath("//")
projectName    = bpy.path.display_name_from_filepath(bpy.data.filepath)
hostServer     = "cgearhar@asahel.cse.taylor.edu"
serverFilePath = "/tmp/cgearhar/" + projectName + "/"
dumpLocation   = projectPath + "render-dump/"
renderType     = []
servers = {'cse21801group':    ['cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807',
                                'cse21808','cse21809','cse21810','cse21811','cse21812','cse21701','cse21702',
                                'cse21703','cse21704','cse21705','cse21706','cse21707','cse21708','cse21709',
                                'cse21710','cse21711','cse21712','cse21713','cse21714','cse21715','cse21716',
                                'cse10301','cse10302','cse10303','cse10304','cse10305','cse10306','cse10307',
                                'cse10309','cse10310','cse10311','cse10312','cse10315','cse10316','cse10317',
                                'cse10318','cse10319','cse103podium',
                                'cse20101','cse20102','cse20103','cse20104','cse20105','cse20106','cse20107',
                                'cse20108','cse20109','cse20110','cse20111','cse20112','cse20113','cse20114',
                                'cse20116','cse20117','cse20118','cse20119','cse20120','cse20121','cse20122',
                                'cse20123','cse20124','cse20125','cse20126','cse20127','cse20128','cse20129',
                                'cse20130','cse20131','cse20132','cse20133','cse20134','cse20135','cse20136'
                                ]}

class View3DPanel():
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

def checkNumAvailServers(scn):
    global availableServers

    bpy.types.Scene.availableServers   = StringProperty(
        name = "Available Servers")
    bpy.types.Scene.offlineServers = StringProperty(
        name = "Offline Servers")

    hosts       = []
    unreachable = []
    for hostGroupName in servers:
        for host in servers[hostGroupName]:
            try:
                tn = telnetlib.Telnet(host + ".cse.taylor.edu",22,.4)
                hosts.append(host)
            except:
                unreachable.append(host)

    scn['availableServers'] = hosts
    scn['offlineServers']   = unreachable

    return

checkNumAvailServers(bpy.context.scene)

def jobIsValid():
    if projectName == "":
        self.report({'ERROR'}, "RENDER FAILED: You have not saved your project file. Please save it before attempting to render.")
        setRenderStatus("Failed")
        return False
    elif bpy.context.scene.camera is None:
        self.report({'ERROR'}, "RENDER FAILED: No camera in scene.")
        setRenderStatus("Failed")
        return False
    elif not bpy.context.scene.render.image_settings.color_mode == 'RGB':
        self.report({'ERROR'}, "RENDER FAILED: Due to current lack of functionality, this script only runs with 'RGB' color mode.")
        setRenderStatus("Failed")
        return False
    elif not bpy.context.scene.cycles.progressive == 'BRANCHED_PATH':
        self.report({'WARNING'}, "RENDER ABORTED: Please use the 'Branched Path Tracing' sampling option for an accurate threaded render.")
        setRenderStatus("Failed")
        return False
    else:
        return True

def cleanLocalDirectoryForGetFrames():
    print("verifying local directory...")
    subprocess.call("mkdir -p " + dumpLocation + "backups/", shell=True)

    print("cleaning up local directory...")
    process = subprocess.Popen("rsync --remove-source-files --exclude='" + projectName + "_average.*'" + dumpLocation + "* " + dumpLocation + "backups/", stdout=subprocess.PIPE, shell=True)
    return process

def getFrames():
    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    print("copying files from server...\n")
    process = subprocess.Popen("rsync --exclude='*.blend' '" + hostServer + ":" + serverFilePath + "*' '" + dumpLocation + "'", stdout=subprocess.PIPE, shell=True)
    return process

def averageFrames():
    process = subprocess.Popen("python ~/my_scripts/averageFrames.py " + projectPath + " " + projectName, stdout=subprocess.PIPE, shell=True)
    return process
   
def renderFrames(startFrame, endFrame):
    bpy.ops.wm.save_as_mainfile(copy=True)
    
    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    subprocess.call("rsync -a --copy-links --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServer + ":" + serverFilePath + "'", shell=True)

    # run blender command to render given range from the remote server
    print("opening connection to " + hostServer + "...")
    process = subprocess.Popen("ssh " + hostServer + " 'nohup blender_task.py -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)
    # To see output from 'blender_task.py', uncomment the following line and comment out the line above.
    #subprocess.call("ssh " + hostServer + " 'nohup blender_task.py -p -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)
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

def appendViewable(typeOfRender):
    global renderType
    if(typeOfRender not in renderType):
        renderType.append(typeOfRender)

def setGlobalProjectVars():
    global projectName
    global serverFilePath
    projectName    = bpy.path.display_name_from_filepath(bpy.data.filepath)
    serverFilePath = "/tmp/cgearhar/" + projectName + "/"

def killAllBlender():
    setKillingStatus("running...")
    process = subprocess.Popen("python ~/my_scripts/killAllBlender.py", stdout=subprocess.PIPE, shell=True)
    return process

class refreshNumAvailableServers(bpy.types.Operator):
    """Refresh number of available servers"""           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.refresh_num_available_servers"  # unique identifier for buttons and menu items to reference.
    bl_label   = "Refresh number of available servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        process = checkNumAvailServers(bpy.context.scene)
        return {'FINISHED'}

class sendAnimationToRenderFarm(bpy.types.Operator):
    """Render animation on remote servers"""            # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_animation_on_servers"    # unique identifier for buttons and menu items to reference.
    bl_label   = "Render animation on remote servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def modal(self, context, event):
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
                
                # prepare local dump location, and move previous files to backup subdirectory
                if(self.state == 1):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                # get rendered frames from remote servers
                elif(self.state == 2):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state +=1
                    return{'PASS_THROUGH'}
                
                elif(self.state == 3):
                    self.report({'INFO'}, "Render completed! View the rendered animation in '//render/'")
                    setRenderStatus("animation", "Complete!")
                    appendViewable("animation")
                    return{'FINISHED'}
                else:
                    self.report({'ERROR'}, "ERROR: Current state not recognized.")
                    setRenderStatus("animation", "ERROR")
                    return{'FINISHED'}
        
        return{'PASS_THROUGH'}

    def execute(self, context):
        if(getRenderStatus("animation") == "Rendering..."):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}

        setGlobalProjectVars()
        
        # ensure the job won't break the script
        if not jobIsValid():
            return{'FINISHED'}
 
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        
        # start render process at the defined start and end frames
        startFrame = bpy.context.scene.frame_start
        endFrame   = bpy.context.scene.frame_end
        self.process = renderFrames(startFrame, endFrame)
        self.state   = 1   # initializes state for modal
        
        self.report({'INFO'}, "Rendering animation on " + str(len(context.scene['availableServers'])) + " servers.")
        setRenderStatus("animation", "Rendering...")

        return{'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class sendFrameToRenderFarm(bpy.types.Operator):
    """Render current frame on remote servers"""            # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_frame_on_servers"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render current frame on remote servers"   # display name in the interface.
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
                
                # prepare local dump location, and move previous files to backup subdirectory
                if(self.state == 1):
                    print("Preparing local directory...")
                    self.process = cleanLocalDirectoryForGetFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                # get rendered frames from remote servers
                elif(self.state == 2):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                # average the rendered frames
                elif(self.state == 3):
                    print("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                elif(self.state == 4):
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
        if(getRenderStatus("image") == "Rendering..."):
            self.report({'WARNING'}, "Render in progress...")
            return{'FINISHED'}
        setGlobalProjectVars()
        
        # ensure the job won't break the script
        if not jobIsValid():
            return{'FINISHED'}
 
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        
        # start render process at current frame and initialize state
        curFrame = bpy.context.scene.frame_current
        self.process = renderFrames(curFrame, curFrame)
        self.state   = 1
        
        self.report({'INFO'}, "Rendering current frame on " + str(len(context.scene['availableServers'])) + " servers.")
        setRenderStatus("image", "Rendering...")

        return{'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()

class getRenderedFrames(bpy.types.Operator):
    """Get Rendered Frames"""                           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.get_rendered_frames"            # unique identifier for buttons and menu items to reference.
    bl_label   = "render animation on remote servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        getFrames()
        return{'FINISHED'}

class averageRenderedFrames(bpy.types.Operator):
    """Average Rendered Frames"""                           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.average_frames"                     # unique identifier for buttons and menu items to reference.
    bl_label   = "Render current frame on remote servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.

    def execute(self, context):
        averageFrames()
        return{'FINISHED'}

class openRenderedImageInUI(bpy.types.Operator):
    """Average Rendered Frames"""                                       # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.open_rendered_image"                            # unique identifier for buttons and menu items to reference.
    bl_label   = "Open the average rendered frame in the Blender UI"    # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                   # enable undo for the operator.
    
    def execute(self, context):
        # change context for bpy.ops.image
        area = bpy.context.area
        old_type = area.type
        area.type = 'IMAGE_EDITOR'
                
        # open rendered image
        averaged_image_filepath = projectPath + "render-dump/" + projectName + "_average.tga"
        bpy.ops.image.open(filepath=averaged_image_filepath)
        
        return{'FINISHED'}
    
class openRenderedAnimationInUI(bpy.types.Operator):
    """Average Rendered Animation"""                                    # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.open_rendered_animation"                        # unique identifier for buttons and menu items to reference.
    bl_label   = "Open the rendered animation in image sequence node and display in Blender's UI" # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                                   # enable undo for the operator.
    
    def execute(self, context):
        # create image node and import all pngs in sequence
        # set the node to an image sequence
        # ???
        
        # change context for bpy.ops.image
        area = bpy.context.area
        old_type = area.type
        area.type = 'IMAGE_EDITOR'
        
        self.report({'WARNING'}, "'Open Rendered Animation' functionality currently not supported")
                
        # open rendered image
        # averaged_image_filepath = projectPath + "render-dump/" + projectName + "_average.tga"
        # bpy.ops.image.open(filepath=averaged_image_filepath)
        
        return{'FINISHED'}

class killBlender(bpy.types.Operator):
    """Kill all blender processes on all remote servers"""              # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.kill_blender"                                   # unique identifier for buttons and menu items to reference.
    bl_label   = "Kill all blender processes on all remote servers"     # display name in the interface.
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

class renderPanelLayout(View3DPanel, Panel):
    bl_label    = "Send to Servers"
    bl_idname   = "VIEW3D_PT_tools_send_to_servers"
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
        row = layout.row(align=True)
        row.label('Available Servers: ' + str(len(scn['availableServers'])) + " / " + str(len(scn['availableServers']) + len(scn['offlineServers'])))
        row.operator("scene.refresh_num_available_servers", text="", icon="FILE_REFRESH")

        # Render Buttons
        col = layout.column(align=True)
        row = col.row(align=True)
        row.alignment = 'EXPAND'
        row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
        row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")
 
        # Basic Render Samples Info
        col = layout.column(align=True)
        row = col.row(align=True)
        aaSampleSize = scn.cycles.aa_samples
        squared = False
        if(scn.cycles.use_square_samples):
            squared = True
            aaSampleSize = aaSampleSize**2
        row.label('AA Samples: ' + str(math.floor(aaSampleSize*len(scn['availableServers']) * 2 / 3)))
        
        # Show/Hide Details Checkbox
        row.prop(scn, "boolTool")
        
        # Shown/Hidden Details
        if(scn.boolTool):
            if(squared):
                diff  = math.floor(aaSampleSize*(scn.cycles.diffuse_samples**2)*len(scn['availableServers']) * 2 / 3)
                glos  = math.floor(aaSampleSize*(scn.cycles.glossy_samples**2)*len(scn['availableServers']) * 2 / 3)
                tran  = math.floor(aaSampleSize*(scn.cycles.transmission_samples**2)*len(scn['availableServers']) * 2 / 3)
                ao    = math.floor(aaSampleSize*(scn.cycles.ao_samples**2)*len(scn['availableServers']) * 2 / 3)
                meshL = math.floor(aaSampleSize*(scn.cycles.mesh_light_samples**2)*len(scn['availableServers']) * 2 / 3)
                sub   = math.floor(aaSampleSize*(scn.cycles.subsurface_samples**2)*len(scn['availableServers']) * 2 / 3)
                vol   = math.floor(aaSampleSize*(scn.cycles.volume_samples**2)*len(scn['availableServers']) * 2 / 3)
            else:
                diff  = math.floor(aaSampleSize*(scn.cycles.diffuse_samples)*len(scn['availableServers']) * 2 / 3)
                glos  = math.floor(aaSampleSize*(scn.cycles.glossy_samples)*len(scn['availableServers']) * 2 / 3)
                tran  = math.floor(aaSampleSize*(scn.cycles.transmission_samples)*len(scn['availableServers']) * 2 / 3)
                ao    = math.floor(aaSampleSize*(scn.cycles.ao_samples)*len(scn['availableServers']) * 2 / 3)
                meshL = math.floor(aaSampleSize*(scn.cycles.mesh_light_samples)*len(scn['availableServers']) * 2 / 3)
                sub   = math.floor(aaSampleSize*(scn.cycles.subsurface_samples)*len(scn['availableServers']) * 2 / 3)
                vol   = math.floor(aaSampleSize*(scn.cycles.volume_samples)*len(scn['availableServers']) * 2 / 3)
            row = col.row(align=True)    
            row.label('• Diffuse: ' + str(diff))
            row = col.row(align=True)
            row.label('• Glossy: ' + str(glos))
            row = col.row(align=True)
            row.label('• Transmission: ' + str(tran))
            row = col.row(align=True)
            row.label('• AO: ' + str(ao))
            row = col.row(align=True)
            row.label('• Mesh Light: ' + str(meshL))
            row = col.row(align=True)
            row.label('• Subsurface: ' + str(sub))
            row = col.row(align=True)
            row.label('• Volume: ' + str(vol))

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
            layout.separator()
            row = col.row(align=True)
            row.label('Render Status: ' + animRenderStatus)
        

        # display buttons to view render(s)
        row = layout.row(align=True)
        if   "image"   in renderType:
            row.operator("scene.open_rendered_image", text="View Image", icon="FILE_IMAGE")
        if "animation" in renderType:
            row.operator("scene.open_rendered_animation", text="View Animation", icon="FILE_MOVIE")

class renderPanelLayout(View3DPanel, Panel):
    bl_label    = "Admin Options"
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
        row = col.row(align=True)
        row.alignment = 'EXPAND'
        row.operator("scene.kill_blender", text="Kill All Blender Processes", icon="CANCEL")
        
        # Killall Blender Status
        if(killingStatus != "None"):
            row = col.row(align=True)
            if killingStatus == "Finished":
                row.label('<placeholder> Blender processes killed!')
            else:
                row.label('Killing blender on remote servers...')
        
def register():
    bpy.types.Scene.boolTool = bpy.props.BoolProperty(
        name="Show Details",
        description="Display details for render sample settings",
        default = False)
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.boolTool

if __name__ == "__main__":
    register()

print("Render Farm Loaded")
