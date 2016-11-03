import bpy
import subprocess
import telnetlib
import sys
import os, numpy
import time
from bpy.types import Menu, Panel, UIList
from bpy.props import *

renderStatus   = "None"
projectPath    = bpy.path.abspath("//")         # the full project path, including <projectName>.blend
projectName    = bpy.path.display_name_from_filepath(bpy.data.filepath)
hostServer     = "cgearhar@asahel.cse.taylor.edu"
serverFilePath = "/tmp/cgearhar/" + projectName + "/"
dumpLocation   = projectPath + "render-dump/"
servers        = { 'cse218': ['cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807','cse21808','cse21809','cse21810','cse21811','cse21812'], 'cse217': ['cse21701','cse21702','cse21703','cse21704','cse21705','cse21706','cse21707','cse21708','cse21709','cse21710','cse21711','cse21712','cse21713','cse21715','cse21716']}

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

    print("Success!")
    return process

def averageFrames():
    process = subprocess.Popen("python ~/my_scripts/averageFrames.py " + projectPath + " " + projectName, stdout=subprocess.PIPE, shell=True)
    return process
   
def renderFrames(startFrame, endFrame):
    bpy.ops.wm.save_mainfile()
    
    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    subprocess.call("rsync -a --copy-links --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServer + ":" + serverFilePath + "'", shell=True)

    # run blender command to render given range from the remote server
    print("opening connection to " + hostServer + "...")
    process = subprocess.Popen("ssh " + hostServer + " 'nohup blender_task.py -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'",stdout=subprocess.PIPE, shell=True)
    #subprocess.call("ssh " + hostServer + " 'nohup blender_task.py -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)
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
            return {'CANCELLED'}

        if event.type == 'TIMER':
            self.process.poll()
            
            #reportedLine = self.process.stdout.readline()
            #if reportedLine != "...":
            #    self.report({'INFO'}, str(reportedLine))
            
            if self.process.returncode != None:
                print("Render completed on remote servers!\n")
                
                # get rendered frames from remote servers
                if(self.state == 1):
                    self.report({'INFO'}, "Servers finished the render. Getting render files...")
                    setRenderStatus("Fetching render files...")
                    self.process = getFrames()
                    self.state +=1
                    return{'PASS_THROUGH'}
                
                # average the rendered frames
                elif(self.state == 2):
                    self.report({'INFO'}, "Averaging frames...")
                    setRenderStatus("Averaging frames...")
                    self.process = averageFrames()
                    self.state += 1
                    return{'PASS_THROUGH'}
                
                elif(self.state == 3):
                    self.report({'INFO'}, "Render completed! View the rendered image in your UV/Image_Editor")
                    setRenderStatus("Complete!")
                    return{'FINISHED'}
                else:
                    self.report({'INFO'}, "ERROR: Current state not recognized.")
                    setRenderStatus("ERROR")
                    return{'FINISHED'}
        
        return{'PASS_THROUGH'}

    def execute(self, context):
        print()
        curFrame = bpy.data.scenes["Scene"].frame_current

        # change context for bpy.ops.image
        #area = bpy.context.area
        #area.type = 'INFO'
        
        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        
        self.process = renderFrames(curFrame,curFrame)
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

        row = layout.row(align=True)

        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
        row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")

        row = layout.row(align=True)
        if(renderStatus != "None"):
            row.label('Render Status: ' + renderStatus)
        
        row = layout.row(align=True)
        if(renderStatus == "Complete!"):
            row.operator("scene.open_rendered_image", text="Open Rendered Image", icon="FILE_IMAGE")
        
#        row = layout.row(align=True)
#        row = layout.row(align=True)
#        row = layout.row(align=True)
#        row.operator("scene.get_rendered_frames", text="Get Frames", icon="IMAGE_DATA")
#        row.operator("scene.average_frames", text="Average Frames", icon="IMAGE_DATA")

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

print("Render Farm Loaded")