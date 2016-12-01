#!/usr/bin/env python

import bpy, os, json

def getLibraryPath():
    # Full path to "\addons\server_farm_client\" -directory
    paths = bpy.utils.script_paths("addons")

    libraryPath = 'assets'
    for path in paths:
        libraryPath = os.path.join(path, "server_farm_client_add_on")
        if os.path.exists(libraryPath):
            break

    if not os.path.exists(libraryPath):
        raise NameError('Did not find assets path from ' + libraryPath)
    return libraryPath

def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### BEGIN " + flagName + " ###\n"):
        nextLine = f.readline()
        numIters += 1
        if numIters >= 300:
            print("Unable to read with over 300 preceeding lines.")
            break

    # read following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### END " + flagName + " ###\n"):
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            print("Unable to read over 250 lines.")
            break

    return readLines

def setupServerVars():
    # Variable definitions
    libraryServersPath = os.path.join(getLibraryPath(), "servers")
    serverFile = open(os.path.join(libraryServersPath, "remoteServers.txt"),"r")

    # Set SSH login information for host server
    username    = readFileFor(serverFile, "SSH USERNAME").replace("\"", "")
    hostServer  = readFileFor(serverFile, "HOST SERVER").replace("\"", "")
    extension   = readFileFor(serverFile, "EXTENSION").replace("\"", "")
    hostServerLogin = username + "@" + hostServer + extension

    # Set server dictionary
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))
    return { "servers":servers, "hostServerLogin":hostServerLogin }

def writeServersFile(serverDict, serverGroups):
    f = open(os.path.join(getLibraryPath(), "to_host_server", "servers.txt"), "w")
    # define serversToUse
    if(serverGroups == "All Servers"):
        serversToUse = serverDict
    else:
        serversToUse = {}
        serversToUse[serverGroups] = serverDict[serverGroups]
    f.write("### BEGIN REMOTE SERVERS DICTIONARY ###\n")
    f.write(str(serversToUse).replace("'", "\"") + "\n")
    f.write("### END REMOTE SERVERS DICTIONARY ###\n")
