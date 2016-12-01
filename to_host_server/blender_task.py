#!/usr/bin/env python

from __future__ import print_function
import argparse
import os,getpass,sys
import subprocess
import threading
import telnetlib
import json
import re
import fnmatch
import shlex
import time

def pflush(string):
    print(string)
    sys.stdout.flush()

# Thanks to: http://stackoverflow.com/questions/6076690/verbose-level-with-argparse-and-multiple-v-options
class verbose_action(argparse.Action):
    def __call__(self,parser,args,values,options_string=None):
        if(values==None):
            values='1'
        try:
            values = int(values)
        except ValueError:
            values = values.count('v')+1
        setattr(args,self.dest,values)

# class HostThread(threading.Thread):
#     def __init__(self,group=None, target=None, name=None, args=(), kwargs=None, verbose=None, post=post):
#         threading.Thread.__init__(self, group=group, target=target, name=name, verbose=verbose)
#         self.post = post
#
#     def run(self):
#         super(HostThread,self).run()
#         if(callable(self.post)):
#             self.post()
#         print("Finished Running thread!")
#         return
#
# class hostThreadsCollection():
#     def __init__(self, post=None ):
#         # If post and target are passed, these are the callbacks that will be set up as new threasds are passed
#         self.post = post
#         self.target = self.complete
#         self.hosts = {}
#
#     def add_host(hostname):
#         pass
#
#     def host_start(hostname):
#         pass
#
#     def host_running():
#         pass
#
#     def host_availible(hostname):
#         return False

def readFileFor(f, flagName):
    readLines = ""

    # skip lines leading up to '### BEGIN flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### BEGIN " + flagName + " ###\n"):
        nextLine = f.readline()
        numIters += 1
        if numIters >= 250:
            print("Unable to read with over 250 preceeding lines.")
            break
    # read following lines leading up to '### END flagName ###'
    nextLine = f.readline()
    numIters = 0
    while(nextLine != "### END " + flagName + " ###\n"):
        readLines += nextLine.replace(" ", "").replace("\n", "").replace("\t", "")
        nextLine = f.readline()
        numIters += 1
        if numIters >= 200:
            print("Unable to read over 200 lines.")
            break
    return readLines

def setServersDict(hostDirPath="remoteServers.txt"):
    if(hostDirPath == "remoteServers.txt"):
        serverFile = open(os.path.dirname(os.path.abspath(__file__)) + "/remoteServers.txt",'r')
    else:
        serverFile = open(hostDirPath,'r')
    servers = json.loads(readFileFor(serverFile, "REMOTE SERVERS DICTIONARY"))
    return servers

parser = argparse.ArgumentParser()

parser.add_argument('-l','--frame_range',action='store',default="[]")

# Takes a string dictionary of hosts
# If neither of these arguments are provided, then use the default hosts file to load hosts
parser.add_argument('-a','--hosts',action='store',default=None,help='Pass a dictionary or list of hosts. Should be valid json.')
parser.add_argument('-H','--hosts_online',action='store_true',default=None,help='Telnets to ports to find out if a host is availible to ssh into.')
parser.add_argument('-i','--hosts_file',action='store',default='remoteServers.txt',help='Pass a filename from which to load hosts. Should be valid json format.')

# NOTE: this parameter is currently required
parser.add_argument('-n','--project_name',action='store',default=False) # just project name. default path will be in /tmp/blenderProjects
# TODO: test this for directories other than toRemote
parser.add_argument('-s','--local_sync',action='store',default='./toRemote',help='Pass a full path or relative path to sync to the project directory on remote.')

# NOTE: remote_sync will sync the directory at results
parser.add_argument('-r','--remote_sync',action='store',default='results',help='Pass a path to the directory that should be synced back.')
# NOTE: passing the contents flag will sync back the contents from the directory given in remote_sync
parser.add_argument('-c','--contents',action='store_true',default=False,help='Pass a path to the directory that should be synced back.')

parser.add_argument('-C','--command',action='store',help='Run the command on the remote host.')

parser.add_argument('-o','--output_file',action='store',default=False,help='Local file to rsync files back into when done')
parser.add_argument('-v','--verbose',action=verbose_action,nargs='?',default=0)
parser.add_argument('-p','--progress',action='store_true',help='Prints the progress to stdout as a json object.')

