#!/usr/bin/env python

import argparse, sys, os, numpy
from PIL import Image
from VerboseAction import verbose_action

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path_to_images", help="Full path to Blender project file", action="store")
parser.add_argument("-n", "--project_name", help="Name of Blender project file", action="store")
parser.add_argument("-v", "--verbose", action=verbose_action, nargs="?", default=0)
args = parser.parse_args()

def averageFrames(renderedFramesPath, projectName, verbose=0):
    """ Averages each pixel from all final rendered images to present one render result """

    if verbose >= 3:
        print("Averaging images...")

    # ensure 'renderedFramesPath' has trailing "/"
    if not renderedFramesPath.endswith("/"):
        renderedFramesPath += "/"

    # get image files to average from 'renderedFramesPath'
    allFiles = os.listdir(renderedFramesPath)
    supportedFileTypes = ["png", "tga", "tif", "jpg", "jp2", "bmp"]
    imList = [filename for filename in allFiles if (filename[-3:] in supportedFileTypes and filename[-11:-4] != "average" and "_seed-" in filename)]
    imList = [os.path.join(renderedFramesPath, im) for im in imList]
    if not imList:
        sys.stderr.write("No valid image files to average.")
        sys.exit(1)
    extension = imList[0][-3:]

    # Assuming all images are the same size, get dimensions of first image
    imRef = Image.open(imList[0])
    w, h = imRef.size
    mode = imRef.mode
    N = len(imList)

    # Create a numpy array of floats to store the average
    if mode == "RGB":
        arr = numpy.zeros((h, w, 3), numpy.float)
    elif mode == "RGBA":
        arr = numpy.zeros((h, w, 4), numpy.float)
    elif mode == "L":
        arr = numpy.zeros((h, w), numpy.float)
    else:
        sys.stderr.write("Unsupported image type. Supported types: ['RGB', 'RGBA', 'BW']")
        sys.exit(1)

    # Build up average pixel intensities, casting each image as an array of floats
    if verbose >= 3:
        print("Averaging the following images:")
    for im in imList:
        # load image
        if verbose >= 3:
            print(im)
        imarr = numpy.array(Image.open(im), dtype=numpy.float)
        arr = arr+imarr/N

    # Round values in array and cast as 8-bit integer
    arr = numpy.array(numpy.round(arr), dtype=numpy.uint8)

    # Print details
    if verbose >= 2:
        print("Averaged successfully!")

    # Generate, save and preview final image
    out = Image.fromarray(arr, mode=mode)
    if verbose >= 3:
        pflush("saving averaged image...")
    out.save(os.path.join(renderedFramesPath, "{projectName}_average.{extension}".format(extension=extension, projectName=projectName)))

def main():
    renderedFramesPath = args.path_to_images.replace(" ", "\\ ")
    projectName = args.project_name
    verbose = args.verbose
    averageFrames(renderedFramesPath, projectName, verbose)

main()
