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
from ..functions import getRenderStatus, have_internet
from ..functions.setupServers import *

@persistent
def handle_saving_when_rendering(scene):
    # TODO: Force end render process or something, instead of 'set_render_status_on_load' below
    pass

bpy.app.handlers.save_pre.append(handle_saving_when_rendering)

@persistent
def set_render_status_on_load(scene):
    scene.renderStatus["image"] = "None"
    scene.renderStatus["animation"] = "None"

bpy.app.handlers.load_post.append(set_render_status_on_load)
