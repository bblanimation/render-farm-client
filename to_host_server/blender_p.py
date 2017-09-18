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
import random
from bpy.app.handlers import persistent

scn = bpy.context.scene

""" BEGIN SUPPORT FOR THE LEGOIZER """

@persistent
def handle_legoizer_animation(scene):
    print("Adjusting frame")
    groupsToAdjust = {}
    for group in bpy.data.groups:
        if group.name.startswith("LEGOizer_") and "_bricks_frame_" in group.name:
            sourceName = group.name[9:(group.name.index("_bricks_frame_"))]
            if sourceName not in groupsToAdjust.keys():
                groupsToAdjust[sourceName] = [group.name]
            else:
                groupsToAdjust[sourceName].append(group.name)
    for sourceName in groupsToAdjust:
        groupsToAdjust[sourceName].sort()
        for i,gName in enumerate(groupsToAdjust[sourceName]):
            group = bpy.data.groups.get(gName)
            frame = int(group.name[(group.name.index("_bricks_frame_") + 14):])
            onCurF = frame == scn.frame_current
            beforeFirstF = (i == 0 and scn.frame_current < frame)
            afterLastF = (i == (len(groupsToAdjust[sourceName]) - 1) and scn.frame_current > frame)
            displayOnCurF = onCurF or beforeFirstF or afterLastF
            brick = group.objects[0]
            if brick.hide == displayOnCurF:
                brick.hide = not displayOnCurF
                brick.hide_render = not displayOnCurF

handle_legoizer_animation(scn)
bpy.app.handlers.render_pre.append(handle_legoizer_animation)
bpy.app.handlers.frame_change_pre.append(handle_legoizer_animation)

""" END SUPPORT FOR THE LEGOIZER """

randomSeed = random.randint(1, 10000)
for scene in bpy.data.scenes:
    scene.cycles.seed = randomSeed
    scene.cycles.transparent_min_bounces = 0
    scene.cycles.min_bounces = 0
    scene.cycles.blur_glossy = 0
    scene.render.use_overwrite = True
    if scene.cycles.film_transparent:
        scene.render.image_settings.color_mode = 'RGBA'
