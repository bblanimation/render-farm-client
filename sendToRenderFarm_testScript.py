import bpy
import subprocess
import telnetlib
import sys
import os, numpy
from bpy.types import Menu, Panel, UIList
from bpy.props import *

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
    print()
    print("Getting frames...")

    print("verifying local directory...")
    subprocess.call("mkdir -p " + dumpLocation + "backups/", shell=True)

    print("cleaning up local directory...")
    subprocess.call("rsync --remove-source-files " + dumpLocation + "* " + dumpLocation + "backups/",shell=True)

    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    print("copying files from server...\n")
    subprocess.call("rsync --exclude='*.blend' '" + hostServer + ":" + serverFilePath + "*' '" + dumpLocation + "'",shell=True)

    print("Success!")
    return

def averageFrames():
    subprocess.call("python ~/my_scripts/averageFrames.py " + projectPath + " " + projectName, shell=True)
   
def renderFrames(startFrame, endFrame):
    bpy.ops.wm.save_mainfile()
    
    print("verifying remote directory...")
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    # set up project folder in remote server
    print("copying blender project files...")
    subprocess.call("rsync -a --copy-links --include=" + projectName + ".blend --exclude='*' '" + projectPath + "' '" + hostServer + ":" + serverFilePath + "'", shell=True)

    # run blender command to render given range from the remote server
    print("opening connection to " + hostServer + "...")
    subprocess.call("ssh " + hostServer + " 'nohup blender_task.py -n " + projectName + " -s " + str(startFrame) + " -e " + str(endFrame) + " &'", shell=True)

    getFrames()

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

    def execute(self, context):
        print()
        curFrame = bpy.data.scenes["Scene"].frame_current

        renderFrames(curFrame,curFrame)
        averageFrames()

        averaged_image_filepath = projectPath + "render-dump/" + projectName + "_average.tga"
        
        # change context for bpy.ops.image
        area = bpy.context.area
        old_type = area.type
        area.type = 'IMAGE_EDITOR'
        
        bpy.ops.image.open(filepath=averaged_image_filepath)

        return{'FINISHED'}

class getRenderedFrames(bpy.types.Operator):
    """Get Rendered Frames"""                           # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.get_rendered_frames"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Animation on Remote Servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                   # enable undo for the operator.

    def execute(self, context):
        getFrames()
        return{'FINISHED'}

class averageRenderedFrames(bpy.types.Operator):
    """Average Rendered Frames"""                               # blender will use this as a tooltip for menu items and buttons.
    bl_idname  = "scene.average_frames"            # unique identifier for buttons and menu items to reference.
    bl_label   = "Render Current Frame on Remote Servers"   # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}                       # enable undo for the operator.

    def execute(self, context):
        averageFrames()
        return{'FINISHED'}

class renderPanelLayout(View3DPanel, Panel):
    bl_label    = "Send to Servers"
    bl_context  = "objectmode"
    bl_category = "Render"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        #layout.label("First row")

        row = layout.row(align=True)
        row.label('Available Servers: ' + str(len(scn['availableServers'])) + " / " + str(len(scn['availableServers']) + len(scn['offlineServers'])))
        row.operator("scene.refresh_num_available_servers", text="", icon="FILE_REFRESH")

        row = layout.row(align=True)

        row = layout.row(align=True)
        row.alignment = 'EXPAND'
        row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
        row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")

        row = layout.row(align=True)


        row = layout.row(align=True)
        row.operator("scene.get_rendered_frames", text="Get Frames", icon="IMAGE_DATA")
        row.operator("scene.average_frames", text="Average Frames", icon="IMAGE_DATA")

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()

print("Render Farm Loaded")