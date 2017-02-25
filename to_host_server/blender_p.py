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

randomSeed = random.randint(1, 10000)

scn = bpy.context.scene

for scene in bpy.data.scenes:
    scene.cycles.seed = randomSeed
    scene.cycles.transparent_min_bounces = 0
    scene.cycles.min_bounces = 0
    scene.cycles.blur_glossy = 0
    scene.render.use_overwrite = True
    if scene.cycles.film_transparent:
        scene.render.image_settings.color_mode = 'RGBA'
