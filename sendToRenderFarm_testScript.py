import bpy, subprocess, telnetlib, sys, os, numpy, time, json
from bpy.types import Menu, Panel, UIList
from bpy.props import *

renderStatus   = "None"
projectPath    = bpy.path.abspath("//")
projectName    = bpy.path.display_name_from_filepath(bpy.data.filepath)
hostServer     = "cgearhar@asahel.cse.taylor.edu"
serverFilePath = "/tmp/cgearhar/" + projectName + "/"
dumpLocation   = projectPath + "render-dump/"
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
                tn = telnetlib.Telnet(host + ".cse.taylor.edu",22,.5)
                hosts.append(host)
            except:
                unreachable.append(host)

    scn['availableServers']   = hosts
    scn['offlineServers'] = unreachable

    return

checkNumAvailServers(bpy.context.scene)

def getFrames():
    print("Getting frames...")

    print("verifying local directory...")
    subprocess.call("mkdir -p " + dumpLocation + "backups/", shell=True)

    print("cleaning up local directory...")
    subprocess.call("rsync --remove-source-files " + dumpLocation + "* " + dumpLocation + "backups/",shell=True)

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
    process = subprocess.Popen("ssh " + hostServer + " 'nohup blender_task.py -p -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)
    # To see output from 'blender_task.py', uncomment the following line and comment out the line above.
    #subprocess.call("ssh " + hostServer + " 'nohup blender_task.py -p -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)
    print("Process sent to remote servers!\n")
    
    return process

def setRenderStatus(status):
    global renderStatus
    renderStatus = status

def getRenderStatus():
    return renderStatus

class refreshNumAvailableServers(bpy.types.Operator):
    """Send to Render Farm"""                           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.refresh_num_available_servers"    # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Animation on Remote Servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        checkNumAvailServers(bpy.context.scene)
        return {'FINISHED'}

class sendAnimationToRenderFarm(bpy.types.Operator):
    """Send to Render Farm"""                           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_animation_on_servers"    # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Animation on Remote Servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        startFrame = bpy.data.scenes["Scene"].frame_start
        endFrame   = bpy.data.scenes["Scene"].frame_end

        renderFrames(startFrame, endFrame)

        return{'FINISHED'}

class sendFrameToRenderFarm(bpy.types.Operator):
    """Send to Render Farm"""                               # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.render_frame_on_servers"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Current Frame on Remote Servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Render process cancelled")
            print("Process cancelled")
            setRenderStatus("Cancelled")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()            
                
            if self.process.returncode != None:
                print("Process " + str(self.state) + " finished!\n")
                
                # get rendered frames from remote servers
                if(self.state == 1):
                    print("Fetching render files...")
                    self.process = getFrames()
                    self.state +=1
                    return{'PASS_THROUGH'}
                
                # average the rendered frames
                elif(self.state == 2):
                    print("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                elif(self.state == 3):
                    self.report({'INFO'}, "Render completed! View the rendered image in your UV/Image_Editor")
                    setRenderStatus("Complete!")
                    return{'FINISHED'}
                else:
                    self.report({'WARNING'}, "ERROR: Current state not recognized.")
                    setRenderStatus("ERROR")
                    return{'FINISHED'}
        
        return{'PASS_THROUGH'}

    def execute(self, context):
        print()
        
        global projectName
        global projectPath
        global serverFilePath
        projectName = bpy.path.display_name_from_filepath(bpy.data.filepath)
        serverFilePath = "/tmp/cgearhar/" + projectName + "/"
 
        if projectName == "":
            self.report({'WARNING'}, "RENDER FAILED: You have not saved your project file. Please save it before attempting to render.")
            setRenderStatus("Failed")
            return{'FINISHED'}
        elif bpy.context.scene.camera is None:
            self.report({'WARNING'}, "RENDER FAILED: No camera in scene.")
            setRenderStatus("Failed")
            return{'FINISHED'}
        elif not bpy.context.scene.render.image_settings.color_mode == 'RGB':
            self.report({'WARNING'}, "RENDER FAILED: Due to current lack of functionality, this script only runs with 'RGB' color mode.")
            setRenderStatus("Failed")
            return{'FINISHED'}
        else:
            self.report({'INFO'}, "Rendering current frame on " + str(len(context.scene['availableServers'])) + " servers.")
            
        curFrame = bpy.data.scenes["Scene"].frame_current
        
        if(len(bpy.data.cameras) == 0):
            self.report({'WARNING'}, "RENDER FAILED: No camera in scene.")
            setRenderStatus("Failed")
            return{'FINISHED'}


        # change context for bpy.ops.image
        #area = bpy.context.area
        #area.type = 'INFO'
        
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        
        self.fiveSecTimer = 0
        self.process = renderFrames(curFrame, curFrame)
        self.state   = 1
        
        self.report({'INFO'}, "Starting render on all available remote servers...")
        setRenderStatus("Rendering...")

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

class renderPanelLayout(View3DPanel, Panel):
    bl_label    = "Send to Servers"
    bl_context  = "objectmode"
    bl_category = "Render"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        #layout.label("First row")
        renderStatus = getRenderStatus()
        
              
        row = layout.row(align=True)
        row.label('Available Servers: ' + str(len(scn['availableServers'])) + " / " + str(len(scn['availableServers']) + len(scn['offlineServers'])))
        row.operator("scene.refresh_num_available_servers", text="", icon="FILE_REFRESH")

        col = layout.column(align=True)

        row = col.row(align=True)
        row.alignment = 'EXPAND'
        row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
        row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")
 
        col = layout.column(align=True)
         
        row = col.row(align=True)
        row.label('Render Samples: ' + str((bpy.data.scenes['Scene'].cycles.samples)*len(scn['availableServers'])))
         
 
        if(renderStatus != "None"):
            row = col.row(align=True)
            row.label('Render Status: ' + renderStatus)
            if(renderStatus == "Complete!"):
                row = layout.row(align=True)
                row.operator("scene.open_rendered_image", text="Open Rendered Image", icon="FILE_IMAGE")

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

print("Render Farm Loaded")