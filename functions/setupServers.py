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
            raise ValueError("Unable to find '### BEGIN {flagName} ###' in the first 300 lines of Remote Servers file".format(flagName=flagName))

    # read the following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while nextLine != "### END " + flagName + " ###\n":
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            print("Unable to read over 250 lines.")
            raise ValueError("'### END {flagName} ###' not found within 250 lines of '### BEGIN {flagName} ###' in the Remote Servers file".format(flagName=flagName))

    return readLines

def invalidEntry(field):
    return "Could not load '{field}'. Please read the instructions carefully to make sure you've set up your file correctly".format(field=field)

def setupServerPrefs():
    # variable definitions
    libraryServersPath = os.path.join(getLibraryPath(), "servers")
    serverFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    # set SSH login information for host server
    try:
        username = readFileFor(serverFile, "SSH USERNAME").replace("\"", "")
    except:
        return {"valid":False, "errorMessage":invalidEntry("SSH USERNAME")}
    try:
        hostServer = readFileFor(serverFile, "HOST SERVER").replace("\"", "")
    except:
        return {"valid":False, "errorMessage":invalidEntry("HOST SERVER")}
    try:
        extension = readFileFor(serverFile, "EXTENSION").replace("\"", "")
    except:
        return {"valid":False, "errorMessage":invalidEntry("EXTENSION")}
    try:
        email = readFileFor(serverFile, "EMAIL ADDRESS").replace("\"", "")
    except:
        return {"valid":False, "errorMessage":invalidEntry("EMAIL ADDRESS")}


    # build SSH login information
    login = "{username}@{hostServer}{extension}".format(username=username, hostServer=hostServer, extension=extension)
    hostConnection = "{hostServer}{extension}".format(hostServer=hostServer, extension=extension)

    # set base path for host server
    try:
        path = readFileFor(serverFile, "HOST SERVER PATH").replace("\"", "")
    except:
        return {"valid":False, "errorMessage":invalidEntry("HOST SERVER PATH")}

    # format host server path
    path = path.replace(" ", "_")
    if not path.endswith("/") and path != "":
        path += "/"

    # read file for servers dictionary
    try:
        tmpServers = readFileFor(serverFile, "REMOTE SERVERS DICTIONARY")
    except:
        return {"valid":False, "errorMessage":"Could not load 'REMOTE SERVERS DICTIONARY'. Please read the instructions carefully to make sure you've set up your file correctly"}

    # convert servers dictionary string to object
    try:
        servers = json.loads(tmpServers)
    except:
        return {"valid":False, "errorMessage":"Could not load dictionary. Please make sure you've entered a valid dictionary and check for syntax errors"}

    return {"valid":True, "servers":servers, "login":login, "path":path, "hostConnection":hostConnection, "email":email}

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
