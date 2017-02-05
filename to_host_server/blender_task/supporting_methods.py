#!/usr/bin/env python

import os
import sys
import json
import shlex
import subprocess
import re
import numpy
import PIL
from PIL import Image

def pflush(string):
    """ Helper function that prints and flushes a string """
    print(string)
    sys.stdout.flush()

def eflush(string):
    """ Helper function that prints and flushes a string """
    sys.stderr.write(string)
    sys.stderr.flush()

def process_blender_output(hostname, line):
    """ helper function to process blender output and print helpful json object """

    status_regex = r"Fra:(\d+)\s.*Time:(\d{2}:\d{2}\.\d{2}).*Remaining:(\d{2}:\d+\.\d+)\s.*"
    hostcount = {}

    # Parsing the following output
    matches = re.finditer(status_regex, line)
    mod = 100
    for matchNum, match in enumerate(matches):
        matchNum = matchNum + 1
        frame = match.group(1)
        elapsed = match.group(2)
        remainingTime = match.group(3)
        json_obj = json.loads("{{ \"hn\" : \"{hostname}\", \"rt\" : \"{remainingTime}\", \"cf\" : \"{frame}\", \"et\" : \"{elapsed}\" }}".format(hostname=hostname, elapsed=elapsed, frame=frame, remainingTime=remainingTime))

        if hostname not in hostcount:
            hostcount[hostname] = 0

        currentCount = hostcount[hostname]
        if currentCount % mod == 99:
            # We want this to go out over stdout
            pflush("##JSON##{jsonString}##JSON##".format(jsonString=json.dumps(json_obj)))

        hostcount[hostname] += 1

def ssh_string(username, hostname, verbose=0):
    tmpStr = "ssh -oStrictHostKeyChecking=no {username}@{hostname}".format(username=username, hostname=hostname)
    if verbose >= 3:
        pflush(tmpStr)
    return tmpStr

def mkdir_string(path, verbose=0):
    tmpStr = "mkdir -p {path}".format(path=path)
    if verbose >= 3:
        pflush(tmpStr)
    return tmpStr

def rsync_files_to_node_string(projectSyncPath, username, hostname, projectPath, verbose=0):

    tmpStr = "rsync -e 'ssh -oStrictHostKeyChecking=no' -a {projectSyncPath} {username}@{hostname}:{projectPath}/".format(projectSyncPath=projectSyncPath, username=username, hostname=hostname, projectPath=projectPath)
    if verbose >= 3:
        pflush(tmpStr)
    return tmpStr

def rsync_files_from_node_string(username, hostname, remoteResultsPath, localResultsPath, verbose=0):

    tmpStr = "rsync -atu --remove-source-files {username}@{hostname}:{remoteResultsPath} {localResultsPath}".format(username=username, hostname=hostname, remoteResultsPath=remoteResultsPath, localResultsPath=localResultsPath)
    if verbose >= 3:
        pflush(tmpStr)
    return tmpStr

def start_tasks(projectName, projectPath, projectSyncPath, hostname, username, jobString, remoteResultsPath, localResultsPath, frame=False, progress=False, verbose=0):
    """ Write tooltip here """

    if verbose >= 1 and frame:
        pflush("Starting thread. Rendering frame {frame} on {hostname}".format(frame=frame, hostname=hostname))

    # First copy the files over using rsync
    rsync_to            = rsync_files_to_node_string(projectSyncPath, username, hostname, projectPath, verbose)
    rsync_from          = rsync_files_from_node_string(username, hostname, remoteResultsPath, localResultsPath, verbose)
    mkdir_local_string  = mkdir_string(localResultsPath, verbose)
    mkdir_remote_string = mkdir_string(remoteResultsPath, verbose)
    ssh_c_string        = ssh_string(username, hostname, verbose)
    ssh_mkdir           = "{ssh_c_string} '{mkdir_remote_string}'".format(ssh_c_string=ssh_c_string, mkdir_remote_string=mkdir_remote_string)
    ssh_blender         = "{ssh_c_string} '{jobString}'".format(ssh_c_string=ssh_c_string, jobString=jobString)
    pull_from           = "{mkdir_local_string};{rsync_from}".format(mkdir_local_string=mkdir_local_string, rsync_from=rsync_from)
    run_status          = {"p":-1, "q":-1, "r":-1}

    if verbose >= 3:
        pflush("Syncing project file {projectName}.blend to {hostname}\nrsync command: {rsync_to}".format(projectName=projectName, hostname=hostname, rsync_to=rsync_to))
    t = subprocess.call(ssh_mkdir, shell=True)
    p = subprocess.call(rsync_to, shell=True)
    if verbose >= 3:
        pflush("Finished the rsync to host {hostname}".format(hostname=hostname))
    if verbose >= 3:
        pflush("Returned from rsync command: {p}".format(p=p))
        if p == 0: pflush("Success!")
    if p == 0:
        run_status["p"] = 0
    else:
        run_status["p"] = 1

    # Now start the blender command
    if verbose >= 3:
        pflush("blender command: {jobString}".format(jobString=jobString))

    q = subprocess.Popen(shlex.split(ssh_blender), stdout=subprocess.PIPE)
    # This blocks til q is done
    while type(q.poll()) == type(None):
        # This blocks til there is something to read
        line = q.stdout.readline()
        if progress:
            process_blender_output(hostname, line)

    # Successful blender
    if q.returncode == 0:
        run_status["q"] = 0

        if verbose >= 1 and frame:
            pflush("Successfully completed render for frame ({frame}) on hostname {hostname}.".format(frame=frame, hostname=hostname))
    else:
        eflush("blender error: {returncode}".format(returncode=q.returncode))
        run_status["q"] = 1


    # Now rsync the files in <remoteResultsPath> back to this host.
    if verbose >= 3:
        pflush("rsync pull: " + pull_from)
    r = subprocess.call(pull_from, shell=True)

    if r == 0 and q.returncode == 0:
        run_status["r"] = 0
        if verbose >= 1 and frame:
            pflush("Render frame ({frame}) has been copied back from hostname {hostname}".format(frame=frame, hostname=hostname))
    else:
        eflush("rsync error: {r}".format(r=r))
        run_status["r"] = 1

    return run_status["p"] + run_status["q"] + run_status["r"]

