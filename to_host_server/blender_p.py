#!/usr/bin/python

import bpy
import sys
import random

randomSeed = random.randint(1, 10000)

scn = bpy.context.scene

for scene in bpy.data.scenes:
    scene.cycles.seed = randomSeed
    scene.cycles.transparent_min_bounces = 0
    scene.cycles.min_bounces = 0
    scene.cycles.blur_glossy = 0
    if scene.cycles.film_transparent:
        scene.color_mode = 'RGBA'
