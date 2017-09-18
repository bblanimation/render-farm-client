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
import io
import json
import os
import subprocess
import time

from bpy.types import Operator
from bpy.props import *
from ..functions import *
from ..functions.averageFrames import *
from ..functions.jobIsValid import *

class listMissingFrames(Operator):
    """List the output files missing from the render dump folder"""             # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.list_frames"                                              # unique identifier for buttons and menu items to reference.
    bl_label = "List Missing Frames"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        try:
            scn = context.scene

            # initializes self.frameRangesDict (returns False if frame range invalid)
            if not setFrameRangesDict(self):
                return{"FINISHED"}

            # list all missing files from start frame to end frame in render dump folder
            missingFrames = listMissingFiles(getNameOutputFiles(), self.frameRangesDict["string"])
            if len(missingFrames) > 0:
                self.report({"INFO"}, "Missing frames: {missingFrames}".format(missingFrames=missingFrames))
            else:
                self.report({"INFO"}, "All frames accounted for!")

            return{"FINISHED"}
        except:
            self.handle_exception()
            return{"CANCELLED"}

    def handle_exception(self):
        errormsg = print_exception('LEGOizer_log')
        # if max number of exceptions occur within threshold of time, abort!
        curtime = time.time()
        print('\n'*5)
        print('-'*100)
        print("Something went wrong. Please start an error report with us so we can fix it! (press the 'Report a Bug' button under the 'Render on Servers' dropdown menu of the Render Farm Client)")
        print('-'*100)
        print('\n'*5)
        showErrorMessage("Something went wrong. Please start an error report with us so we can fix it! (press the 'Report a Bug' button under the 'Render on Servers' dropdown menu of the Render Farm Client)", wrap=240)

class setToMissingFrames(Operator):
    """Set frame range to frames missing from the render dump folder"""         # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.set_to_missing_frames"                                   # unique identifier for buttons and menu items to reference.
    bl_label = "Set to Missing Frames"                                          # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        try:
            scn = context.scene

            # initializes self.frameRangesDict (returns False if frame range invalid)
            if not setFrameRangesDict(self):
                return{"FINISHED"}

            # list all missing files from start frame to end frame in render dump location
            scn.frameRanges = listMissingFiles(getNameOutputFiles(), self.frameRangesDict["string"])

            return{"FINISHED"}
        except:
            self.handle_exception()
            return{"CANCELLED"}

    def handle_exception(self):
        errormsg = print_exception('LEGOizer_log')
        # if max number of exceptions occur within threshold of time, abort!
        curtime = time.time()
        print('\n'*5)
        print('-'*100)
        print("Something went wrong. Please start an error report with us so we can fix it! (press the 'Report a Bug' button under the 'Render on Servers' dropdown menu of the Render Farm Client)")
        print('-'*100)
        print('\n'*5)
        showErrorMessage("Something went wrong. Please start an error report with us so we can fix it! (press the 'Report a Bug' button under the 'Render on Servers' dropdown menu of the Render Farm Client)", wrap=240)
