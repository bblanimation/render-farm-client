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

# System imports
#None!!

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Render Farm imports
from .ui import *
from .buttons import *
from .functions.setupServers import *

# Used to store keymaps for addon
addon_keymaps = []

def more_menu_options(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("render_farm.render_frame_on_servers", text="Render Image on Servers", icon='RENDER_STILL')
    layout.operator("render_farm.render_animation_on_servers", text="Render Animation on Servers", icon='RENDER_ANIMATION')

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_render.append(more_menu_options)

    bpy.props.render_farm_module_name = __name__
    bpy.props.render_farm_version = str(bl_info["version"])[1:-1].replace(", ", ".")

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

    bpy.types.Scene.imagePreviewAvailable = BoolProperty(default=False)
    bpy.types.Scene.animPreviewAvailable = BoolProperty(default=False)
    bpy.types.Scene.imageRenderStatus = StringProperty(name="Image Render Status", default="None")
    bpy.types.Scene.animRenderStatus = StringProperty(name="Image Render Status", default="None")

    # Initialize server and login variables
    bpy.types.Scene.serverGroups = EnumProperty(
        attr="serverGroups",
        name="Servers",
        description="Choose which hosts to use for render processes",
        items=[("All Servers", "All Servers", "Render on all servers")],
        default="All Servers")
    bpy.types.Scene.lastServerGroup = StringProperty(name="Last Server Group", default="All Servers")
    bpy.props.serverPrefs = {"servers":None, "login":None, "path":None, "hostConnection":None}
    bpy.types.Scene.availableServers = IntProperty(name="Available Servers", default=0)
    bpy.types.Scene.offlineServers = IntProperty(name="Offline Servers", default=0)
    bpy.types.Scene.needsUpdating = BoolProperty(default=True)

    bpy.types.Scene.nameAveragedImage = StringProperty(default="")
    bpy.types.Scene.nameImOutputFiles = StringProperty(default="")
    bpy.types.Scene.imExtension = StringProperty(default="")
    bpy.types.Scene.animExtension = StringProperty(default="")
    bpy.types.Scene.imFrame = IntProperty(default=-1)
    bpy.props.animFrameRange = None

    # handle the keymap
    wm = bpy.context.window_manager
    # Note that in background mode (no GUI available), keyconfigs are not available either, so we have
    # to check this to avoid nasty errors in background case.
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new("render_farm.render_frame_on_servers", 'F12', 'PRESS', alt=True)
        kmi = km.keymap_items.new("render_farm.render_animation_on_servers", 'F12', 'PRESS', alt=True, shift=True)
        kmi = km.keymap_items.new("render_farm.open_rendered_image", 'O', 'PRESS', shift=True)
        kmi = km.keymap_items.new("render_farm.open_rendered_animation", 'O', 'PRESS', alt=True, shift=True)
        kmi = km.keymap_items.new("render_farm.list_frames", 'M', 'PRESS', shift=True)
        kmi = km.keymap_items.new("render_farm.set_to_missing_frames", 'M', 'PRESS', alt=True, shift=True)
        kmi = km.keymap_items.new("render_farm.refresh_num_available_servers", 'R', 'PRESS', ctrl=True)
        kmi = km.keymap_items.new("render_farm.edit_servers_dict", 'E', 'PRESS', ctrl=True)
        addon_keymaps.append(km)

def unregister():
    # handle the keymap
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

    Scn = bpy.types.Scene

    del bpy.props.animFrameRange
    del Scn.imFrame
    del Scn.animExtension
    del Scn.nameImOutputFiles
    del Scn.imExtension
    del Scn.nameAveragedImage
    del bpy.props.serverPrefs
    del Scn.offlineServers
    del Scn.availableServers
    del Scn.needsUpdating
    del Scn.lastServerGroup
    del Scn.serverGroups
    del Scn.animRenderStatus
    del Scn.imageRenderStatus
    del Scn.animPreviewAvailable
    del Scn.imagePreviewAvailable
    del Scn.maxSamples
    del Scn.samplesPerFrame
    del Scn.timeout
    del Scn.maxServerLoad
    del Scn.nameOutputFiles
    del Scn.renderDumpLoc
    del Scn.tempLocalDir
    del Scn.frameRanges
    del Scn.compress
    del Scn.killPython
    del Scn.showAdvanced

    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(more_menu_options)

if __name__ == "__main__":
    register()
