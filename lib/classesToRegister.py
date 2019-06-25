# Copyright (C) 2019 Christopher Gearhart
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

# Addon imports
from ..ui import *
from ..buttons import *
from ..functions.common import *
from .preferences import *
from .reportError import *


classes = [
    # render-farm-client/button
    editServers.RFC_OT_edit_servers_dict,
    missingFramesActions.RFC_OT_list_frames,
    missingFramesActions.RFC_OT_set_to_missing_frames,
    openRender.RFC_OT_open_rendered_image,
    openRender.RFC_OT_open_rendered_animation,
    refreshServers.RFC_OT_refresh_available_servers,
    renderFrame.RFC_OT_render_frame,
    renderAnimation.RFC_OT_render_animation,
    # render-farm-client/ui
    RFC_PT_render_on_servers,
    RFC_PT_frame_range,
    RFC_PT_servers,
    RFC_PT_advanced,
    # render-farm-client/lib
    RFC_AP_preferences,
    SCENE_OT_report_error,
    SCENE_OT_close_report_error,
]
