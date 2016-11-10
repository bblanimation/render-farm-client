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


parser = argparse.ArgumentParser()
# parser.add_argument('-s','--start',action='store',default='1')
# parser.add_argument('-e','--end',action='store',default='1')

parser.add_argument('-l','--frame_ranges',action='store',default="[]")
parser.add_argument('-f','--project_file',action='store',default=False) # /full/path/to/project.blend
parser.add_argument('-n','--project_name',action='store',default=False) # just projectname. default path will be in /tmp/blenderProjects
parser.add_argument('-o','--output_file',action='store',default=False,help='local output file to rsync files back into when done')
parser.add_argument('-v','--verbose',action=verbose_action,nargs='?',default=0)
parser.add_argument('-S','--samples',action='store',default='50')
parser.add_argument('-p','--progress',action='store_true',help='prints the progress to stdout as a json object')

CSE_HOSTS = {'cse103group': [   'cse10301','cse10302','cse10303','cse10304','cse10305','cse10306','cse10307',
                                'cse10309','cse10310','cse10311','cse10312','cse10315','cse10316','cse10317',
                                'cse10318','cse10319','cse103podium'
                            ],
            'cse201group' : [     'cse20101','cse20102','cse20103','cse20104','cse20105','cse20106','cse20107',
                                'cse20108','cse20109','cse20110','cse20111','cse20112','cse20113','cse20114',
                                'cse20116','cse20117','cse20118','cse20119','cse20120','cse20121','cse20122',
                                'cse20123','cse20124','cse20125','cse20126','cse20127','cse20128','cse20129',
                                'cse20130','cse20131','cse20132','cse20133','cse20134','cse20135','cse20136'
                            ],
            'cse21801group': [  'cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807',
                                'cse21808','cse21809','cse21810','cse21811','cse21812'
                            ],
            'cse217group' : [   'cse21701','cse21702','cse21703','cse21704','cse21705','cse21706','cse21707',
                                'cse21708','cse21709','cse21710','cse21711','cse21712','cse21713','cse21714',
                                'cse21715','cse21716'
                            ]
        }

status_regex = r"Fra:(\d)\s.*Time:(\d{2}:\d{2}\.\d{2}).*Remaining:(\d{2}:\d{2}\.\d{2})\s.*"

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

def get_hosts(groupName=None):
    if(groupName):
        return CSE_HOSTS[groupName]
    else:
        return [ i for k in CSE_HOSTS.keys() for i in CSE_HOSTS[k]]

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

def rsync_files_to_node_string(projectFullPath,username,hostname,remoteFullPath,verbose=False):
    tmpStr = "rsync  -e 'ssh -oStrictHostKeyChecking=no'  -a %s %s@%s:%s" % (projectFullPath,username,hostname,remoteFullPath)
    if( verbose >= 2 ):
        pflush(tmpStr)
    return tmpStr

def rsync_files_from_node_string(username,hostname,remoteProjectPath,projectName,projectOutuptFile,verbose=False):
    tmpStr = "rsync -atu --remove-source-files %s@%s:%s/render/%s* %s." % (username,hostname,remoteProjectPath,projectName,projectOutuptFile)
    if(verbose >= 2):
        pflush(tmpStr)
    return tmpStr

def ssh_command_string(user,hostname,command,verbose=False):
    if( verbose >= 1 ):
        print("ssh -oStrictHostKeyChecking=no %s@%s %s" % (user,hostname,command))
        sys.stdout.flush()
    return "ssh -oStrictHostKeyChecking=no %s@%s %s" % (user,hostname,command)

def rsync_files_string(username,hostname,projectName,projectPath):
    projectFullPath = "%s/%s.blend" % (projectPath,projectName)
    return ssh_command_string(username,hostname,"mkdir -p /tmp/%s/%s;rsync -a %s %s@%s:/tmp/%s/%s" % (username,projectName,projectFullPath,username,hostname,username,projectName))

