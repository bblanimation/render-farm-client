import argparse, sys, os, numpy, PIL
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--project_path", help="Full path to Blender project file", action="store")
parser.add_argument("-n", "--project_name", help="Name of Blender project file", action="store")
args = parser.parse_args()

def averageFrames(projectPath, projectName):
    print "running averageFrames()... (currently only supports '.png' and '.tga')"
    allfiles=os.listdir(projectPath + "render-dump/")
    imlist=[filename for filename in allfiles if  (filename[-4:] in [".tga",".TGA"] and filename[-5] != "e" and "_seed-" in filename)]
    for i in range(len(imlist)):
        imlist[i] = projectPath + "render-dump/" + imlist[i]
    if len(imlist) == 0:
        print "There were no image files to average..."
        return;

    # Assuming all images are the same size, get dimensions of first image
    print "Averaging the following images:"
    for image in imlist:
        print image
    imRef = Image.open(imlist[0])
    w,h=imRef.size
    mode=imRef.mode
    N=len(imlist)

    # Create a numpy array of floats to store the average
    if mode == "RGB":
        arr=numpy.zeros((h,w,3),numpy.float)
    elif mode == "RGBA":
        arr=numpy.zeros((h,w,4),numpy.float)
    elif mode == "L":
        arr=numpy.zeros((h,w),numpy.float)
    else:
        print("ERROR: Unsupported image type. Supported types: ['RGB', 'RGBA', 'BW']")

    # Build up average pixel intensities, casting each image as an array of floats
    for im in imlist:
        # load image
        imarr=numpy.array(Image.open(im),dtype=numpy.float)
        arr=arr+imarr/N

    # Round values in array and cast as 8-bit integer
    arr=numpy.array(numpy.round(arr),dtype=numpy.uint8)

    # Print details
    print "Averaged successfully!"

    # Generate, save and preview final image
    out=Image.fromarray(arr,mode=mode)
    print "saving averaged image..."
    out.save(projectPath + "render-dump/" + projectName + "_average.tga")

def main():
    projectPath = args.project_path.replace(" ", "\\ ")
    projectName = args.project_name
    averageFrames(projectPath, projectName)

main()
