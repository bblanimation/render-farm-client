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

def jobIsValid(jobType, classObject):
    """ verifies that the job is valid before sending it to the host server """

    jobValidityDict = False

    # verify that project has been saved
    if classObject.projectName == "":
        jobValidityDict = {"valid":False, "errorType":"WARNING", "errorMessage":"RENDER FAILED: You have not saved your project file. Please save it before attempting to render."}

    # verify that a camera exists in the scene
    elif bpy.context.scene.camera is None:
        jobValidityDict = {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: No camera in scene."}

    # verify image file format
    unsupportedFormats = ["AVI_JPEG", "AVI_RAW", "FRAMESERVER", "H264", "FFMPEG", "THEORA", "QUICKTIME", "XVID"]
    if not jobValidityDict and bpy.context.scene.render.image_settings.file_format in unsupportedFormats:
        jobValidityDict = {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: Output file format not supported. Supported formats: BMP, PNG, TARGA, JPEG, JPEG 2000, TIFF. (Animation only: IRIS, CINEON, HDR, DPX, OPEN_EXR, OPEN_EXR_MULTILAYER)"}

    # verify that sampling is high enough to provide expected results
    if not jobValidityDict and jobType == "image":
        if bpy.context.scene.cycles.progressive == "PATH":
            samples = bpy.context.scene.cycles.samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 10:
                jobValidityDict = {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at {samples} samples. Try 10 or more samples for a more accurate render.".format(samples=str(samples))}
        elif bpy.context.scene.cycles.progressive == "BRANCHED_PATH":
            samples = bpy.context.scene.cycles.aa_samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 5:
                jobValidityDict = {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at {samples} AA samples. Try 5 or more AA samples for a more accurate render.".format(samples=str(samples))}

    # else, the job is valid
    if not jobValidityDict:
        jobValidityDict = {"valid":True, "errorType":None, "errorMessage":None}

    # if error detected, report error in Blender UI
    if jobValidityDict["errorType"] != None:
        classObject.report({jobValidityDict["errorType"]}, jobValidityDict["errorMessage"])
    # else alert user that render job has started
    else:
        if jobType == "image":
            classObject.report({"INFO"}, "Rendering current frame on {numAvailable} servers (Preview with 'SHIFT + P')".format(numAvailable=str(bpy.context.scene.availableServers)))
        else:
            classObject.report({"INFO"}, "Rendering animation on {numAvailable} servers (Check status with 'SHIFT + P')".format(numAvailable=str(bpy.context.scene.availableServers)))

    # if job is invalid, return false
    if not jobValidityDict["valid"]:
        return False

    # job is valid, return true
    return True
