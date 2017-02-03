#!/usr/bin/env python

import bpy, math
from bpy.types import Panel
from bpy.props import *
from ..functions import getRenderStatus
from ..functions.setupServerVars import *

class renderOnServersPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Render on Servers"
    bl_idname      = "VIEW3D_PT_tools_render_on_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine != 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label("Please switch to Cycles")
        else:
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
            col = layout.column(align=True)
            row = col.row(align=True)

            # if 'remoteServers.txt' file has been edited, read in new input
            if bpy.props.requiredFileRead:
                serverVars = setupServerVars()
                bpy.props.servers = serverVars["servers"]
                bpy.props.hostServerLogin = serverVars["hostServerLogin"]
                bpy.props.requiredFileRead = False
            row.prop(scn, "serverGroups")

            # Render Status Info
            if(imRenderStatus != "None" and animRenderStatus != "None"):
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label('Render Status (f): ' + imRenderStatus)
                row = col.row(align=True)
                row.label('Render Status (a):  ' + animRenderStatus)
            elif(imRenderStatus != "None"):
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label('Render Status: ' + imRenderStatus)
            elif(animRenderStatus != "None"):
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label('Render Status: ' + animRenderStatus)


            # display buttons to view render(s)
            row = layout.row(align=True)
            if   "image"   in scn.renderType:
                row.operator("scene.open_rendered_image", text="View Image", icon="FILE_IMAGE")
            if "animation" in scn.renderType:
                row.operator("scene.open_rendered_animation", text="View Animation", icon="FILE_MOVIE")

def menu_draw(self, context):
    layout = self.layout
    scn = context.scene

    if scn.render.engine == 'CYCLES' and not scn.cycles.progressive == 'BRANCHED_PATH':
        # Basic Render Samples Info
        col = layout.column(align=True)
        row = col.row(align=True)
        sampleSize = scn.cycles.samples
        if(scn.cycles.use_square_samples):
            sampleSize = sampleSize**2
        if sampleSize < 10:
            row.label('Too few samples')
        else:
            row.label("Samples on Servers: " + str(math.floor(sampleSize*len(scn['availableServers']))))

bpy.types.CyclesRender_PT_sampling.append(menu_draw)

class frameRangePanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Frame Range"
    bl_idname      = "VIEW3D_PT_frame_range"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(scn, "frameRanges")
            col = layout.column(align=True)
            col.active = bpy.path.display_name_from_filepath(bpy.data.filepath) != ""
            row = col.row(align=True)
            row.operator("scene.list_files", text="List Missing Files", icon="LONGDISPLAY")
            row = col.row(align=True)
            row.operator("scene.set_to_missing_frames", text="Set to Missing Frames", icon="FILE_PARENT")

class serversPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Servers"
    bl_idname      = "VIEW3D_PT_servers"
    bl_context     = "objectmode"
    bl_category    = "Render"
    bl_options     = {'DEFAULT_CLOSED'}
    COMPAT_ENGINES = {'CYCLES'}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("scene.edit_servers_dict", text="Edit Remote Servers", icon="TEXT")
            row = col.row(align=True)
            row.operator("scene.restart_remote_servers", text="Restart Remote Servers", icon="FILE_REFRESH")

            col = layout.column(align=True)
            row = col.row(align=True)
            box = row.box()
            box.prop(scn, "showAdvanced")
            if scn.showAdvanced:
                row = box.row(align=True)
                row.prop(scn, "maxServerLoad")
                row = box.row(align=True)
                row.prop(scn, "unpack")
                row = box.row(align=True)
                row.prop(scn, "tempFilePath")
                row = box.row(align=True)
                row.prop(scn, "nameOutputFiles")
                row = box.row(align=True)
                row.prop(scn, "tempLocalDir")
