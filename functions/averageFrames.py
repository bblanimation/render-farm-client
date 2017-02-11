#!/usr/bin/env python

import bpy, sys, os, numpy, fnmatch
from . import getRenderDumpFolder



def averageFrames(classObject, outputFileName, verbose=0):
    """ Averages final rendered images in blender to present one render result """

    if verbose >= 1:
        print("Averaging images...")

    # ensure renderedFramesPath has trailing "/"
    renderedFramesPath = getRenderDumpFolder()
    if not renderedFramesPath.endswith("/"):
        renderedFramesPath += "/"

    # get image files to average from 'renderedFramesPath'
    allFiles = os.listdir(renderedFramesPath)
    inFileName = "{outputFileName}_seed-*_{frame}{extension}".format(outputFileName=outputFileName, frame=str(bpy.props.imFrame).zfill(4), extension=bpy.props.imExtension)
    imListNames = [filename for filename in allFiles if fnmatch.fnmatch(filename, inFileName)]
    imList = [os.path.join(renderedFramesPath, im) for im in imListNames]
    if not imList:
        classObject.report({"ERROR"}, "No image files to average")

    # Assuming all images are the same size, get dimensions of first image
    imRef = bpy.data.images.load(imList[0])
    w = imRef.size[0]
    h = imRef.size[1]
    ch = imRef.channels
    alpha = (ch == 4)
    bpy.data.images.remove(imRef, do_unlink=True)
    if type(classObject.avDict["array"]) == numpy.ndarray:
        arr = classObject.avDict["array"]
    elif ch in [3, 4]:
        arr = numpy.zeros((w * h * ch), numpy.float)
    else:
        arr = numpy.zeros((w * h), numpy.float)
    N = len(imList) + classObject.avDict["numFrames"]

    # Build up average pixel intensities, casting each image as an array of floats
    if verbose >= 2:
        print("Averaging the following images:")

    for image in imList:
        if verbose >= 2:
            print(image)
        # load image
        im = bpy.data.images.load(image)
        data = list(im.pixels)
        imarr = numpy.array(data, dtype=numpy.float)
        arr = arr+imarr
        bpy.data.images.remove(im, do_unlink=True)

    classObject.avDict["numFrames"] = N
    classObject.avDict["array"] = arr

    arr = arr/N

    # Print details
    if verbose >= 1:
        print("Averaged successfully!")

    # Generate final averaged image, add it to the main database, and save it
    imName = "{outputFileName}_{frame}_average{extension}".format(outputFileName=outputFileName, frame=str(bpy.props.imFrame).zfill(4), extension=bpy.props.imExtension)
    if bpy.data.images.find(imName) < 0:
        new = bpy.data.images.new(imName, w, h, alpha)
    else:
        new = bpy.data.images[imName]
    new.pixels = arr.tolist()
    new.filepath_raw = "{renderedFramesPath}{imName}".format(renderedFramesPath=renderedFramesPath, imName=imName)
    new.save()