HOSTS = {    'cse103group': [   'cse10301','cse10302','cse10303','cse10304','cse10305','cse10306','cse10307',
                                'cse10309','cse10310','cse10311','cse10312','cse10315','cse10316','cse10317',
                                'cse10318','cse10319','cse103podium'
                            ],
            'cse201group':  [   'cse20101','cse20102','cse20103','cse20104','cse20105','cse20106','cse20107',
                                'cse20108','cse20109','cse20110','cse20111','cse20112','cse20113','cse20114',
                                'cse20116','cse20117','cse20118','cse20119','cse20120','cse20121','cse20122',
                                'cse20123','cse20124','cse20125','cse20126','cse20127','cse20128','cse20129',
                                'cse20130','cse20131','cse20132','cse20133','cse20134','cse20135','cse20136'
                            ],
            'cse21801group':[  'cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807',
                               'cse21808','cse21809','cse21810','cse21811','cse21812'
                            ],
            'cse217group' : [   'cse21701','cse21702','cse21703','cse21704','cse21705','cse21706','cse21707',
                                'cse21708','cse21709','cse21710','cse21711','cse21712','cse21713','cse21714',
                                'cse21715','cse21716'
                            ]
}

status_regex = r"Fra:(\d+)\s.*Time:(\d{2}:\d{2}\.\d{2}).*Remaining:(\d{2}:\d+\.\d+)\s.*"

hostcount = {}
def process_blender_output(hostname,line):
    # Parsing the following output
    matches = re.finditer(status_regex, line)
    mod     = 100
    for matchNum, match in enumerate(matches):
        matchNum = matchNum + 1
        frame = match.group(1)
        elapsed = match.group(2)
        remainingTime = match.group(3)
        json_obj = json.loads("{{ \"{hostname}\" : {{ \"rt\" : \"{remainingTime}\", \"cf\" : \"{frame}\", \"et\" : \"{elapsed}\" }} }}".format( hostname=hostname ,elapsed = elapsed,frame = frame,remainingTime = remainingTime))

        if(hostname not in hostcount):
            hostcount[hostname] = 0

        currentCount = hostcount[hostname]
        if( currentCount % mod == 99 ):
            # We want this to go out over stdout
            print("##JSON##" + json.dumps(json_obj) + "##JSON##")

        hostcount[hostname] += 1
        sys.stdout.flush()

def get_hosts(groupName=None,hosts=None):
    global HOSTS
    if(groupName):
        return HOSTS[groupName]
    elif(hosts):
        return [ i for k in HOSTS.keys() for i in hosts[k]]
    else:
        return [ i for k in HOSTS.keys() for i in HOSTS[k]]

def ssh_string(username,hostname,verbose=False):
    tmpStr = "ssh -oStrictHostKeyChecking=no %s@%s" % (username,hostname)
    if( verbose >= 2 ):
        pflush(tmpStr)
    return tmpStr

def mkdir_string(path,verbose=False):
    tmpStr = "mkdir -p %s" % (path)
    if( verbose >= 2 ):
        pflush(tmpStr)
    return tmpStr

def rsync_files_to_node_string(projectFullPath,username,hostname,remoteProjectPath,verbose=False):
    tmpStr = "rsync  -e 'ssh -oStrictHostKeyChecking=no' -a %s %s@%s:%s/" % (projectFullPath,username,hostname,remoteProjectPath)
    if( verbose >= 2 ):
        pflush(tmpStr)
    return tmpStr

def rsync_files_from_node_string(username,hostname,remoteProjectPath,projectName,projectOutuptFile,verbose=False):
    tmpStr = "rsync -atu --remove-source-files %s@%s:%s %s." % (username,hostname,remoteProjectPath,projectOutuptFile)
    if(verbose >= 2):
        pflush(tmpStr)
    return tmpStr

