# Copyright (C) 2018 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# system imports
import bpy
import math
from bpy.types import Panel
from bpy.props import *
from ..functions import *
from .app_handlers import *

class RFC_PT_render_on_servers(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_label       = "Render on Servers"
    bl_idname      = "RFC_PT_render_on_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if not have_internet():
            col = layout.column(align=True)
            col.label(text="No internet connection")
            return

        imRenderStatus = getRenderStatus("image")
        animRenderStatus = getRenderStatus("animation")

        # Available Servers Info
        col = layout.column(align=True)
        row = col.row(align=True)
        availableServerString = "Available Servers: {available} / {total}".format(available=str(scn.rfc_availableServers),total=str(scn.rfc_availableServers + scn.rfc_offlineServers))
        row.operator("render_farm_client.refresh_available_servers", text=availableServerString, icon="FILE_REFRESH")

        # Render Buttons
        row = col.row(align=True)
        row.alignment = "EXPAND"
        row.operator("render_farm_client.render_frame", text="Render", icon="RENDER_STILL")
        row.operator("render_farm_client.render_animation", text="Animation", icon="RENDER_ANIMATION")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scn, "rfc_serverGroups")

        # Render Status Info
        if imRenderStatus != "None":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Render Status: {status}".format(status=imRenderStatus))
        elif animRenderStatus != "None":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Render Status: {status}".format(status=animRenderStatus))

        # display buttons to view render(s)
        row = layout.row(align=True)
        if scn.rfc_imagePreviewAvailable:
            row.operator("render_farm_client.open_rendered_image", text="View Image", icon="FILE_IMAGE")
        if scn.rfc_animPreviewAvailable:
            row.operator("render_farm_client.open_rendered_animation", text="View Animation", icon="FILE_MOVIE")

        if bpy.data.texts.find('Render_Farm_log') >= 0:
            split = layout.split(align=True, percentage=0.9)
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("render_farm_client.report_error", text="Report Error", icon="URL")
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("render_farm_client.close_report_error", text="", icon="PANEL_CLOSE")


class RFC_PT_frame_range(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_label       = "Frame Range"
    bl_idname      = "RFC_PT_frame_range"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scn, "rfc_frameRanges")
        col = layout.column(align=True)
        col.active = bpy.path.display_name_from_filepath(bpy.data.filepath) != ""
        row = col.row(align=True)
        row.operator("render_farm_client.list_frames", text="List Missing Frames", icon="LONGDISPLAY")
        row = col.row(align=True)
        row.operator("render_farm_client.set_to_missing_frames", text="Set to Missing Frames", icon="FILE_PARENT")

class RFC_PT_servers(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_label       = "Servers"
    bl_idname      = "RFC_PT_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    # bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("render_farm_client.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")

        col = layout.column(align=True)
        row = col.row(align=True)

        if not b280():
            RFC_PT_advanced.draw(self, context)


class RFC_PT_advanced(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_label       = "Advanced"
    bl_idname      = "RFC_PT_advanced"
    bl_context     = "objectmode"
    bl_category    = "Render"
    bl_parent_id   = "RFC_PT_servers"
    # bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES"}

    @classmethod
    def poll(self, context):
        return b280()

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if not b280():
            box = layout.box()
            box.prop(scn, "rfc_showAdvanced")
            if not scn.rfc_showAdvanced:
                return
        else:
            box = layout

        col = box.column()
        col.label(text="Output:")
        col.prop(scn, "rfc_renderDumpLoc", text="")

        col = box.column(align=True)
        col.label(text="Distribution:")
        col.prop(scn, "rfc_maxServerLoad")
        col.prop(scn, "rfc_timeout")
        if scn.render.engine == "CYCLES":
            col.prop(scn, "rfc_samplesPerFrame")
            col.prop(scn, "rfc_maxSamples")

        row = col.row(align=True)
        row.prop(scn, "rfc_killPython")
        row.prop(scn, "rfc_compress")
        # The following is probably unnecessary
        # col = box.row(align=True)
        # col.prop(scn, "tempLocalDir")

        col = box.column(align=True)
        row = col.row()
        col = row.column(align=True)
        col.label(text="Device:")
        col.prop(scn, "rfc_renderDevice", text="")
        # col.prop(scn, "cyclesComputeDevice", text="")
        col = row.column(align=True)
        col.label(text="Tiles:")
        col.prop(scn, "rfc_renderTiles", text="")
