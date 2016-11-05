#!/usr/bin/python

import bpy
import sys
import random

randomSeed = random.randint(1, 10000)

for scene in bpy.data.scenes:
    scene.cycles.seed = randomSeed
    scene.render.image_settings.file_format = 'TARGA'
