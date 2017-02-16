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
import math
from bpy.types import Panel
from bpy.props import *
from ..functions import getRenderStatus
from ..functions.setupServers import *

class renderOnServersPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Render on Servers"
    bl_idname      = "VIEW3D_PT_tools_render_on_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine != "CYCLES":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label("Please switch to Cycles")
        else:
            imRenderStatus = getRenderStatus("image")
            animRenderStatus = getRenderStatus("animation")

            # Available Servers Info
            col = layout.column(align=True)
            row = col.row(align=True)
            availableServerString = "Available Servers: {available} / {total}".format(available=str(scn.availableServers),total=str(scn.availableServers + scn.offlineServers))
            row.operator("scene.refresh_num_available_servers", text=availableServerString, icon="FILE_REFRESH")

            # Render Buttons
            row = col.row(align=True)
            row.alignment = "EXPAND"
            row.active = scn.availableServers > 0
            row.operator("scene.render_frame_on_servers", text="Render", icon="RENDER_STILL")
            row.operator("scene.render_animation_on_servers", text="Animation", icon="RENDER_ANIMATION")
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scn, "serverGroups")

            # Render Status Info
            if imRenderStatus != "None":
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label("Render Status: {imRenderStatus}".format(imRenderStatus=imRenderStatus))
            elif animRenderStatus != "None":
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label("Render Status: {animRenderStatus}".format(animRenderStatus=animRenderStatus))

            # display buttons to view render(s)
            row = layout.row(align=True)
            if   "image"   in scn.renderType:
                row.operator("scene.open_rendered_image", text="View Image", icon="FILE_IMAGE")
            if "animation" in scn.renderType:
                row.operator("scene.open_rendered_animation", text="View Animation", icon="FILE_MOVIE")

class frameRangePanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Frame Range"
    bl_idname      = "VIEW3D_PT_frame_range"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == "CYCLES":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scn, "frameRanges")
            col = layout.column(align=True)
            col.active = bpy.path.display_name_from_filepath(bpy.data.filepath) != ""
            row = col.row(align=True)
            row.operator("scene.list_frames", text="List Missing Frames", icon="LONGDISPLAY")
            row = col.row(align=True)
            row.operator("scene.set_to_missing_frames", text="Set to Missing Frames", icon="FILE_PARENT")

class serversPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Servers"
    bl_idname      = "VIEW3D_PT_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    # bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == "CYCLES":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("scene.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")

            col = layout.column(align=True)
            row = col.row(align=True)

            box = row.box()
            box.prop(scn, "showAdvanced")
            if scn.showAdvanced:
                col = box.column()
                col.prop(scn, "nameOutputFiles")
                col.prop(scn, "renderDumpLoc")

                layout.separator()

                col = box.column(align=True)
                col.label(text="Performance:")
                col.prop(scn, "maxServerLoad")
                col.prop(scn, "timeout")
                col.prop(scn, "maxSamples")

                layout.separator()

                row = col.row(align=True)
                row.prop(scn, "killPython")
                row.prop(scn, "compress")
                # The following is probably unnecessary
                # col = box.row(align=True)
                # col.prop(scn, "tempLocalDir")
