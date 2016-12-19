#!/usr/bin/env python

import os
import sys
import json
import shlex
import subprocess
# import numpy
# import PIL
# from PIL import Image

def pflush(string):
    print(string)
    sys.stdout.flush()

def process_blender_output(hostname,line):
    # Parsing the following output
    matches = re.finditer(status_regex, line)
    mod     = 100
    for matchNum, match in enumerate(matches):
        matchNum = matchNum + 1
        frame = match.group(1)
        elapsed = match.group(2)
        remainingTime = match.group(3)
        json_obj = json.loads("{{ \"hn\" : \"{hostname}\", \"rt\" : \"{remainingTime}\", \"cf\" : \"{frame}\", \"et\" : \"{elapsed}\" }}".format( hostname=hostname ,elapsed = elapsed,frame = frame,remainingTime = remainingTime))

        if(hostname not in hostcount):
            hostcount[hostname] = 0

        currentCount = hostcount[hostname]
        if( currentCount % mod == 99 ):
            # We want this to go out over stdout
            print("##JSON##" + json.dumps(json_obj) + "##JSON##")

        hostcount[hostname] += 1
        sys.stdout.flush()

def ssh_string(username,hostname,verbose=False):
    tmpStr = "ssh -oStrictHostKeyChecking=no %s@%s" % (username,hostname)
    if( verbose >= 3 ):
        pflush(tmpStr)
    return tmpStr

def mkdir_string(path,verbose=False):
    tmpStr = "mkdir -p %s" % (path)
    if( verbose >= 3 ):
        pflush(tmpStr)
    return tmpStr

def rsync_files_to_node_string(projectFullPath,username,hostname,remoteFullPath,verbose=False):
    tmpStr = "rsync  -e 'ssh -oStrictHostKeyChecking=no'  -a %s %s@%s:%s/" % (projectFullPath,username,hostname,remoteFullPath)
    if( verbose >= 3 ):
        pflush(tmpStr)
    return tmpStr

def rsync_files_from_node_string(username,hostname,remoteProjectPath,projectName,projectOutuptFile,verbose=False):
    tmpStr = "rsync -atu --remove-source-files %s@%s:%s %s" % (username,hostname,remoteProjectPath,projectOutuptFile)
    if(verbose >= 3 ):
        pflush(tmpStr)
    return tmpStr

def start_tasks(
    projectName, projectPath,
    projectSyncPath, hostname,
    username, jobString,
    projectOutuptFile, remoteProjectPath,
    remoteSyncBack,
    progress=False, verbose=0 ):

    # First copy the files over using rsync
    rsync_to            = rsync_files_to_node_string( projectSyncPath, username, hostname, remoteProjectPath )
    rsync_from          = rsync_files_from_node_string( username, hostname, remoteSyncBack, projectName, projectOutuptFile )
    mkdir_local_string  = mkdir_string( projectPath )
    mkdir_remote_string = mkdir_string( remoteProjectPath + '/results' )
    ssh_c_string        = ssh_string( username, hostname )

    ssh_mkdir           = ssh_c_string + " '" + mkdir_remote_string + "'"
    ssh_blender         = ssh_c_string + " '" + jobString + "' "
    pull_from           = mkdir_remote_string + ";" + rsync_from

    run_status          = { 'p' : -1,'q' : -1,'r' : -1 }
    if(verbose >= 3):
        print("Syncing project file %s.blend to %s" % (projectName,hostname))
        print("rsync command: %s" % (rsync_to))
    t = subprocess.call(ssh_mkdir,shell=True )
    p = subprocess.call(rsync_to, shell=True)
    if( verbose >= 3 ):
        print("Finished the rsync to host %s" % (hostname))
    if( verbose >= 3 ):
        print("Returned from rsync command: %d" % (p))
        sys.stdout.flush()
    if(p == 0):
        run_status['p'] = 0
    else:
        run_status['p'] = 1
    # Now start the blender command
    if(verbose >= 3):
        print ( "blender command: %s" % (jobString))

    q = subprocess.Popen(shlex.split(ssh_blender),stdout=subprocess.PIPE)
    # This blocks til q is done
    while( type(q.poll()) == type(None) ):
        # This blocks til there is something to read
        line = q.stdout.readline()
        if( progress ):
            process_blender_output(hostname,line)

    # Successful blender
    if( q.returncode == 0 ):
        run_status['q'] = 0
        sys.stdout.flush()
    else:
        sys.stderr.write("blender error: %d" % (q.returncode))
        sys.stderr.flush()
        run_status['q'] = 1

    # Now rsync the files in /tmp/<name>/render back to this host.
    if( verbose >= 3 ):
        print("rsync pull: " + pull_from )
        sys.stdout.flush()

    r = subprocess.call(pull_from,shell=True)

    if( r == 0 and q.returncode == 0 ):
        run_status['r'] = 0
    else:
        sys.stderr.write("rsync error: %d" % (r))
        sys.stderr.flush()
        run_status['r'] = 1

    return run_status['p'] + run_status['q'] + run_status['r']

