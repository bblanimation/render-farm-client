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
import time
import os

# Blender imports
import bpy
props = bpy.props

# Render Farm imports
from ..functions import *


class reportError(bpy.types.Operator):
    """Report a bug via an automatically generated issue ticket"""
    bl_idname = "render_farm.report_error"
    bl_label = "Report Error"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            # set up file paths
            libraryServersPath = os.path.join(getLibraryPath(), "error_log")
            # write necessary debugging information to text file
            writeErrorToFile(libraryServersPath, 'Render_Farm_log', bpy.props.render_farm_version)
            # open error report in UI with text editor
            changeContext(context, "TEXT_EDITOR")
            try:
                bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "Render_Farm_error_report.txt"))
                bpy.context.space_data.show_word_wrap = True
                self.report({"INFO"}, "Opened 'Render_Farm_error_report.txt'")
                bpy.props.needsUpdating = True
            except:
                self.report({"ERROR"}, "ERROR: Could not open 'Render_Farm_error_report.txt'. If the problem persists, try reinstalling the add-on.")
        except:
            self.report({"ERROR"}, "ERROR: Could not generate error report. Please use the 'Report a Bug' button in the Render Farm Preferences (found in Add-On User Preferences)")
        return{"FINISHED"}


class closeReportError(bpy.types.Operator):
    """Deletes error report from blender's memory (still exists in file system)"""
    bl_idname = "render_farm.close_report_error"
    bl_label = "Close Report Error"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        try:
            txt = bpy.data.texts['Render_Farm_log']
            bpy.data.texts.remove(txt, True)
        except:
            handle_exception()
        return{"FINISHED"}