def start_blender_tasks(
    projectName, projectPath,
    projectSyncPath, hostname,
    username, jobString,
    projectOutuptFile, jobStatus,
    remoteProjectPath, frame,
    remoteSyncBack, progress=False,
    verbose=0 ):

    pflush("Starting thread. Rendering frame %s on %s" % (frame,hostname))
    # First copy the files over using rsync
    rsync_to            = rsync_files_to_node_string( projectSyncPath, username, hostname, remoteProjectPath )
    rsync_from          = rsync_files_from_node_string( username, hostname, remoteSyncBack, projectName, projectOutuptFile )
    mkdir_local_string  = mkdir_string( projectPath )
    mkdir_remote_string = mkdir_string( remoteProjectPath + '/results' )
    ssh_c_string        = ssh_string( username, hostname )

    ssh_mkdir           = ssh_c_string + " '" + mkdir_remote_string + "'"
    ssh_blender         = ssh_c_string + " '" + jobString + "' "
    pull_from           = mkdir_remote_string + ";" + rsync_from

    if(verbose >= 2):
        print("Syncing project file %s.blend to %s" % (projectName,hostname))
        print("rsync command: %s" % (rsync_to))
    t = subprocess.call(ssh_mkdir,shell=True )
    p = subprocess.call(rsync_to, shell=True)
    if(verbose >= 2):
        print("Finished the rsync to host %s" % (hostname))
    if(verbose >= 2):
        print("Returned from rsync command: %d" % (p))
        sys.stdout.flush()
        if(p == 0): print ("Success!")
    # Now start the blender command

    if(verbose >= 2):
        print ( "blender command: %s" % (jobString))

    q = subprocess.Popen(shlex.split(ssh_blender),stdout=subprocess.PIPE)
    # This blocks til q is done
    while(type(q.poll()) == type(None)):
        # This blocks til there is something to read
        line = q.stdout.readline()
        if( progress ):
            process_blender_output(hostname,line)

    if( q.returncode == 0 ):
        print ("Successfully completed render for frame (%s) on hostname %s." % (frame,hostname))
        jobStatus[jobString] = dict()
        jobStatus[jobString]['blend'] = 0
        sys.stdout.flush()
    else:
        print("blender error: %d" % (q.returncode))
    # Now rsync the files in /tmp/<name>/render back to this host.

    if( verbose >= 2 ):
        print("rsync pull: " + pull_from )
    r = subprocess.call(pull_from,shell=True)

    if( r == 0 and q.returncode == 0 ):
        jobStatus[jobString]['rsync'] = 0
        print( "Render frame (%s) has been copied back from hostname %s" % (frame,hostname))
        sys.stdout.flush()
    else:
        print("rsync error: %d" % (r))

def buildJobStrings(frames,pathToProjectFiles,projectName,username,servers=1): # jobList is a list of lists containing start and end values
    jobStrings = []
    seedString = ""
    if(len(frames) == 1):
        # TODO: zero pad str(i) to three digits
        frame = frames[0]
        for i in range(servers):
            seedString = "_seed-" + str(i)
            builtString = "blender -b " + pathToProjectFiles + projectName + ".blend -x 1 -o //results/" + projectName + seedString + "_####.png -s " + str(frame) + " -e " + str(frame) + " -P  '" + pathToProjectFiles + "blender_p.py' -a"
            jobStrings.append(builtString)
    else:
        for frame in frames:
            builtString = "blender -b " + pathToProjectFiles + projectName + ".blend -x 1 -o //results/" + projectName + "_####.png -s " + str(frame) + " -e " + str(frame) +  " -P  '" + pathToProjectFiles + "blender_p.py' -a"
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
            print("Unknown type in frames list")

    return frames

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

def hostsStatus(hosts_file=None,hosts=None,hosts_online=False,verbose=False):
    global HOSTS # Using the global HOSTS variable
    if( hosts ):
        HOSTS = json.loads(args.hosts)
    elif( hosts_file ):
        HOSTS = setServersDict( hosts_file )
    jobs            = []
    tmp_hosts       = get_hosts()
    hosts           = []
    unreachable     = [] # jobList is a list of lists containing start and end values
    for host in tmp_hosts:
        try:
            tn = telnetlib.Telnet(host,22,.5)
            hosts.append(host.encode('utf-8'))
        except:
            unreachable.append(host.encode('utf-8'))
    numHosts = len( hosts )
    if( not(hosts_online) ):
        print("")
        print("Could not reach the following hosts: ")
        print(unreachable)
        print("Using the following %d hosts: " % (numHosts))
        print( hosts )
        print("")
        sys.stdout.flush()
    else:
        print( hosts )
        print( unreachable )
    return hosts

