#!/usr/bin/python

import bpy
import sys
import random

randomSeed = random.randint(1, 10000)

for scene in bpy.data.scenes:
    scene.cycles.seed = randomSeed
    scene.cycles.transparent_min_bounces = 0
    scene.cycles.min_bounces = 0
    scene.cycles.blur_glossy = 0
    scene.render.image_settings.file_format = 'TARGA'
    if scene.cycles.film_transparent:
        scene.color_mode = 'RGBA'
