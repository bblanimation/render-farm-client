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

class editRemoteServersDict(Operator):
    """Edit the remote servers dictionary in a text editor"""                   # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.edit_servers_dict"                                       # unique identifier for buttons and menu items to reference.
    bl_label = "Edit Remote Servers"                                            # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    def execute(self, context):
        changeContext(context, "TEXT_EDITOR")
        try:
            libraryServersPath = os.path.join(getLibraryPath(), "servers")
            bpy.ops.text.open(filepath=os.path.join(libraryServersPath, "remoteServers.txt"))
            self.report({"INFO"}, "Opened 'remoteServers.txt'")
            bpy.props.needsUpdating = True
        except:
            self.report({"ERROR"}, "ERROR: Could not open 'remoteServers.txt'. If the problem persists, try reinstalling the add-on.")
        return{"FINISHED"}
