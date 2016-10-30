#!/usr/bin/python

import subprocess
import sys

print "running 'sendToRenderFarm.py'..."

# Enter testing mode for default values
testing   = False
verbose   = False
recursive = False




# DEFAULTS
defaultBasePath       = "/Users/cgear13/Documents/filmmaking/files_for_render_farm/"
# create ssh redirect here so I can use this code remotely
defaultHostServer     = "cgearhar@asahel.cse.taylor.edu"
defaultServerFilePath = "/tmp/cgearhar/"

# GLOBAL VARIABLES
hostServer     = ""
projectName    = ""
projectPath    = ""
serverFilePath = ""
frameStart     = ""
frameEnd       = ""















# SETUP FUNCTIONS

def handleArgs():
    global testing
    global verbose
    global recursive

    args = ""
    for i in range(1, len(sys.argv)):
        curArg = sys.argv[-1]
        if (curArg[:1] != "-" or ("t" not in curArg and "v" not in curArg and "r" not in curArg)):
            print "'" + curArg + "' not allowed as an argument."
            print ""
            print "Accepted arguments:"
            print ">  -v  => run in verbose mode. In verbose mode, rsync files are called with -v, and blender_task.py (written by nwhite, stored on asahel) is called with -v."
            print ">  -t  => run in testing mode. In testing mode, nearly all inputs have non-destructive, non-taxing default values set for carriage return, and '_test.blend' is opened automatically."
            print ">  -r  => run in recursive mode. In recursive mode, getNewProjectFile searches through ~/filmmaking/, so that all respective '*.blend' files are available"
            print ""
            sys.exit()
        args += sys.argv.pop()

    if "t" in args: 
        testing = True
    if "v" in args:
        verbose = True
    if "r" in args:
        recursive = True




def setProjectFileOnOpen():
    global serverFilePath

    if testing:
        projectName = "_test.blend"
        serverFilePath = defaultServerFilePath + projectName[:-6] + "/"
        print ""
        return projectName

    else:
        return ""




def setServer():
    # set server to default server
    print "hostServer = "  + defaultHostServer + "\n"
    return defaultHostServer















# HELPERS

def getFrameStart():
    global frameStart
    while True:
        if testing:
            frameStart = raw_input("frame start => ")
            if frameStart == "":
                frameStart = 1
            elif frameStart == "m":
                runMainMenu()
                sys.exit()
        else: 
            frameStart = raw_input("frame start => ")
            if frameStart == "m":
                runMainMenu()
                sys.exit()
        try: 
            frameStart = int(frameStart)
            break;
        except ValueError:
            print "Whoops! That was no valid number. Try again..."
    return frameStart




def getFrameEnd():
    global frameEnd
    while True:
        if testing:
            frameEnd = raw_input("frame end => ")
            if frameEnd == "":
                frameEnd = 25
            elif frameEnd == "m":
                runMainMenu()
                sys.exit()
        else: 
            frameEnd = raw_input("frame end => ")
            if frameEnd == "m":
                runMainMenu()
                sys.exit()
        try: 
            frameEnd = int(frameEnd)
            break;
        except ValueError:
            print "Whoops! That was no valid number. Try again..."
    return frameEnd




def formatter(start, end):
    return '{}-{}'.format(start, end)
    



def re_range(lst):
    n = len(lst)
    result = []
    scan = 0
    while n - scan > 2:
        step = lst[scan + 1] - lst[scan]
        if (lst[scan + 2] - lst[scan + 1] != step or step > 1):
            result.append(str(lst[scan]))
            scan += 1
            continue

        for j in range(scan+2, n-1):
            if lst[j+1] - lst[j] != step:
                result.append(formatter(lst[scan], lst[j]))
                scan = j+1
                break
        else:
            result.append(formatter(lst[scan], lst[-1]))
            return ','.join(result)

    if n - scan == 1:
        result.append(str(lst[scan]))
    elif n - scan == 2:
        result.append(','.join(map(str, lst[scan:])))

    return ','.join(result)