def start_blender_tasks(
    projectName, projectPath,
    projectFullPath, hostname,
    username, jobString,
    projectOutuptFile, jobStatus,
    remoteProjectPath, remoteFullPath,
    start, end, progress=False,
    verbose=0 ):

    pflush("Starting thread. Rendering from %s to %s on %s" % (start,end,hostname))
    # print(projectFullPath)
    # First copy the files over using rsync
    rsync_to            = rsync_files_to_node_string( projectFullPath, username, hostname, remoteFullPath )
    rsync_from          = rsync_files_from_node_string( username, hostname, remoteProjectPath, projectName, projectOutuptFile )
    mkdir_local_string  = mkdir_string( projectPath )
    mkdir_remote_string = mkdir_string( remoteProjectPath )
    ssh_c_string        = ssh_string( username, hostname )

    ssh_mkdir           = ssh_c_string + " '" + mkdir_remote_string + "'"
    ssh_blender         = ssh_c_string + " '" + jobString + "' "
    pull_from           = mkdir_remote_string + ";" + rsync_from

    # print(rsync_from)
    # print(mkdir_local_string)
    # print(ssh_mkdir)

    if(verbose >= 2):
        print("Syncing project file %s.blend to %s" % (projectName,hostname))
        print("rsync command: %s" % (rsync_to))
    t = subprocess.call( ssh_mkdir,shell=True )
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
        print ("Successfully completed render for frames (%d-%d) on hostname %s." % (start,end,hostname))
        jobStatus[jobString] = dict()
        jobStatus[jobString]['blend'] = 0
        sys.stdout.flush()
    else:
        print("blender error: %d" % (q.returncode))
    # Now rsync the files in /tmp/<name>/render back to this host.

    if(verbose >= 2):
        print("rsync pull: " + pull_from )
    r = subprocess.call( pull_from,shell=True)

    if( r == 0 and q.returncode == 0 ):
        jobStatus[jobString]['rsync'] = 0
        print( "Render frames (%d-%d) have been copied back from hostname %s" % (start,end,hostname))
        sys.stdout.flush()
    else:
        print("rsync error: %d" % (r))


def buildJobStrings(jobLists, projectName, username): # jobList is a list of lists containing start and end values
    jobStrings = []
    for lst in jobLists:
        seedString = ""
        if (lst[2] != -1):
            seedString = "_seed-" + str(lst[2])
        builtString = "blender -b " + '/tmp/'+username+'/' +projectName+'/' +projectName + ".blend -x 1 -o //render/" + projectName + seedString + "_####.png -s " + str(lst[0]) + " -e " + str(lst[1]) + " -P " + "/home/CS/faculty/nwhite/.linux/distribute-blender-work/blender_p.py -a"
        jobStrings.append(builtString)
    return jobStrings

def calcFrames( frame_ranges, availableServers=5):
    # TODO: fix the start stop values and use frame_ranges
    jobs   = []
    frames = []
    sequential = False
    junk        = True
    for i in frame_ranges:
        if( type(i) == list ):
            frames += range(i[0],i[1])
            if(junk):
                sequential = True
                junk = False
        elif( type(i) == int ):
            frames.append(i)
            sequential = False
        else:
            print("Unknown type in frames list")

    if ( len(frames) == 1 ):
        for i in range(availableServers):
            jobs.append([frames[0],frames[0],i])
    elif ( availableServers > len(frames) ):
        for frame in frames:
            jobs.append([frame,frame])
    elif(sequential):
        remainder = len(frames) % availableServers
        framesToDistribute = len(frames) - remainder
        fraction = framesToDistribute/availableServers
        counter = 0
        for i in range(1, availableServers + 1):
            startFrame = frames[((i*fraction) - fraction) + counter]
            endFrame   = frames[(i*fraction) + counter - 1]
            if ( remainder != 0 ):
                endFrame += 1
                counter += 1
                remainder -= 1
            jobs.append([startFrame, endFrame,-1])
    else:
        # TODO: Implement this.
        print("NOT YET IMPLEMENTED")
        sys.exit()
    return jobs

