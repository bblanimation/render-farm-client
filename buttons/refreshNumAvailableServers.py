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

class refreshNumAvailableServers(Operator):
    """Attempt to connect to all servers through host server"""                 # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "scene.refresh_num_available_servers"                           # unique identifier for buttons and menu items to reference.
    bl_label = "Refresh Available Servers"                                      # display name in the interface.
    bl_options = {"REGISTER", "UNDO"}                                           # enable undo for the operator.

    @classmethod
    def poll(cls, context):
        """ ensures operator can execute (if not, returns false) """
        if not have_internet():
            return False
        return True

    def checkNumAvailServers(self):
        scn = bpy.context.scene
        command = "ssh -T -oStrictHostKeyChecking=no -x {login} 'python {remotePath}blender_task -Hv --connection_timeout {timeout} --hosts_file {remotePath}servers.txt'".format(login=bpy.props.serverPrefs["login"], remotePath=bpy.props.serverPrefs["path"], timeout=scn.timeout)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        return process

    def updateAvailServerInfo(self):
        scn = bpy.context.scene

        available = None
        offline = None

        while available is None:
            try:
                rl = self.process.stdout.readline()
                line1 = rl.decode("ASCII").replace("\\n", "")
                available = json.loads(line1.replace("'", "\""))
            except:
                print(line1, end="")
                available = None
        while offline is None:
            try:
                rl = self.process.stdout.readline()
                line2 = rl.decode("ASCII").replace("\\n", "")
                offline = json.loads(line2.replace("'", "\""))
            except:
                print(line2, end="")
                offline = None

        scn.availableServers = len(available)
        scn.offlineServers = len(offline)
        for a in bpy.context.screen.areas:
            a.tag_redraw()

    def modal(self, context, event):
        if event.type in {"ESC"}:
            self.report({"INFO"}, "Refresh process cancelled")
            self.cancel(context)
            return{"CANCELLED"}

        if event.type == "TIMER":
            self.process.poll()

            # if python not found on host server
            if self.process.returncode == 127 and self.state == 2:
                self.report({"ERROR"}, "python not installed on host server")
                self.cancel(context)
                return{"CANCELLED"}

            # if process finished and unknown error thrown
            if self.process.returncode != 0 and self.process.returncode != None:
                handleError(self, "Process {curState}".format(curState=str(self.state-1)))
                self.cancel(context)
                return{"CANCELLED"}

            # if process finished and no errors
            if self.process.returncode != None:
                # print("Process {curState} finished! (return code: {returnCode})".format(curState=str(self.state-1), returnCode=str(self.process.returncode)))

                # check number of available servers via host server
                if self.state == 1:
                    bpy.props.needsUpdating = False
                    self.state += 1
                    self.process = self.checkNumAvailServers()
                    return{"PASS_THROUGH"}

                elif self.state == 2:
                    self.updateAvailServerInfo()
                    scn = context.scene
                    self.report({"INFO"}, "Refresh process completed ({num} servers available)".format(num=str(scn.availableServers)))
                    return{"FINISHED"}
                else:
                    self.report({"ERROR"}, "ERROR: Current state not recognized.")
                    return{"FINISHED"}

        return{"PASS_THROUGH"}

    def execute(self, context):
        print("\nRunning 'checkNumAvailServers' function...")
        scn = context.scene

        # start initial process
        self.state = 1 # initializes state for modal
        if bpy.props.needsUpdating or bpy.props.lastServerGroup != scn.serverGroups:
            bpy.props.lastServerGroup = scn.serverGroups
            updateStatus = updateServerPrefs()
            if not updateStatus["valid"]:
                self.report({"ERROR"}, updateStatus["errorMessage"])
                return{"CANCELLED"}
            self.process = copyFiles()
            bpy.props.lastRemotePath = bpy.props.serverPrefs["path"]
        else:
            self.process = self.checkNumAvailServers()
            self.state += 1

        # create timer for modal
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)

        self.report({"INFO"}, "Refreshing available servers...")

        return{"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self.process.kill()
