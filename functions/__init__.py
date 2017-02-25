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
import fnmatch
import itertools
import operator
import os
import subprocess
import sys
from .setupServers import *

def getFrames(projectName, archiveFiles=False, frameRange=False):
    """ rsync rendered frames from host server to local machine """
    scn = bpy.context.scene
    basePath = bpy.path.abspath("//")
    dumpLocation = getRenderDumpFolder()

    if archiveFiles:
        # move old render files to backup directory
        if frameRange:
            fileStrings = ""
            for frame in frameRange:
                fileStrings += "{nameOutputFiles}_{frameNum}{animExtension}\n".format(nameOutputFiles=getNameOutputFiles(), frameNum=str(frame).zfill(4), animExtension=bpy.props.animExtension)
            outFilePath = os.path.join(dumpLocation, "includeList.txt")
            f = open(outFilePath, "w")
            f.write(fileStrings)
            includeDict = "--include-from='{outFilePath}'".format(outFilePath=outFilePath)
            f.close()
        else:
            includeDict = ""
        archiveRsyncCommand = "rsync -qx --rsync-path='mkdir -p {dumpLocation}/backups/ && rsync' --remove-source-files {includeDict} --exclude='{nameOutputFiles}_????.???' '{dumpLocation}/*' '{dumpLocation}/backups/';".format(includeDict=includeDict, dumpLocation=dumpLocation, nameOutputFiles=getNameOutputFiles(), imExtension=bpy.props.imExtension)
    else:
        archiveRsyncCommand = "mkdir -p {dumpLocation};".format(dumpLocation=dumpLocation)

    # rsync files from host server to local directory
    fetchRsyncCommand = "rsync -x --progress --remove-source-files --exclude='*.blend' --exclude='*_average.???' -e 'ssh -T -oCompression=no -oStrictHostKeyChecking=no -x' '{login}:{remotePath}{projectName}/results/*' '{dumpLocation}/';".format(login=bpy.props.serverPrefs["login"], remotePath=bpy.props.serverPrefs["path"], projectName=projectName, dumpLocation=dumpLocation)

    # run the above processes
    process = subprocess.Popen(archiveRsyncCommand + fetchRsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def buildFrameRangesString(frameRanges):
    """ builds frame range list of lists/ints from user-entered frameRanges string """
    frameRangeList = frameRanges.replace(" ", "").split(",")
    newFrameRangeList = []
    invalidDict = {"valid":False, "string":None}
    for string in frameRangeList:
        try:
            newInt = int(string)
            if newInt >= 0 and newInt <= 500000:
                newFrameRangeList.append(newInt)
            else:
                return invalidDict
        except:
            if "-" in string:
                newString = string.split("-")
                if len(newString) != 2:
                    return invalidDict
                try:
                    newInt1 = int(newString[0])
                    newInt2 = int(newString[1])
                    if newInt1 <= newInt2 and newInt2 <= 500000:
                        newFrameRangeList.append([newInt1, newInt2])
                    else:
                        return invalidDict
                except:
                    return invalidDict
            else:
                return invalidDict
    return {"valid":True, "string":str(newFrameRangeList).replace(" ", "")}

def copyProjectFile(projectName, compress):
    """ copies project file from local machine to host server """
    scn = bpy.context.scene
    bpy.ops.file.pack_all()
    saveToPath = "{tempLocalDir}{projectName}.blend".format(tempLocalDir=scn.tempLocalDir, projectName=projectName)
    if compress:
        bpy.ops.wm.save_as_mainfile(filepath=saveToPath, compress=True, copy=True)
    else:
        bpy.ops.wm.save_as_mainfile(filepath=saveToPath, copy=True)

    # copies blender project file to host server
    rsyncCommand = "rsync --copy-links --progress --rsync-path='mkdir -p {remotePath}{projectName}/toRemote/ && rsync' -qazx --include={projectName}.blend --exclude='*' -e 'ssh -T -oCompression=no -oStrictHostKeyChecking=no -x' '{tempLocalDir}' '{login}:{remotePath}{projectName}/toRemote/'".format(remotePath=bpy.props.serverPrefs["path"], projectName=projectName, tempLocalDir=scn.tempLocalDir, login=bpy.props.serverPrefs["login"])
    process = subprocess.Popen(rsyncCommand, shell=True)
    return process

def copyFiles():
    """ copies necessary files to host server """
    scn = bpy.context.scene

    # write out the servers file for remote servers
    writeServersFile(bpy.props.serverPrefs["servers"], scn.serverGroups)

    # rsync setup files to host server ('servers.txt', 'blender_p.py', 'blender_task' module)
    rsyncCommand = "rsync -qax -e 'ssh -T -oCompression=no -oStrictHostKeyChecking=no -x' --rsync-path='mkdir -p {remotePath} && rsync' '{to_host_server}/' '{login}:{remotePath}'".format(remotePath=bpy.props.serverPrefs["path"], to_host_server=os.path.join(getLibraryPath(), "to_host_server"), login=bpy.props.serverPrefs["login"])
    process = subprocess.Popen(rsyncCommand, stdout=subprocess.PIPE, shell=True)
    return process

def renderFrames(frameRange, projectName, jobsPerFrame=False):
    """ calls 'blender_task' on host server """
    scn = bpy.context.scene
    # defines the name of the output files generated by 'blender_task'
    extraFlags = " -O {nameOutputFiles}".format(nameOutputFiles=getNameOutputFiles())

    if jobsPerFrame:
        extraFlags += " -j {jobsPerFrame}".format(jobsPerFrame=jobsPerFrame)
        extraFlags += " -s {numImSamples}".format(numImSamples=scn.samplesPerFrame)

    # runs blender command to render given range from the remote server
    renderCommand = "ssh -T -oStrictHostKeyChecking=no -x {login} 'python {remotePath}blender_task -v -p -n {projectName} -l {frameRange} --hosts_file {remotePath}servers.txt -R {remotePath} --connection_timeout {t} --max_server_load {maxServerLoad}{extraFlags}'".format(login=bpy.props.serverPrefs["login"], remotePath=bpy.props.serverPrefs["path"], projectName=projectName, frameRange=frameRange.replace(" ", ""), t=scn.timeout, maxServerLoad=str(scn.maxServerLoad), extraFlags=extraFlags)
    process = subprocess.Popen(renderCommand, stderr=subprocess.PIPE, shell=True)
    print("Process sent to remote servers!")
    return process

def setRenderStatus(key, status):
    bpy.context.scene.renderStatus[key] = status
    for a in bpy.context.screen.areas:
        a.tag_redraw()

def getRenderStatus(key):
    return bpy.context.scene.renderStatus[key]

def appendViewable(typeOfRender):
    if typeOfRender not in bpy.context.scene.renderType:
        bpy.context.scene.renderType.append(typeOfRender)

def removeViewable(typeOfRender):
    try:
        bpy.context.scene.renderType.remove(typeOfRender)
    except:
        return

def expandFrames(frame_range):
    """ Helper function takes frame range string and returns list with frame ranges expanded """
    frames = []
    for i in frame_range:
        if type(i) == list:
            frames += range(i[0], i[1]+1)
        elif type(i) == int:
            frames.append(i)
        else:
            sys.stderr.write("Unknown type in frames list")

    return list(set(frames))

def intsToFrameRanges(intsList):
    """ turns list of ints to list of frame ranges """
    frameRangesS = ""
    i = 0
    while i < len(intsList) - 1:
        s = intsList[i] # start index
        e = s           # end index
        while i < len(intsList) - 1 and intsList[i + 1] - intsList[i] == 1:
            e += 1
            i += 1
        frameRangesS += "{s},".format(s=s) if s == e else "{s}-{e},".format(s=s, e=e)
        i += 1
    return frameRangesS[:-1]

def listMissingFiles(filename, frameRange):
    """ lists all missing files from local render dump directory """
    dumpFolder = getRenderDumpFolder()
    compList = expandFrames(json.loads(frameRange))
    if not os.path.exists(dumpFolder):
        errorMsg = "The folder does not exist: {dumpFolder}/".format(dumpFolder=dumpFolder)
        sys.stderr.write(errorMsg)
        print(errorMsg)
        return str(compList)[1:-1]
    try:
        allFiles = os.listdir(dumpFolder)
    except:
        errorMsg = "Error listing directory {dumpFolder}/".format(dumpFolder=dumpFolder)
        sys.stderr.write(errorMsg)
        print(errorMsg)
        return str(compList)[1:-1]
    imList = []
    for f in allFiles:
        if "_average." not in f and not fnmatch.fnmatch(f, "*_seed-*_????.???") and f[:len(filename)] == filename:
            imList.append(int(f[len(filename)+1:len(filename)+5]))
    # compare lists to determine which frames are missing from imlist
    missingF = [i for i in compList if i not in imList]
    # convert list of ints to string with frame ranges
    missingFR = intsToFrameRanges(missingF)
    # return the list of missing frames as string, omitting the open and close brackets
    return missingFR

def handleError(classObject, errorSource, i="Not Provided"):
    errorMessage = False
    # if error message available, print in Info window and define errorMessage string
    if i == "Not Provided":
        if classObject.process.stderr != None:
            errorMessage = "Error message available in terminal/Info window."
            for line in classObject.process.stderr.readlines():
                classObject.report({"WARNING"}, str(line, "utf-8").replace("\n", ""))
        rCode = classObject.process.returncode
    else:
        if classObject.processes[i].stderr != None:
            errorMessage = "Error message available in terminal/Info window."
            for line in classObject.processes[i].stderr.readlines():
                classObject.report({"WARNING"}, str(line, "utf-8").replace("\n", ""))
        rCode = classObject.processes[i].returncode
    if not errorMessage:
        errorMessage = "No error message to print."

    classObject.report({"ERROR"}, "{errorSource} gave return code {returnCode}. {errorMessage}".format(errorSource=errorSource,returnCode=rCode-1, errorMessage=errorMessage))

def handleBTError(classObject, i="Not Provided"):
    if i == "Not Provided":
        classObject.stderr = classObject.process.stderr.readlines()
    else:
        classObject.stderr = classObject.processes[i].stderr.readlines()

    print("\nERRORS:")
    for line in classObject.stderr:
        line = line.decode("ASCII").replace("\\n", "")[:-1]
        errorMessage = "blender_task error: '{line}'".format(line=line)
        classObject.report({"ERROR"}, errorMessage)
        print(errorMessage)
        sys.stderr.write(line)
    errorMsg = classObject.stderr[-1].decode("ASCII")

def setFrameRangesDict(classObject):
    scn = bpy.context.scene
    if scn.frameRanges == "":
        classObject.frameRangesDict = {"string":"[[{frameStart},{frameEnd}]]".format(frameStart=str(scn.frame_start), frameEnd=str(scn.frame_end))}
    else:
        classObject.frameRangesDict = buildFrameRangesString(scn.frameRanges)
        if not classObject.frameRangesDict["valid"]:
            classObject.report({"ERROR"}, "ERROR: Invalid frame ranges given.")
            return False
    return True

def getRenderDumpFolder():
    dumpLoc = bpy.context.scene.renderDumpLoc
    # setup the render dump folder based on user input
    if dumpLoc.startswith("//"):
        dumpLoc = os.path.join(bpy.path.abspath("//"), dumpLoc[2:])
    elif dumpLoc != "":
        dumpLoc = dumpLoc[2:]
    # if no user input, use default render location
    else:
        dumpLoc = os.path.join(bpy.path.abspath("//"), "render-dump")
    # ensure it doesn't end in forwardslash
    if dumpLoc.endswith("/"):
        dumpLoc = dumpLoc[:-1]
    # TODO: Throw error if backslash found in path
    # check to make sure dumpLoc exists on local machine
    if not os.path.exists(dumpLoc):
        os.mkdir(dumpLoc)
    return dumpLoc

def getRunningStatuses():
    return ["Rendering...", "Preparing files...", "Finishing..."]

def getNameOutputFiles():
    """return nameOutputFiles, or current project name if nameOutputFiles not specified"""
    scn = bpy.context.scene
    if scn.nameOutputFiles != "":
        # remove illegal characters
        for char in " <>:\"'/|\?*.^":
            scn.nameOutputFiles = scn.nameOutputFiles.replace(char, "_")
        return scn.nameOutputFiles
    else:
        return bpy.path.display_name_from_filepath(bpy.data.filepath).replace(" ", "_")

def getNumRenderedFiles(jobType, frameRange=None, fileName=None):
    if jobType == "image":
        numRenderedFiles = len([f for f in os.listdir(getRenderDumpFolder()) if "_seed-" in f and f.endswith(str(frameRange[0]) + bpy.props.imExtension)])
    else:
        renderedFiles = []
        for f in os.listdir(getRenderDumpFolder()):
            try:
                frameNum = int(f[-8:-4])
            except:
                continue
            if frameNum in frameRange and fnmatch.fnmatch(f, "{fileName}_????{extension}".format(fileName=fileName, extension=bpy.props.animExtension)):
                renderedFiles.append(f)
        numRenderedFiles = len(renderedFiles)
    return numRenderedFiles

def cleanupCancelledRender(classObject, context, killPython=True):
    """ Kills running processes when render job cancelled """
    wm = context.window_manager
    wm.event_timer_remove(classObject._timer)
    for j in range(len(classObject.processes)):
        if classObject.processes[j]:
            try:
                classObject.processes[j].kill()
            except:
                pass
    if killPython:
        subprocess.call("ssh -T -oStrictHostKeyChecking=no -x {login} 'killall -9 python'".format(login=bpy.props.serverPrefs["login"]), shell=True)

def changeContext(context, areaType):
    """ Changes current context and returns previous area type """
    lastAreaType = context.area.type
    context.area.type = areaType
    return lastAreaType

def updateServerPrefs():
    # verify rsync is installed on local machine
    localVerify = subprocess.call("rsync --version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if localVerify > 0:
        return {"valid":False, "errorMessage":"rsync not installed on local machine."}

    # run setupServerPrefs() and store last results to oldServerPrefs
    oldServerPrefs = bpy.props.serverPrefs
    newServerPrefs = setupServerPrefs()
    if newServerPrefs["valid"]:
        bpy.props.serverPrefs = newServerPrefs
    else:
        return newServerPrefs

    # verify host server login, built from user entries, correspond to a responsive server, and that defined renderFarm path is writable
    rc = subprocess.call("ssh -T -oBatchMode=yes -oStrictHostKeyChecking=no -oConnectTimeout=10 -x {login} 'mkdir -p {remotePath}; touch {remotePath}test'".format(login=bpy.props.serverPrefs["login"], remotePath=bpy.props.serverPrefs["path"]), shell=True)
    if rc != 0:
        return {"valid":False, "errorMessage":"ssh to '{login}' failed (return code: {rc}). Check your settings, ensure ssh keys are setup, and verify your write permissions for '{remotePath}' (see error in terminal)".format(login=bpy.props.serverPrefs["login"], rc=rc, remotePath=bpy.props.serverPrefs["path"])}

    if bpy.props.serverPrefs != oldServerPrefs:
        # initialize server groups enum property
        groupNames = [("All Servers", "All Servers", "Render on all servers")]
        for groupName in bpy.props.serverPrefs["servers"]:
            tmpList = [groupName, groupName, "Render only servers in this group"]
            groupNames.append(tuple(tmpList))
        bpy.types.Scene.serverGroups = bpy.props.EnumProperty(
            attr="serverGroups",
            name="Servers",
            description="Choose which hosts to use for render processes",
            items=groupNames,
            default="All Servers")
    return {"valid":True, "errorMessage":None}
