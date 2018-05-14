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
from bpy.app.handlers import persistent
from bpy.props import *
from ..functions import *


@persistent
def refresh_servers(scene):
    updateServerPrefs()

bpy.app.handlers.load_post.append(refresh_servers)


@persistent
def verify_render_status_on_load(scene):
    scn = bpy.context.scene
    scn.imageRenderStatus = "None" if scn.imageRenderStatus in ["Preparing files...", "Rendering...", "Finishing...", "ERROR"] else scn.imageRenderStatus
    scn.animRenderStatus = "None" if scn.animRenderStatus in ["Preparing files...", "Rendering...", "Finishing...", "ERROR"] else scn.animRenderStatus


bpy.app.handlers.load_post.append(verify_render_status_on_load)
