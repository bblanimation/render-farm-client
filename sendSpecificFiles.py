#!/usr/bin/python

import subprocess
import sys
import telnetlib
import ast



# DEFAULTS
projectName = "rise_of_miniland_logo"
testing = False




def importCSE_HOSTS():
    try:
        f = open("CSE_HOSTS.txt", "r")
    except:
        print "Whoops! File could not be opened. Make sure 'CSE_HOSTS.txt' is in the same directory as this script file."

    CSE_HOSTS = ast.literal_eval(f.readline())

    f.close()

    return CSE_HOSTS


def getAvailableHosts(CSE_HOSTS):
    hosts       = []
    unreachable = []
    for hostGroupName in CSE_HOSTS:
        for host in CSE_HOSTS[hostGroupName]:
            try:
                tn = telnetlib.Telnet(host + ".cse.taylor.edu",22,.5)
                hosts.append(host)
            except:
                unreachable.append(host)
    return { 'hosts':hosts, 'unreachable':unreachable }

def handleArguments():
    global testing

    badValues = []

    #if no argument provided
    if (len(sys.argv) < 2 or (len(sys.argv) == 2 and "-t" in sys.argv[1])):
        print "ERROR: please provide a list of missing frames as an argument (excluding spaces). e.g. python sendSpecificFrames.py [1,8-10,34]"
        sys.exit()

    # if 1 argument provided (not including '-t')
    elif ((len(sys.argv) == 3 and "-t" in sys.argv[1]) or (len(sys.argv) == 2)):
        if len(sys.argv) == 2:
            frames = list(set(sys.argv[1].replace("[", "").replace("]", "").split(",")))
        else:
            testing = True
            frames = list(set(sys.argv[2].replace("[", "").replace("]", "").split(",")))

        #check to make sure argument list items are valid
        for i in range(len(frames)-1, -1, -1):
            # handles ranges in argument
            if "-" in frames[i]:
                rangeList = frames.pop(i).split("-")

                if len(rangeList) > 2: # if more than one '-' character provided in one list item
                    print "ERROR: There were too many dashes in one of your list items in the argument passed."
                else:
                    try:
                        # make sure the items are ints
                        rangeList[0] = int(rangeList[0])
                        rangeList[1] = int(rangeList[1])

                        # append values in range to original frames
                        for j in range(rangeList[0], rangeList[1]+1):
                            frames.append(j)
                    except:
                        badValues.append(rangeList)
                        print "BAD VALUE (removed from argument) => " + str(badValues[-1])

            else:
                try:
                    frames[i] = int(frames[i])
                except:
                    badValues.append(frames.pop(i))
                    print "BAD VALUE (removed from argument) => " + str(badValues[-1])

    # if >1 argument provided
    else:
        print "ERROR: Too many arguments. Please provide a list of missing frames as argument (excluding spaces)"
        sys.exit()

    frames.sort()

    return frames

def getAvailableHosts(CSE_HOSTS):
    hosts       = []
    unreachable = []
    for hostGroupName in CSE_HOSTS:
        for host in CSE_HOSTS[hostGroupName]:
            try:
                tn = telnetlib.Telnet(host + ".cse.taylor.edu",22,.5)
                hosts.append(host)
            except:
                unreachable.append(host)
    return { 'hosts':hosts, 'unreachable':unreachable }

"[1,3,10-25,83]"

[1,3,10,11,...,25,83]

def sendSpecificFrames(hosts, unreachable, frames):
    if testing:
        print "running sendSpecificFrames in TESTING mode..."
    else:
        print "running sendSpecificFrames..."
    print ""
    print "sending frames => " + str(frames)
    print ""
    print "Could not reach the following hosts:", str(unreachable)
    print "Using the following %d hosts:" %(len(hosts)), str(hosts)
    print ""
    print "Sending to hosts..."
    iterator = 0
    finished=False
    usedServers = []
    if len(frames) == 0:
        print "whoops! You passed an empty list.\n"
        sys.exit()
    for host in hosts:
        start = frames[iterator]
        end   = frames[iterator]
        print "starting frame " + str(start) + " - " + str(end) + " on " + host
        if not testing:
            subprocess.call("nohup ssh cgearhar@" + host + ".cse.taylor.edu 'cd /tmp/cgearhar/" + projectName + "; blender -b " + projectName + ".blend -x 1 -o //render/" + projectName + "_####.png -s " + str(start) + " -e " + str(end) + " -a;' > _sendSpecificFrames.out 2> _sendSpecificFrames.err < /dev/null &", shell=True)
        usedServers.append(host)
        if iterator >= len(frames)-1:
            finished=True
            break
        iterator += 1
    if finished:
        print "All frames sent!"
    else:
        print "the following frames were not sent to the render farm: [",
        for i in range( iterator+1, len(frames) ):
            print str(frames[i]) + ", ",
        print "\b\b\b ]"
    print ""
    print str(len(usedServers)) + " servers used: " + str(usedServers)
    print ""
    print "running renders in background. Track the render status in the '_sendSpecificFrames.out' and '_sendSpecificFrames.err' files."
    print ""

def main():
    CSE_HOSTS = importCSE_HOSTS()
    frames = handleArguments()
    hostDict = getAvailableHosts(CSE_HOSTS)
    sendSpecificFrames(hostDict['hosts'], hostDict['unreachable'], frames)

main()