def buildJobStrings(frames, projectName, projectPath, nameOutputFiles, servers=1): # jobList is a list of lists containing start and end values
    """ Helper function to build Blender job strings to be sent to client servers """

    jobStrings = []
    seedString = ""
    if len(frames) == 1:
        # TODO: zero pad str(i) to three digits
        frame = frames[0]
        for i in range(servers):
            seedString = "_seed-" + str(i)
            builtString = "blender -b " + projectPath + "/" + projectName + ".blend -x 1 -o //results/" + nameOutputFiles + seedString + "_####.png -s " + str(frame) + " -e " + str(frame) + " -P " + projectPath + "/blender_p.py -a"
            jobStrings.append(builtString)
    else:
        for frame in frames:
            builtString = "blender -b " + projectPath + "/" + projectName + ".blend -x 1 -o //results/" + nameOutputFiles + "_####.png -s " + str(frame) + " -e " + str(frame) +  " -P " + projectPath + "/blender_p.py -a"
            jobStrings.append(builtString)
    return jobStrings

def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while nextLine != "### BEGIN " + flagName + " ###\n":
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            eflush("Unable to read with over 250 preceeding lines.")
            break
    # read following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while nextLine != "### END " + flagName + " ###\n":
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 200:
            eflush("Unable to read over 200 lines.")
            break
    return readLines

def setServersDict(hostDirPath="remoteServers.txt"):
    if hostDirPath == "remoteServers.txt":
        serverFile = open(os.path.dirname(os.path.abspath(__file__)) + "/remoteServers.txt", "r")
    else:
        serverFile = open(hostDirPath, "r")
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))
    return servers

def listHosts(hostDict):
    if type(hostDict) == list:
        return hostDict
    return [j for i in hostDict.keys() for j in hostDict[i]]

def stopWatch(value):
    """From seconds to Days;Hours:Minutes;Seconds"""

    valueD = ((value/365)/24)/60
    Days = int(valueD)

    valueH = (valueD-Days)*365
    Hours = int(valueH)

    valueM = (valueH - Hours)*24
    Minutes = int(valueM)

    valueS = (valueM - Minutes)*60
    Seconds = int(valueS)

    Days = str(Days)
    if len(Days) == 1:
        Days = "0" + Days
    Hours = str(Hours)
    if len(Hours) == 1:
        Hours = "0" + Hours
    Minutes = str(Minutes)
    if len(Minutes) == 1:
        Minutes = "0" + Minutes
    Seconds = str(Seconds)
    if len(Seconds) == 1:
        Seconds = "0" + Seconds

    return Days + ";" + Hours + ":" + Minutes + ";" + Seconds

def averageFrames(renderedFramesPath, projectName, verbose=0):
    """ Averages each pixel from all final rendered images to present one render result """

    if verbose >= 3:
        pflush("running averageFrames()... (currently only supports '.png' and '.tga')")

    # ensure 'renderedFramesPath' has trailing "/"
    if renderedFramesPath[-1] != "/":
        renderedFramesPath = renderedFramesPath + "/"

    # get image files to average from 'renderedFramesPath'
    allFiles = os.listdir(renderedFramesPath)
    imList = [filename for filename in allFiles if (filename[-3:] in ["tga", "png"] and filename[-11:-4] != "average" and "_seed-" in filename)]
    imList = [os.path.join(renderedFramesPath, im) for im in imList]
    if not imList:
        eflush("No valid image files to average.")
        sys.exit(1)

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
        eflush("Unsupported image type. Supported types: ['RGB', 'RGBA', 'BW']")
        sys.exit(1)

    # Build up average pixel intensities, casting each image as an array of floats
    if verbose >= 3:
        pflush("Averaging the following images:")
    for im in imList:
        if verbose >= 3:
            pflush(im)
        imarr = numpy.array(Image.open(im), dtype=numpy.float)
        arr = arr+imarr/N

    # Round values in array and cast as 8-bit integer
    arr = numpy.array(numpy.round(arr), dtype=numpy.uint8)

    # Print details
    if verbose >= 2:
        pflush("Averaged successfully!")

    # Generate, save and preview final image
    out = Image.fromarray(arr, mode=mode)
    if verbose >= 3:
        pflush("saving averaged image...")
    out.save(os.path.join(renderedFramesPath, projectName + "_average.tga"))