def buildJobStrings(frames,projectName,projectPath,nameOutputFiles,servers=1): # jobList is a list of lists containing start and end values
    jobStrings = []
    seedString = ""
    if(len(frames) == 1):
        # TODO: zero pad str(i) to three digits
        frame = frames[0]
        for i in range(servers):
            seedString = "_seed-" + str(i)
            builtString = "blender -b " + projectPath+"/"+projectName + ".blend -x 1 -o //results/" + nameOutputFiles + seedString + "_####.png -s " + str(frame) + " -e " + str(frame) + " -P " + projectPath + "/blender_p.py -a"
            jobStrings.append(builtString)
    else:
        for frame in frames:
            builtString = "blender -b " + projectPath+"/"+projectName + ".blend -x 1 -o //results/" + nameOutputFiles + "_####.png -s " + str(frame) + " -e " + str(frame) +  " -P " + projectPath + "/blender_p.py -a"
            jobStrings.append(builtString)
    return jobStrings

def expandFrames( frame_range ):
    # TODO: fix the start stop values and use frame_range
    frames = []
    sequential = False
    junk        = True
    for i in frame_range:
        if( type(i) == list ):
            frames += range(i[0],i[1]+1)
            if( junk ):
                sequential  = True
                junk        = False
        elif( type(i) == int ):
            frames.append(i)
            sequential = False
        else:
            sys.stderr.write("Unknown type in frames list")
            sys.stderr.flush()
    return frames


def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### BEGIN " + flagName + " ###\n"):
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            sys.stderr.write("Unable to read with over 250 preceeding lines.")
            sys.stderr.flush()
            break
    # read following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### END " + flagName + " ###\n"):
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 200:
            sys.stderr.write("Unable to read over 200 lines.")
            sys.stderr.flush()
            break
    return readLines

def setServersDict(hostDirPath="remoteServers.txt"):
    if(hostDirPath == "remoteServers.txt"):
        serverFile = open(os.path.dirname(os.path.abspath(__file__)) + "/remoteServers.txt",'r')
    else:
        serverFile = open(hostDirPath,'r')
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))
    return servers

def listHosts(hostDict):
    if(type(hostDict) == list):
        return hostDict
    return [ j for i in hostDict.keys() for j in hostDict[i] ]


def stopWatch(value):
    '''From seconds to Days;Hours:Minutes;Seconds'''

    valueD = (((value/365)/24)/60)
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

def averageFrames(renderedFramesPath, projectName):
    if( verbose >= 2 ):
        print "running averageFrames()... (currently only supports '.png' and '.tga')"

    # ensure 'renderedFramesPath' has trailing "/"
    if renderedFramesPath[-1] != "/":
        renderedFramesPath = renderedFramesPath + "/"

    # get image files to average from 'renderedFramesPath'
    allfiles=os.listdir(renderedFramesPath)
    imlist=[filename for filename in allfiles if  (filename[-4:] in [".tga",".TGA"] and filename[-5] != "e" and "_seed-" in filename)]
    for i in range(len(imlist)):
        imlist[i] = renderedFramesPath + imlist[i]
    if len(imlist) == 0:
        sys.stderr.write("There were no image files to average...")
        return;

    if ( verbose >= 3):
        print "Averaging the following images:"
        for image in imlist:
            print image

    # Assuming all images are the same size, get dimensions of first image
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
        sys.stderr.write("ERROR: Unsupported image type. Supported types: ['RGB', 'RGBA', 'BW']")
        sys.exit(0)

    # Build up average pixel intensities, casting each image as an array of floats
    for im in imlist:
        # load image
        imarr=numpy.array(Image.open(im),dtype=numpy.float)
        arr=arr+imarr/N

    # Round values in array and cast as 8-bit integer
    arr=numpy.array(numpy.round(arr),dtype=numpy.uint8)

    if ( verbose >= 3):
        print "Averaged successfully!"

    # Generate, save and preview final image
    out=Image.fromarray(arr,mode=mode)
    if ( verbose >= 3):
        print "saving averaged image..."
    out.save(renderedFramesPath + projectName + "_average.tga")
