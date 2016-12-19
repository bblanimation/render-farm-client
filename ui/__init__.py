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

class samplingPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Sampling (Single Frame)"
    bl_idname      = "VIEW3D_PT_sampling"
    bl_context     = "objectmode"
    bl_category    = "Render"
    COMPAT_ENGINES = {'CYCLES'}

    def calcSamples(self, scn, squared, category, multiplier):
        if squared:
            category = category**2
        result = math.floor(multiplier*category*len(scn['availableServers']))
        return result

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        if scn.render.engine == 'CYCLES':
            # Basic Render Samples Info
            col = layout.column(align=True)
            row = col.row(align=True)

            if not context.scene.cycles.progressive == 'BRANCHED_PATH':
                sampleSize = scn.cycles.samples
                if(scn.cycles.use_square_samples):
                    sampleSize = sampleSize**2
                if sampleSize < 10:
                    row.label('Samples: Too few samples')
                else:
                    row.label("Samples: " + str(math.floor(sampleSize*len(scn['availableServers']))))
            else:
                # find AA sample size first (this affects other sample sizes)
                aaSampleSize = scn.cycles.aa_samples
                squared = False
                if(scn.cycles.use_square_samples):
                    squared = True
                    aaSampleSize = aaSampleSize**2

                # calculate sample sizes for single frame renders on available servers
                aa    = self.calcSamples(scn, squared, aaSampleSize, 1)
                diff  = self.calcSamples(scn, squared, scn.cycles.diffuse_samples, aaSampleSize)
                glos  = self.calcSamples(scn, squared, scn.cycles.glossy_samples, aaSampleSize)
                tran  = self.calcSamples(scn, squared, scn.cycles.transmission_samples, aaSampleSize)
                ao    = self.calcSamples(scn, squared, scn.cycles.ao_samples, aaSampleSize)
                meshL = self.calcSamples(scn, squared, scn.cycles.mesh_light_samples, aaSampleSize)
                sub   = self.calcSamples(scn, squared, scn.cycles.subsurface_samples, aaSampleSize)
                vol   = self.calcSamples(scn, squared, scn.cycles.volume_samples, aaSampleSize)

                row = col.row(align=True)
                if(aaSampleSize < 5):
                    row.label('AA: Too few samples')
                else:
                    row.label('AA:')
                    row.label(str(aa))
                    row = col.row(align=True)
                    row.label('Diffuse:')
                    row.label(str(diff))
                    row = col.row(align=True)
                    row.label('Glossy:')
                    row.label(str(glos))
                    row = col.row(align=True)
                    row.label('Transmission:')
                    row.label(str(tran))
                    row = col.row(align=True)
                    row.label('AO:')
                    row.label(str(ao))
                    row = col.row(align=True)
                    row.label('Mesh Light:')
                    row.label(str(meshL))
                    row = col.row(align=True)
                    row.label('Subsurface:')
                    row.label(str(sub))
                    row = col.row(align=True)
                    row.label('Volume:')
                    row.label(str(vol))
    # def menu_draw(self, context):
    #     layout = self.layout
    #     scn = context.scene
    #
    #     if scn.render.engine == 'CYCLES' and not scn.cycles.progressive == 'BRANCHED_PATH':
    #         # Basic Render Samples Info
    #         col = layout.column(align=True)
    #         row = col.row(align=True)
    #         sampleSize = scn.cycles.samples
    #         if(scn.cycles.use_square_samples):
    #             sampleSize = sampleSize**2
    #         if sampleSize < 10:
    #             row.label('Too few samples')
    #         else:
    #             row.label("Total Samples: " + str(math.floor(sampleSize*len(scn['availableServers']))))
    #
    # bpy.types.CyclesRender_PT_sampling.append(menu_draw)

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
                row.prop(scn, "distributionType")
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