def verifyFramesPresent(dumpLocation, boundsSpecified):

    # save list of render files to renderFilesList via the file 'renderFilesList.txt'
    subprocess.call("cd " + dumpLocation + ";ls | grep -v '.txt' > renderFilesList.txt", shell=True)
    f = open(dumpLocation + "renderFilesList.txt", "r")
    renderFilesList = f.read().splitlines()
    f.close() # close the file
    subprocess.call("cd " + dumpLocation + "; rm renderFilesList.txt", shell=True) # delete file we just created (no longer needed)
    if len(renderFilesList) == 0:
        print "no files present."
        return

    # trim the render file strings in renderFilesList to integers (e.g. 'demo_0001.png' becomes 1)
    for idx,string in enumerate(renderFilesList):
        renderFilesList[idx] = int(string.split('.')[0][-4:])

    # init skippedImages
    skippedFrames = []

    # append all frames excluded from renderFilesList to skippedFrames
    if not boundsSpecified:
        # append to skippedFrames any number excluded from list in its own bounds
        currentFrame = renderFilesList[0]
        for renderFrame in renderFilesList:
            while renderFrame != currentFrame:
                skippedFrames.append(currentFrame)
                currentFrame += 1
            currentFrame += 1
    else:
        # if frame starts line up, this for loop is skipped
        for i in range(frameStart,renderFilesList[0]):
            skippedFrames.append(i)
        
        # append to skippedFrames any number excluded from list in its own bounds
        currentFrame = renderFilesList[0]
        for renderFrame in renderFilesList:
            while renderFrame != currentFrame:
                skippedFrames.append(currentFrame)
                currentFrame += 1
            currentFrame += 1

        # if frame ends line up, this for loop is skipped
        for i in range(renderFilesList[-1] + 1,frameEnd):
            skippedFrames.append(i)
    skippedFrameRanges = re_range(skippedFrames).split(",")
    if len(skippedFrames) == 0:
        print "all render files seem to be present!"
    else:
        print "Missing frames: [",
        for frames in skippedFrameRanges:
            print str(frames) + ",",
        print "\b\b ]"




def chooseProjectFile(filesList):
    global projectName

    if len(filesList) == 1:
        userChoice = raw_input("Press ENTER to use project file '" + filesList[0] + "' => ")
        while ( userChoice != '' and userChoice != "m" ):
            userChoice = raw_input("Whoops! Press ENTER to confirm ('m' for main menu) => ")
        if userChoice == "m":
            runMainMenu()
            sys.exit()
        else:
            return 0

    elif len(filesList) > 1:
        # print out list of files in defaultBasePath to screen
        if recursive:
            print "files in '~/filmmaking/*'"
        else:
            print "files in '~/filmmaking/files_for_render_farm/'"
        for i,item in enumerate(filesList):
            print str(i+1) + ":  " + item

        # prompt user to choose a file
        print ""

        while True:
            userChoice = raw_input("USE FILE => ")
            if ( testing and userChoice == "" ):
                userChoice = 1
            try: 
                userChoice = int(userChoice)
                break;
            except ValueError:
                print "Whoops! That was no valid number. Try again..."
        while(userChoice > len(filesList) or userChoice == 0):
            print "Whoops! Index out of bounds. Try again..."
            while True:
                userChoice = raw_input("USE FILE (default=1) => ")
                if ( testing and userChoice == "" ):
                    userChoice = 1
                try: 
                    userChoice = int(userChoice)
                    break;
                except ValueError:
                    print "Whoops! That was no valid number. Try again..."

        return userChoice-1

    














# PRINCIPAL FUNCTIONS

def setProjectFile():
    global serverFilePath

    # save list of files in defaultBasePath to 'filesList.txt' and readlines into variable filesList
    subprocess.call("cd " + defaultBasePath + ";ls *.blend | grep -v '_test.blend' > filesList.txt", shell=True)
    f = open(defaultBasePath + "filesList.txt", "r")
    filesList = f.read().splitlines()
    # close 'filesList.txt' and delete it
    f.close()
    subprocess.call("cd " + defaultBasePath + "; rm filesList.txt", shell=True)
    if ( len(filesList) == 0 ):
        print "    please create dynamic link to your project file with the following command:"
        print "        =>  ln -s path/to/project.blend ~/filmmaking/files_for_render_farm/\n"
        print "run 'render' again once you've done this.\n"
        sys.exit()
    chosenIndex = chooseProjectFile(filesList)
    
    # set user choice to projectName
    projectName    = filesList[chosenIndex]
    if " " in projectName:
        if verbose:
            print "changing ' ' characters to '_' in source file"
        subprocess.call("cd " + defaultBasePath + ";mv " + projectName.replace(" ", "\ ") + " " + projectName.replace(" ", "_"), shell=True)
        projectName = projectName.replace(" ", "_")
    serverFilePath = defaultServerFilePath + projectName[:-6] + "/"

    print "using file '" + projectName + "'\n"
    return projectName