def main():
    args    = parser.parse_args()
    print ("Starting blender_task...")
    sys.stdout.flush()

    if(args.verbose >= 2):
        print (args)
    username    = getpass.getuser()
    projectRoot   = "/tmp/%s" % (username)

    if(args.project_name):

        projectName         = args.project_name
        projectPath         = '%s/%s'  % (projectRoot,projectName)
        projectFullPath     = '%s/%s.blend' % (projectPath,projectName)

        remoteProjectPath   = '%s/%s'  % (projectRoot,projectName)
        remoteFullPath      = '%s/%s.blend' % (remoteProjectPath,projectName)

    elif(args.project_file):

        projectName         = (os.path.basename(args.project_file)).split('.')[0]
        projectPath         = os.path.dirname(args.project_file)
        projectFullPath     = args.project_file

        remoteProjectPath   = '%s/%s' % (projectRoot,projectName)
        remoteFullPath      = '%s/%s.blend' % (remoteProjectPath,projectName)
    else:
        projectFiles = []
        checkPaths = []
        checkPaths.append(os.path.dirname(os.path.abspath(__file__)))
        tmp_path = '/tmp/%s' % (username)
        if(os.path.exists(path=tmp_path)):
            checkPaths.append(tmp_path)
        else:
            os.makedirs(tmp_path)
        for path in checkPaths:
            for item in os.listdir(path):
                if os.path.isfile(os.path.join(path,item)):
                    if('.blend' in item):
                        projectFiles.append(os.path.join(path,item))
        if(len(projectFiles) == 0):
            print("Sorry, cannot run. Ambiguous instructions. Or no .blend files found in %s or in %s " % (checkPaths[0],checkPaths[1]))
            sys.exit()
        # else
        validChoice = False
        txt = ""
        val = -1
        while(not(validChoice)):
            for idx,fileName in enumerate(projectFiles):
                print( "%d) %s " % (idx+1,fileName))
            txt = raw_input("Please choose the project file you want to use. Choices %d-%d: " % (1,len(projectFiles)))
            try:
                val = int(txt)
                if(val <= len(projectFiles) and val >= 1):
                    validChoice = True
                    val -= 1
            except:
                pass
        projectFullPath = projectFiles[val]


        projectPath = os.path.dirname(projectFullPath)
        projectName = (os.path.basename(projectFullPath)).split('.')[0]

        remoteProjectPath   = '%s/%s' % (projectRoot,projectName)
        remoteFullPath      = '%s/%s.blend' % (remoteProjectPath,projectName)

    if(not(args.output_file)):
        projectOutuptFile = "/tmp/%s/%s/" % ( username,projectName )
        for file in os.listdir(projectOutuptFile):
            if( fnmatch.fnmatch(file,'*_seed-*') or fnmatch.fnmatch(file,'*.tga') ):
                if( args.verbose > 1 ):
                    print('Removing %s from project dir.' % (projectOutuptFile + file))
                os.remove(projectOutuptFile + file)

    print ("Rendering frames %s in %s" % (args.frame_ranges,projectName))
    sys.stdout.flush()

    frame_range = json.loads(args.frame_range)

    print(frame_range)

    jobs            = []
    tmp_hosts       = get_hosts()
    hosts           = []
    unreachable     = [] # jobList is a list of lists containing start and end values

    for host in tmp_hosts:
        try:
            tn = telnetlib.Telnet(host,22,.5)
            hosts.append(host)
        except:
            unreachable.append(host)

    numHosts = len(hosts)

    print ("")
    print ("Could not reach the following hosts: ",unreachable)
    print ("Using the following %d hosts: " % (numHosts), hosts)
    print ("")

    sys.stdout.flush()

    samples     = args.samples
    frames      = calcFrames(frame_range, numHosts)
    jobStrings  = buildJobStrings(frames,projectName,username)

    if(args.verbose >= 2):
        print ("Frames: ", frames)
        print ("Blender Commands: ", jobStrings)

    rsync_threads = []
    jobStatus = {}
    for idx,jobString in enumerate(jobStrings):
        # Get the job string at the index of this host and pass to the thread with other info
        hostname = hosts[idx]
        frame = frames[idx]
        job_args =  {
            'projectName':      projectName,
            'projectPath':      projectPath,
            'projectFullPath':  projectFullPath,
            'remoteProjectPath':remoteProjectPath,
            'remoteFullPath':   remoteFullPath,
            'hostname':         hostname,
            'username':         username,
            'verbose':          args.verbose,
            'projectOutuptFile' :projectOutuptFile,
            'jobString' :       jobString,
            'jobStatus' :       jobStatus,
            'start':            frame[0],
            'end' :             frame[1],
            'progress' :        args.progress
        }
        thread = threading.Thread(target=start_blender_tasks,kwargs=job_args)
        rsync_threads.append(thread)
        thread.start()

    for thread in rsync_threads:
        thread.join()

    failed = 0
    for job in jobStrings:
        if(job not in jobStatus):
            print("Render task did not complete. Command: %s" % (job))
            sys.stdout.flush()
            failed += 1
    if(failed==0):
        print("")
        print("Render completed successfully!")
        sys.stdout.flush()
        sys.exit(0)
    else:
        print("")
        print("Render failed for %d jobs" % (failed))
        sys.stdout.flush()
        sys.exit(1)


if __name__ == '__main__':
    main()
