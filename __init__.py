#!/usr/bin/env python

bl_info = {
    "name"        : "Server Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 7, 0),
    "blender"     : (2, 78, 0),
    "description" : "Render your scene on a remote server farm with this addon.",
    "location"    : "View3D > Tools > Render",
    "warning"     : "Relatively stable but still work in progress",
    "wiki_url"    : "",
    "tracker_url" : "",
    "category"    : "Render"}

import bpy
from bpy.types import Operator
from bpy.props import *
from . import (ui, buttons)
from .functions.setupServerVars import *

def more_menu_options(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("sendFrame", text="Render Image on Servers", icon='RENDER_STILL')
    layout.operator("sendAnimation", text="Render Image on Servers", icon='RENDER_ANIMATION')

# store keymaps here to access after registration
addon_keymaps = []

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_render.append(more_menu_options)

    # initialize check box for displaying render sampling details
    bpy.types.Scene.showAdvanced = BoolProperty(
        name="Show Advanced",
        description="Display advanced remote server settings",
        default=False)

    # unpack the files automatically after packing them into the .blend file
    bpy.types.Scene.unpack = BoolProperty(
        name="Auto-unpack files",
        description="Unpack the files that got packed for remote servers after saving",
        default=True)

    # initialize frame range string text box
    bpy.types.Scene.frameRanges = StringProperty(
        name="Frames"
        description="define frame ranges to render, separated by commas. (e.g. '1,3,6-10')"
        default="")

    # initialize frame range string text box
    bpy.types.Scene.tempFilePath = StringProperty(
        name="Remote Path",
        description="File path on host server (temporary storage location)",
        maxlen=128,
        default="/tmp/renderFarm/")

    bpy.types.Scene.tempLocalDir = StringProperty(
        name="Temp Local Path",
        description="File path on local drive to store temporary project files",
        maxlen=128,
        default="/tmp/",
        subtype="DIR_PATH")

    bpy.types.Scene.nameOutputFiles = StringProperty(
        name="Name Output Files",
        description="Custom name used for rendered frames in 'render_dump' folder (prepended to: '_####')",
        maxlen=128,
        default="")

    bpy.types.Scene.maxServerLoad = IntProperty(
        name="Max Server Load",
        description="Set a limit on the number of frames to be rendered in parallel by each server (0 for no limit)",
        min=0, max=50,
        default=0)

    bpy.types.Scene.renderType = []
    bpy.types.Scene.renderStatus = {"animation":"None", "image":"None"}

    # Initialize server and hostServerLogin variables
    serverVars = setupServerVars()
    bpy.props.servers = serverVars["servers"]
    bpy.props.hostServerLogin = serverVars["hostServerLogin"]
    writeServersFile(bpy.props.servers, "All Servers")
    bpy.props.requiredFileRead = False

    # initialize server groups enum property
    groupNames = [("All Servers", "All Servers", "Render on all servers")]
    for groupName in serverVars["servers"]:
        tmpList = [groupName, groupName, "Render only servers on this group"]
        groupNames.append(tuple(tmpList))
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
    del bpy.types.Scene.showAdvanced
    del bpy.types.Scene.unpack
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.tempFilePath
    del bpy.types.Scene.tempLocalDir
    del bpy.types.Scene.nameOutputFiles
    del bpy.types.Scene.maxServerLoad
    del bpy.types.Scene.renderType
    del bpy.types.Scene.renderStatus
    del bpy.props.servers
    del bpy.props.hostServerLogin
    del bpy.props.requiredFileRead
    del bpy.types.Scene.serverGroups

    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)

    # clear the list
    addon_keymaps.clear()

if __name__ == "__main__":
    register()