def setProjectFileRecursive():
    global serverFilePath
    global projectPath

    # save list of files in '~/filmmaking/' to 'defaultBasePath/filesPathsList.txt' and readlines into variable filesList
    subprocess.call("cd ~/filmmaking; find . -type f \( -name '*.blend' ! -name '_test.blend' \)  > " + defaultBasePath + "filesPathsList.txt", shell=True)
    f = open(defaultBasePath + "filesPathsList.txt", "r")
    filesPathsList = f.read().splitlines()
    filesList = []
    pathsList = []
    # close 'filesPathsList.txt' and delete it
    f.close()
    subprocess.call("cd " + defaultBasePath + "; rm filesPathsList.txt", shell=True)
    if ( len(filesPathsList) == 0 ):
        print "    please create dynamic link to your project file with the following command:"
        print "        =>  ln -s path/to/project.blend ~/filmmaking/files_for_render_farm/\n"
        print "run 'render' again once you've done this.\n"
        sys.exit()

    for i in range(len(filesPathsList)):
        filesPathsList[i] = "~/filmmaking/" + filesPathsList[i][2:]
        tempSplitPath = filesPathsList[i].split("/")
        filesList.append(tempSplitPath.pop())
        pathsList.append("")
        for item in tempSplitPath:
            pathsList[i] = pathsList[i] + item + "/"

    #change global variable for projectPath
    chosenIndex = chooseProjectFile(filesList)
    # set user choice to projectName

    projectName    = filesList[chosenIndex]
    projectPath    = pathsList[chosenIndex].replace(" ", "\ ")
    if " " in projectName:
        if verbose:
            print "changing ' ' characters to '_' in source file"
        subprocess.call("cd " + projectPath + ";mv " + projectName.replace(" ", "\ ") + " " + projectName.replace(" ", "_"), shell=True)
        projectName = projectName.replace(" ", "_")

    subprocess.call("cd " + defaultBasePath + "; ln -s " + projectPath + projectName  + " ./" + projectName,shell=True)
    serverFilePath = defaultServerFilePath + projectName[:-6] + "/"

    print "using file '" + projectName + "'\n"
    return projectName




def sendToHostServer():
    userChoice = "b"
    getFrameStart()
    getFrameEnd()
    numFrames = frameEnd - frameStart + 1
    userChoice = raw_input("Press ENTER to render " + str(numFrames) + " frames of '" + projectName[:-6] + "' => ")
    while ( userChoice != 'm' and userChoice != '' ):
        userChoice = raw_input("Whoops! Press ENTER to confirm ('m' for main menu) => ")
    if userChoice == 'm':
        return False
    print ""

    print "verifying remote directory..."
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    # set up project folder in remote server
    print "copying blender project files..."

    subprocess.call("rsync -a --copy-links '" + defaultBasePath + projectName + "' '" + hostServer + ":" + serverFilePath + projectName + "'", shell=True)
    print "rsync -v -a --copy-links '" + defaultBasePath + projectName + "' '" + hostServer + ":" + serverFilePath + projectName + "'"
    print ""

    # run blender command to render given range from the remote server
    print "opening connection to " + hostServer + "..."
    if verbose:
        subprocess.call("ssh " + hostServer + " 'blender_task.py -v -n " + projectName[:-6] + " -s " + str(frameStart) + " -e " + str(frameEnd) + "'", shell=True)
    else:
        subprocess.call("ssh " + hostServer + " 'blender_task.py -n " + projectName[:-6] + " -s " + str(frameStart) + " -e " + str(frameEnd) + "'", shell=True)

    return True




def getRenderFiles():
    dumpLocation   = defaultBasePath + "renderedFrames/" + projectName[:-6] + "/" # local directory
    if verbose:
        print dumpLocation

    print "verifying local directory..."
    subprocess.call("mkdir -p " + dumpLocation, shell=True)

    print "cleaning up local directory..."
    subprocess.call("find " + dumpLocation + ".. ! -name '" + projectName[:-6] + "' -empty -type d -delete", shell=True)

    print "verifying remote directory..."
    if verbose:
        print "ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'"
    subprocess.call("ssh " + hostServer + " 'mkdir -p " + serverFilePath + ";'", shell=True)

    print "copying files from server...\n"
    if verbose:
        print ""
    subprocess.call("rsync --exclude='*.blend' '" + hostServer + ":" + serverFilePath + "*' '" + dumpLocation + "'",shell=True)

    print "verifying all render frames present",
    if ( frameStart != "" and frameEnd != "" ):
        print "(" + str(frameStart) + "-" + str(frameEnd) + ")"
        boundsSpecified = True
    else:
        print "(no start frame or end frame specified)"
        boundsSpecified = False
    verifyFramesPresent(dumpLocation, boundsSpecified)