def main():
    startTime=time.time()
    args    = parser.parse_args()
    if(not( args.hosts_online )):
        print ("Starting blender_task...")
        sys.stdout.flush()
    else:
        hostsStatus(hosts_file=args.hosts_file, hosts=args.hosts, hosts_online=True, verbose=args.verbose)
        sys.exit(0)

    if(args.verbose >= 2 and not(args.hosts_online)):
        print (args)
    username    = getpass.getuser()
    projectRoot = os.path.dirname(os.path.abspath(__file__))

    if(not os.path.exists(projectRoot)):
        os.mkdir(projectRoot)

    if(args.project_name):

        projectName         = args.project_name
        projectPath         = '{projectRoot}/{projectName}/'.format(projectRoot=projectRoot,projectName=projectName)

        # Make the /tmp/<username> directory
        if(not os.path.exists(projectRoot)):
            os.mkdir(projectRoot)
        # Make the /tmp/<username>/<projectname> directory
        if(not (os.path.exists(projectPath))):
            os.mkdir(projectPath)

        if( args.local_sync == './toRemote' ):
            workingDir      = os.path.dirname(os.path.abspath(__file__))
            # Defaults to ./toRemote directory in working directory
            if(os.path.exists(os.path.join(workingDir,'toRemote'))):
                projectSyncPath = '{workingDir}/toRemote/'.format(workingDir=workingDir)
            # Otherwise, tries to find toRemote in /tmp/<username>/<projectname>/toRemote
            else:
                tmpDir = os.path.join(projectPath,'toRemote')
                # If this is the case, we literally have nothing to sync :(
                if(not(os.path.exists(tmpDir))):
                    os.mkdir(tmpDir)
                projectSyncPath = '{tmpDir}/'.format(tmpDir=tmpDir)
        else:
            projectSyncPath = args.local_sync
        if(not(os.path.exists(projectSyncPath))):
            os.mkdir(projectSyncPath)

        remoteProjectPath       = '{projectRoot}/{projectName}'.format(projectRoot=projectRoot,projectName=projectName)
        if(args.remote_sync == 'results'):
            remoteSyncBack      = '{remoteProjectPath}/results'.format(remoteProjectPath=remoteProjectPath)
        else:
            remoteSyncBack      = args.remote_sync
        if(args.contents):
            remoteSyncBack      = remoteSyncBack + "/*"
    else:
        print("sorry, please give your project a name")
        sys.exit(0)

    if(not(args.output_file)):
        projectOutuptFile = "{projectPath}".format(projectPath=projectPath)
        for file in os.listdir(projectOutuptFile):
            if( fnmatch.fnmatch(file,'*_seed-*') or fnmatch.fnmatch(file,'*.tga') ):
                if( args.verbose > 1 ):
                    print('Removing %s from project dir.' % (projectOutuptFile + file))
                os.remove(projectOutuptFile + file)

    cpCommand = "cp -n '" + projectRoot + "/blender_p.py' '" + projectSyncPath + "'"
    subprocess.call(cpCommand, shell=True)

    print ("Rendering frames %s in %s" % (args.frame_range,projectName))
    sys.stdout.flush()
    frame_range = json.loads(args.frame_range)

    hosts = hostsStatus(hosts_file=args.hosts_file,hosts=args.hosts,verbose=args.verbose)
    numHosts = len(hosts)

    frames      = expandFrames(frame_range)
    jobStrings  = buildJobStrings(frames,projectPath,projectName,username,numHosts)

    if(args.verbose >= 2):
        print ("Frames: ", frames)
        print ("Blender Commands: ", jobStrings)
    rsync_threads = {}
    jobStatus = {}

    for idx,jobString in enumerate(jobStrings):
        # Get the job string at the index of this host and pass to the thread with other info
        hostname = hosts[ idx % (len(hosts)) ]

        if(len(frames)==1):
            frame = frames[0]
        else:
            frame = frames[idx]

        job_args =  {
            'projectName':      projectName,
            'projectPath':      projectPath,
            'projectSyncPath':  projectSyncPath,
            'remoteProjectPath':   remoteProjectPath,
            'hostname':         hostname,
            'username':         username,
            'verbose':          args.verbose,
            'projectOutuptFile' :projectOutuptFile,
            'jobString' :       jobString,
            'jobStatus' :       jobStatus,
            'progress' :        args.progress,
            'frame' :           frame,
            'remoteSyncBack':   remoteSyncBack
        }

        thread = threading.Thread(target=start_blender_tasks,kwargs=job_args)
        rsync_threads[hostname] = thread
        thread.start()

    # Blocks `til all threads are done
    for hostname in rsync_threads.keys():
        rsync_threads[hostname].join()


    failed = 0
    for job in jobStrings:
        if(job not in jobStatus):
            print("Render task did not complete. Command: %s" % (job))
            sys.stdout.flush()
            failed += 1
    endTime = time.time()
    timer = stopWatch(endTime-startTime)
    print("")
    print("Elapsed time: " + timer)
    if(failed==0):
        print("Render completed successfully!")
        print("")
        sys.stdout.flush()
        sys.exit(0)
    else:
        print("Render failed for %d jobs" % (failed))
        print("")
        sys.stdout.flush()
        sys.exit(1)


if __name__ == '__main__':
    main()
