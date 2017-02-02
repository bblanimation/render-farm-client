#!/usr/bin/env python

import bpy, subprocess, os, sys
from .setupServerVars import *

def jobIsValid(jobType, projectName):
    # verify that project has been saved
    if projectName == "":
        return {"valid":False, "errorType":"WARNING", "errorMessage":"RENDER FAILED: You have not saved your project file. Please save it before attempting to render."}

    # verify that project name contains no spaces
    elif " " in projectName:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER ABORTED: Please remove ' ' (spaces) from the project file name."}

    # verify that a camera exists in the scene
    elif bpy.context.scene.camera is None:
        return {"valid":False, "errorType":"ERROR", "errorMessage":"RENDER FAILED: No camera in scene."}

    # verify that sampling is high enough to provide expected results
    elif jobType == "image":
        if bpy.context.scene.cycles.progressive == 'PATH':
            samples = bpy.context.scene.cycles.samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 10:
                return {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at " + str(samples) + " samples. Try 10 or more samples for a more accurate render."}
            else:
                return {"valid":True, "errorType":None, "errorMessage":None}
        elif bpy.context.scene.cycles.progressive == 'BRANCHED_PATH':
            samples = bpy.context.scene.cycles.aa_samples
            if bpy.context.scene.cycles.use_square_samples:
                samples = samples**2
            if samples < 5:
                return {"valid":True, "errorType":"WARNING", "errorMessage":"RENDER ALERT: Render result may be inaccurate at " + str(samples) + " AA samples. Try 5 or more AA samples for a more accurate render."}
            else:
                return {"valid":True, "errorType":None, "errorMessage":None}
        else:
            return {"valid":True, "errorType":None, "errorMessage":None}
    else:
        return {"valid":True, "errorType":None, "errorMessage":None}

def getFrames(projectName):
    dumpLocation = bpy.path.abspath("//")+ "render-dump/"
    scn = bpy.context.scene

    # create backup directory
    mkdirCommand = "mkdir -p " + dumpLocation + "backups/;"
    # move old render files to backup directory
    archiveRsyncCommand = "rsync -qx --remove-source-files --exclude='" + projectName + "_average.*' " + dumpLocation + "* " + dumpLocation + "backups/;"
    # rsync files from host server to local directory
    fetchRsyncCommand = "rsync -x --progress --remove-source-files --exclude='*.blend' -e 'ssh -T -o Compression=no -x' '" + bpy.props.hostServerLogin + ":" + scn.tempFilePath + projectName + "/results/*' '" + dumpLocation + "';"

    # run the above processes
    process = subprocess.Popen(mkdirCommand + archiveRsyncCommand + fetchRsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def buildFrameRangesString(frameRanges):
    frameRangeList = frameRanges.replace(" ", "").split(",")
    newFrameRangeList = []
    invalidDict = { "valid":False, "string":None }
    for string in frameRangeList:
        try:
            newInt = int(string)
        except:
            if "-" in string:
                newString = string.split("-")
                if len(newString) > 2:
                    return invalidDict
                try:
                    newInt1 = int(newString[0])
                    newInt2 = int(newString[1])
                    if newInt1 <= newInt2:
                        newFrameRangeList.append([newInt1,newInt2])
                    else:
                        return invalidDict
                except:
                    return invalidDict
            else:
                return invalidDict
    return { "valid":True, "string":str(newFrameRangeList).replace(" ","") }

def copyProjectFile(projectName):
    scn = bpy.context.scene
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=scn.tempLocalDir + projectName + ".blend", copy=True)
    if scn.unpack:
        bpy.ops.file.unpack_all()

    # copies blender project file to host server
    rsyncCommand = "rsync --copy-links --progress --rsync-path='mkdir -p " + scn.tempFilePath + projectName + "/toRemote/ && rsync' -qazx --include=" + projectName + ".blend --exclude='*' -e 'ssh -T -o Compression=no -x' '" + scn.tempLocalDir + "' '" + bpy.props.hostServerLogin + ":" + scn.tempFilePath + projectName + "/toRemote/'"

    print("copying blender project files...")
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def copyFiles():
    scn = bpy.context.scene

    # copies necessary files to host server (currently unnecessary to run 'mkdir', as the functionality exists in 'copyProjectFile()')
    rsyncCommand = "rsync -qax -e 'ssh -T -o Compression=no -x' '" + os.path.join(getLibraryPath(), "to_host_server") + "/' '" + bpy.props.hostServerLogin + ":" + scn.tempFilePath + "'"

    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def renderFrames(frameRange, projectName, averageFrames=False):
    scn = bpy.context.scene
    extraFlags = ""

    # defines the name of the output files generated by 'blender_task'
    if scn.nameOutputFiles != "":
        extraFlags += " -O " + scn.nameOutputFiles

    # if rendering one frame, set '-a' flag to alert blender_task that we want an averaged result
    if averageFrames:
        extraFlags += " -a"

    # if the distribution type is split process, set the appropriate flag to alert blender_task of user setting
    if scn.distributionType == "Split Process":
        extraFlags += " -L"
    # else, show JSON progress objects
    else:
        extraFlags += " -p"

    # defines the project path on the host server if specified
    if scn.tempFilePath == "":
        scn.tempFilePath = "/tmp/"

    # runs blender command to render given range from the remote server
    renderCommand = "ssh -T -x " + bpy.props.hostServerLogin + " 'python " + scn.tempFilePath + "blender_task -v -n " + projectName + " -l " + frameRange + " --hosts_file " + scn.tempFilePath + "servers.txt -R " + scn.tempFilePath + " --max_server_load " + str(scn.maxServerLoad) + extraFlags + "'"
    print("Running command: " + renderCommand)

    print("Process sent to remote servers!\n")
    process = subprocess.Popen(renderCommand, stderr=subprocess.PIPE, shell=True)
    return process

def setRenderStatus(key, status):
    bpy.context.scene.renderStatus[key] = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getRenderStatus(key):
    return bpy.context.scene.renderStatus[key]

def appendViewable(typeOfRender):
    if(typeOfRender not in bpy.context.scene.renderType):
        bpy.context.scene.renderType.append(typeOfRender)

def expandFrames( frame_range ):
    frames = []
    for i in frame_range:
        if( type(i) == list ):
            frames += range(i[0],i[1]+1)
        elif( type(i) == int ):
            frames.append(i)
        else:
            sys.stderr.write("Unknown type in frames list")

    return list(set(frames))

def listMissingFiles(filename, frameRange):
    try:
        allfiles=os.listdir(bpy.path.abspath("//") + "render-dump/")
    except:
        sys.stderr.write("Error listing directory " + bpy.path.abspath("//") + "render-dump/. The folder may not exist.")
        return ""
    imlist = []
    for f in allfiles:
        if (f[-4:] in [".tga",".TGA"] and f[-5] != "e" and f[:len(filename)] == filename):
            imlist.append(int(f[len(filename)+1:len(filename)+5]))
    complist = expandFrames(json.loads(frameRange))

    # compare lists and determine which frames are missing from imlist
    missingF = []
    for i in complist:
        if i not in imlist:
            missingF.append(i)

    # return the list of missing frames as string, omitting the open and close brackets
    return str(missingF)[1:-1]
