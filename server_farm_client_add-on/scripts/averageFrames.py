import argparse, sys, os, numpy, PIL
from PIL import Image

args = None

def ParseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--project_path", help="Full path to Blender project file", action="store_true")
    parser.add_argument("-n", "--project_name", help="Name of Blender project file", action="store_true")
    args = parser.parse_args()

def averageFrames(projectPath, projectName):
    print "running averageFrames()... (currently only supports '.png' and '.tga')"
    allfiles=os.listdir(projectPath + "render-dump/")
    imlist=[filename for filename in allfiles if  (filename[-4:] in [".tga",".TGA"] and filename[-5] != "e" and filename[:-10] == projectName + "_seed-")]
    for i in range(len(imlist)):
        imlist[i] = projectPath + "render-dump/" + imlist[i]

    if len(imlist) == 0:
        print "There were no image files to average..."
        return;

    # Assuming all images are the same size, get dimensions of first image
    print "Averaging the following images:"
    for image in imlist:
        print image
    w,h=Image.open(imlist[0]).size
    N=len(imlist)

    # Create a numpy array of floats to store the average (assume RGB images)
    arr=numpy.zeros((h,w,3),numpy.float)

    # Build up average pixel intensities, casting each image as an array of floats
    for im in imlist:
        # load image
        imarr=numpy.array(Image.open(im),dtype=numpy.float)
        try:
            arr=arr+imarr/N
        except:
            print "It seems your image may have an alpha value. This is not currently supported by this script; please either add support for alpha channels to the averageFrames() function, or try another image."

    # Round values in array and cast as 8-bit integer
    arr=numpy.array(numpy.round(arr),dtype=numpy.uint8)

    # Print details
    print "Averaged successfully!"

    # Generate, save and preview final image
    out=Image.fromarray(arr,mode="RGB")
    print "saving averaged image..."
    out.save(projectPath + "render-dump/" + projectName + "_average.tga")

def main():
    parseArgs()
    projectPath = args.project_path
    projectName = args.project_name
    averageFrames(projectPath, projectName)

main()
