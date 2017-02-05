import argparse, sys, os, numpy
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--project_path", help="Full path to Blender project file", action="store")
parser.add_argument("-n", "--project_name", help="Name of Blender project file", action="store")
args = parser.parse_args()

def averageFrames(projectPath, projectName):
    """ Averages each pixel from all rendered images to present resulting render """

    print("running averageFrames()... (currently only supports '.png' and '.tga')")
    allFiles = os.listdir(os.path.join(projectPath, "render-dump/"))
    imList = [filename for filename in allFiles if (filename[-3:] in ["tga", "TGA", "png", "PNG"] and filename[-11:-4] != "average" and "_seed-" in filename)]
    imList = [os.path.join(projectPath, "render-dump", im) for im in imList]
    if not imList:
        sys.stderr.write("No valid image files to average.")
        sys.exit(1)
        
    # Assuming all images are the same size, get dimensions of first image
    imRef = Image.open(imlist[0])
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
    print("Averaging the following images:")
    for im in imList:
        # load image
        print(im)
        imarr = numpy.array(Image.open(im), dtype=numpy.float)
        arr = arr+imarr/N

    # Round values in array and cast as 8-bit integer
    arr = numpy.array(numpy.round(arr), dtype=numpy.uint8)

    # Print details
    print("Averaged successfully!")

    # Generate, save and preview final image
    out = Image.fromarray(arr, mode=mode)
    print("saving averaged image...")
    out.save(os.path.join(projectPath, "render-dump/", projectName, "_average.tga"))

def main():
    projectPath = args.project_path.replace(" ", "\\ ")
    projectName = args.project_name
    averageFrames(projectPath, projectName)

main()
