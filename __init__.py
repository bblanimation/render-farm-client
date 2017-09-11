bl_info = {
    "name"        : "Render Farm Client",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (0, 7, 5),
    "blender"     : (2, 78, 0),
    "description" : "Render your scene on a custom server farm with this addon.",
    "location"    : "View3D > Tools > Render",
    "warning"     : "Relatively stable but still work in progress",
    "wiki_url"    : "",
    "tracker_url" : "",
    "category"    : "Render"}

"""
Copyright (C) 2017 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# system imports
import bpy
from bpy.types import Operator
from bpy.props import *
from .ui import *
from .buttons import *
from .functions.setupServers import *

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

    bpy.types.Scene.showAdvanced = BoolProperty(
        name="Show Advanced",
        description="Display advanced remote server settings",
        default=False)

    bpy.types.Scene.killPython = BoolProperty(
        name="Kill Python",
        description="Run 'killall -9 python' on host server after render process cancelled",
        default=True)

    bpy.types.Scene.compress = BoolProperty(
        name="Compress",
        description="Send compressed Blender file to host server (slower local save, faster file transfer)",
        default=True)

    bpy.types.Scene.frameRanges = StringProperty(
        name="Frames",
        description="Define frame ranges to render, separated by commas (e.g. '1,3,6-10')",
        default="")

    bpy.types.Scene.tempLocalDir = StringProperty(
        name="Temp Local Path",
        description="File path on local drive to store temporary project files",
        maxlen=128,
        default="/tmp/",
        subtype="DIR_PATH")

    bpy.types.Scene.renderDumpLoc = StringProperty(
        name="Output",
        description="Folder to store output files from Blender (empty folder recommended)",
        maxlen=128,
        default="//render-dump/",
        subtype="DIR_PATH")

    bpy.types.Scene.nameOutputFiles = StringProperty(
        name="Name",
        description="Name output files in 'render_dump' folder (prepended to: '_####')",
        maxlen=128,
        default="")

    bpy.types.Scene.maxServerLoad = IntProperty(
        name="Max Server Load",
        description="Maximum number of frames to be handled at once by each server",
        min=1, max=8,
        default=1)

    bpy.types.Scene.timeout = FloatProperty(
        name="Timeout",
        description="Time (in seconds) to wait for client servers to respond",
        min=.001, max=1,
        default=.01)

    bpy.types.Scene.samplesPerFrame = IntProperty(
        name="Samples Per Job",
        description="Number of samples to render per job when rendering current frame",
        min=10, max=999,
        default=10)

    bpy.types.Scene.maxSamples = IntProperty(
        name="Max Samples",
        description="Maximum number of samples to render when rendering current frame",
        min=100, max=9999,
        default=1000)

    bpy.types.Scene.renderType = []
    bpy.types.Scene.renderStatus = {"animation":"None", "image":"None"}

    # Initialize server and login variables
    bpy.types.Scene.serverGroups = EnumProperty(
        attr="serverGroups",
        name="Servers",
        description="Choose which hosts to use for render processes",
        items=[("All Servers", "All Servers", "Render on all servers")],
        default="All Servers")
    bpy.props.lastServerGroup = "All Servers"
    bpy.props.serverPrefs = {"servers":None, "login":None, "path":None, "hostConnection":None}
    bpy.types.Scene.availableServers = IntProperty(name="Available Servers", default=0)
    bpy.types.Scene.offlineServers = IntProperty(name="Offline Servers", default=0)
    bpy.props.lastRemotePath = None
    bpy.props.needsUpdating = True

    bpy.props.nameAveragedImage = ""
    bpy.props.imExtension = False
    bpy.props.nameImOutputFiles = ""
    bpy.props.animExtension = False
    bpy.props.imFrame = -1
    bpy.props.animFrameRange = []

    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new("scene.render_frame_on_servers", 'F12', 'PRESS', alt=True)
    kmi = km.keymap_items.new("scene.render_animation_on_servers", 'F12', 'PRESS', alt=True, shift=True)
    kmi = km.keymap_items.new("scene.open_rendered_image", 'O', 'PRESS', shift=True)
    kmi = km.keymap_items.new("scene.open_rendered_animation", 'O', 'PRESS', alt=True, shift=True)
    kmi = km.keymap_items.new("scene.list_frames", 'M', 'PRESS', shift=True)
    kmi = km.keymap_items.new("scene.set_to_missing_frames", 'M', 'PRESS', alt=True, shift=True)
    kmi = km.keymap_items.new("scene.refresh_num_available_servers", 'R', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new("scene.edit_servers_dict", 'E', 'PRESS', ctrl=True)
    addon_keymaps.append(km)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(more_menu_options)
    del bpy.types.Scene.showAdvanced
    del bpy.types.Scene.frameRanges
    del bpy.types.Scene.tempLocalDir
    del bpy.types.Scene.renderDumpLoc
    del bpy.types.Scene.nameOutputFiles
    del bpy.types.Scene.maxServerLoad
    del bpy.types.Scene.timeout
    del bpy.types.Scene.maxSamples
    del bpy.types.Scene.renderType
    del bpy.types.Scene.killPython
    del bpy.types.Scene.renderStatus
    del bpy.props.serverPrefs
    del bpy.props.animFrameRange
    del bpy.props.lastRemotePath
    del bpy.props.nameAveragedImage
    del bpy.props.imExtension
    del bpy.props.animExtension
    del bpy.props.needsUpdating
    del bpy.types.Scene.serverGroups

    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)

    # clear the list
    addon_keymaps.clear()

if __name__ == "__main__":
    register()