# def clearRenderFolder(forceClear=False):
#     global frameStart
#     global frameEnd
# 
#     if forceClear:
#         subprocess.call('''ssh ''' + hostServer + ''' "cd ''' + serverFilePath + '''; find . -type f ! -name '*.blend' -delete"''', shell=True)
#         frameStart = ""
#         frameEnd   = ""
#     else:
#         confirmation = raw_input( "Permanently delete all render files for project '" + projectName[:-6] + "' on " + defaultHostServer + "? [yes/no] => " )
#         while ( confirmation != "yes" and confirmation != "no" and confirmation != "" and confirmation != "m" ):
#             confirmation = raw_input("Whoops! Invalid input. Please enter 'yes' or 'no' => ")
#         if ( confirmation == "yes" ):
#             print "You brought this on yourself..."
#             print ""
#             print "cleaning render folder for '" + projectName[:-6] + "'..."
#             subprocess.call('''ssh ''' + hostServer + ''' "cd ''' + serverFilePath + '''; find . -type f ! -name '*.blend'; find . -type f ! -name '*.blend' -delete"''', shell=True)
#             frameStart = ""
#             frameEnd   = ""
#             return True
#         else:
#             return False














# MAIN MENU

def runMainMenu():
    global projectName
    
    continueRunning = True
    while(continueRunning):
        subprocess.call("clear", shell=True)
        print "\nMAIN MENU",
        if verbose or testing or recursive:
            print " (mode:",
        if verbose:
            print "-v",
        if testing:
            print "-t",
        if recursive:
            print "-r",
        if verbose or testing or recursive:
            print "\b)",
        print ""
        print "(press 'm' to return to main menu at any time)\n"
        print "Menu options:"
        print "1.   n: newProjectFile"
        print "2.   s: sendToRenderFarm (DEFAULT)"
        print "3.   g: getRenderFiles"
        print "4.   q: quit"
        if testing:
            print "5.   d: openDefaultFile"
        print ""
        if( projectName == "" ): print "no project file set."
        else:                    print "projectFile = " + projectName
        print ""
        menuSelection = raw_input("SELECT MENU OPTION => ")
        print ""
        if (menuSelection == "n" or menuSelection == "1"):
            print "running setProjectFile script...\n"
            if recursive:
                projectName = setProjectFileRecursive()
            else:
                projectName = setProjectFile()
            subprocess.call("clear", shell=True)
        elif (menuSelection == "s" or menuSelection == "" or menuSelection == "2" ):
            if projectName == "":
                projectName = setProjectFile()
            print "running sendToRenderFarm script..."
            if ( sendToHostServer() ):
                junk = raw_input("\nPress ENTER to get render files => ")
                while (junk != "" and junk != "m"):
                    junk = raw_input("\nWhoops! you entered '" + "'. Press ENTER to continue => ")
                if junk == "":
                    print "\nrunning getRenderFiles script..."
                    getRenderFiles()
                    if ( testing and projectName == "_test.blend"):
                        clearRenderFolder(True)
                        print "\nBecause this was a test, render files have been cleared from the server"
                    junk = raw_input("\nprocess completed. Press enter for main menu...")
            subprocess.call("clear", shell=True)
        elif (menuSelection == "g" or menuSelection == "3" ):
            if projectName == "":
                projectName = setProjectFile()
            print "running getRenderFiles script..."
            getRenderFiles()
            junk = raw_input("\nprocess completed. Press enter for main menu...")
            subprocess.call("clear", shell=True)
        elif (menuSelection == "q" or menuSelection == "4" ):
            continueRunning = False
        elif (testing and (menuSelection == "d" or menuSelection == "5") ):
            projectName = setProjectFileOnOpen()
        else:
            print "Whoops! Invalid input."















# MAIN

def main():
    global projectName
    global hostServer

    # if arguments were passed, handle them
    if len(sys.argv) > 1:
        handleArgs()
    
    # set up global variable "hostServer"
    hostServer = setServer()

    # for testing purposes for now... (in the future, it will automatically open last opened file)
    projectName = setProjectFileOnOpen()

    # open the main menu
    runMainMenu()

main()
