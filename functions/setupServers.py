#!/usr/bin/env python

import bpy, os, json

def getLibraryPath():
    # Full path to module directory
    addons = bpy.context.user_preferences.addons

    functionsPath = os.path.dirname(os.path.abspath(__file__))
    libraryPath = functionsPath[:-10]

    if not os.path.exists(libraryPath):
        raise NameError("Did not find addon from path {libraryPath}".format(libraryPath=libraryPath))
    return libraryPath

def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while nextLine != "### BEGIN {flagName} ###\n".format(flagName=flagName):
        nextLine = f.readline()
        numIters += 1
        if numIters >= 300:
            print("Unable to read with over 300 preceeding lines.")
            break

    # read the following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while nextLine != "### END " + flagName + " ###\n":
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            print("Unable to read over 250 lines.")
            break

    return readLines

def setupServerPrefs():
    # Variable definitions
    libraryServersPath = os.path.join(getLibraryPath(), "servers")
    serverFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    # Set SSH login information for host server
    username = readFileFor(serverFile, "SSH USERNAME").replace("\"", "")
    hostServer = readFileFor(serverFile, "HOST SERVER").replace("\"", "")
    extension = readFileFor(serverFile, "EXTENSION").replace("\"", "")
    path = readFileFor(serverFile, "HOST SERVER PATH").replace("\"", "")
    login = "{username}@{hostServer}{extension}".format(username=username, hostServer=hostServer, extension=extension)
    hostConnection = "{hostServer}{extension}".format(hostServer=hostServer, extension=extension)

    # Format host server path
    path = path.replace(" ", "_")
    if not path.endswith("/"):
        path += "/"

    # Set server dictionary
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))
    return {"servers":servers, "login":login, "path":path, "hostConnection":hostConnection}

def writeServersFile(serverDict, serverGroups):
    f = open(os.path.join(getLibraryPath(), "to_host_server", "servers.txt"), "w")

    # define dictionary 'serversToUse'
    if serverGroups == "All Servers":
        serversToUse = serverDict
    else:
        serversToUse = {}
        serversToUse[serverGroups] = serverDict[serverGroups]

    # write dictionary 'serversToUse' to 'servers.txt'
    f.write("### BEGIN REMOTE SERVERS DICTIONARY ###\n")
    f.write(str(serversToUse).replace("'", "\"") + "\n")
    f.write("### END REMOTE SERVERS DICTIONARY ###\n")
