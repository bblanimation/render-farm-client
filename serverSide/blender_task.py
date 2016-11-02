#!/usr/bin/env python

import argparse
import os,getpass,sys
import subprocess
import threading
import telnetlib


# DEFAULT_PROJECT_PATH = '/tmp/blenderProjects'
# PROJECT_NAME = 'demo'
# OUTPUT_PROJECT_PATH = '/tmp/%s/' % (PROJECT_NAME)

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
parser.add_argument('-s','--start',action='store',default='1')
parser.add_argument('-e','--end',action='store',default='1')
parser.add_argument('-f','--project_file',action='store',default=False) # /full/path/to/project.blend
parser.add_argument('-n','--project_name',action='store',default=False) # just projectname. default path will be in /tmp/blenderProjects
parser.add_argument('-o','--output_file',action='store',default=False,help='local output file to rsync files back into when done')
parser.add_argument('-v','--verbose',action=verbose_action,nargs='?',default=0)
parser.add_argument('-S','--samples',action='store',default='50')

CSE_HOSTS = {'cse21801group': ['cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807','cse21808','cse21809','cse21810','cse21811','cse21812','cse21701','cse21702','cse21703','cse21704','cse21705','cse21706','cse21707','cse21708','cse21709','cse21710','cse21711','cse21712','cse21713','cse21715','cse21716']}

# This way if we come up with a good dynamic way to figure out the hosts we have to use we are using a function anyway.
def get_hosts(groupName=None):
    if(groupName):
        return CSE_HOSTS[groupName]
    else:
        return [ i for k in CSE_HOSTS.keys() for i in CSE_HOSTS[k]]

def ssh_command_string(user,hostname,command,verbose=False):
    if( verbose >= 1 ):
        print("ssh -oStrictHostKeyChecking=no %s@%s %s" % (user,hostname,command))
        sys.stdout.flush()
    return "ssh -oStrictHostKeyChecking=no %s@%s %s" % (user,hostname,command)

def rsync_files_string(username,hostname,projectName,projectPath):
    projectFullPath = "%s/%s.blend" % (projectPath,projectName)
    return ssh_command_string(username,hostname,"mkdir -p /tmp/%s/%s;rsync -a %s %s@%s:/tmp/%s/%s" % (username,projectName,projectFullPath,username,hostname,username,projectName))

def start_blender_tasks(projectName,projectPath,projectFullPath,hostname,username,jobString,projectOutuptFile,jobStatus,startFrame,endFrame,verbose=0):
    print("Starting thread. Rendering from %s to %s on %s" % (startFrame,endFrame,hostname))
    sys.stdout.flush()
    # First copy the files over using rsync
    rstring = rsync_files_string(username,hostname,projectName,projectPath)
    blendString = ssh_command_string(username,hostname,jobString,verbose)
    if(verbose >= 2):
        print("Syncing project file %s.blend to %s" % (projectName,hostname))
        print("rsync command: %s" % (rstring))
    p = subprocess.call(rstring,shell=True)
    if(verbose >= 2):
        print("Finished the rsync to host %s" % (hostname))
    if(verbose >= 2):
        print("Returned from rsync command: %d" % (p))
        sys.stdout.flush()
        if(p == 0): print "Success!"
    # Now start the blender command
    if(verbose >= 2):
        print "blender command: %s" % (blendString)

    with open(os.devnull, "w") as f:
        q = subprocess.call(blendString,stdout=f,shell=True)

    if( q == 0 ):
        print "Successfully completed render for frames (%d-%d) on hostname %s." % (startFrame,endFrame,hostname)
        jobStatus[jobString] = dict()
        jobStatus[jobString]['blend'] = 0
        sys.stdout.flush()
    else:
        print("blender error: %d" % (q))

    # Now rsync the files in /tmp/<name>/render back to this host.
    rsyncPullFiles = "mkdir -p %s;rsync -atu --remove-source-files %s@%s:/tmp/%s/%s/render/%s* %s." % (projectOutuptFile,username,hostname,username,projectName,projectName,projectOutuptFile)
    if(verbose >= 2):
        print("rsync command: %s" % (rsyncPullFiles))
    r = subprocess.call(rsyncPullFiles,shell=True)

    if( r == 0 and q == 0 ):
        jobStatus[jobString]['rsync'] = 0
        print( "Render frames (%d-%d) have been copied back from hostname %s" % (startFrame,endFrame,hostname))
        sys.stdout.flush()
    else:
        print("rsync error: %d" % (r))


def buildJobStrings(jobLists, projectName, username): # jobList is a list of lists containing start and end values
    jobStrings = []
    for lst in jobLists:
        seedString = ""
        if (lst[2] != -1):
            seedString = "_seed-" + str(lst[2])
        builtString = "blender -b " + '/tmp/'+username+'/' +projectName+'/' +projectName + ".blend -x 1 -o //render/" + projectName + seedString + "_####.png -s " + str(lst[0]) + " -e " + str(lst[1]) + " -P " + "/home/CS/users/cgearhar/.linux/bin/blender_p.py -a"
        jobStrings.append(builtString)
    return jobStrings

def calcFrames( frameStart, frameEnd, availableServers=5):
    jobs   = []
    frames = []
    for i in range( frameStart, frameEnd + 1 ):
        frames.append(i)
    if ( len(frames) == 1 ):
        for i in range(availableServers):
            jobs.append([frames[0],frames[0],i])
    elif ( availableServers > len(frames) ):
        for frame in frames:
            jobs.append([frame,frame])
    else:
        remainder = len(frames) % availableServers
        framesToDistribute = len(frames) - remainder
        fraction = framesToDistribute/availableServers
        counter = 0
        for i in range(1,availableServers + 1):
            startFrame = frames[((i*fraction) - fraction) + counter]
            endFrame   = frames[(i*fraction) + counter - 1]
            if ( remainder != 0 ):
                endFrame += 1
                counter += 1
                remainder -= 1
            jobs.append([startFrame, endFrame,-1]);
    return jobs

def main():
    args    = parser.parse_args()
    print ("Starting blender_task...")
    sys.stdout.flush()

    if(args.verbose >= 2):
        print args
    username    = getpass.getuser()

    if(args.project_name):
        projectName = args.project_name
        projectPath = '/tmp/%s/%s' % (username,projectName)
        projectFullPath = "%s/%s.blend" % (projectPath,projectName)
    elif(args.project_file):
        projectName = (os.path.basename(args.project_file)).split('.')[0]
        projectPath = os.path.dirname(args.project_file)
        projectFullPath = args.project_file
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

    if(not(args.output_file)):
        projectOutuptFile = "/tmp/%s/%s/" % ( username,projectName )

    print ("Rendering from %s to %s in %s" % (args.start,args.end,projectName))
    sys.stdout.flush()

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
    print "Could not reach the following hosts: ",unreachable
    print "Using the following %d hosts: " % (numHosts), hosts
    print ("")

    sys.stdout.flush()

    samples     = args.samples
    frames      = calcFrames(int(args.start), int(args.end), numHosts)
    jobStrings  = buildJobStrings(frames,projectName,username)

    if(args.verbose >= 2):
        print "Frames: ", frames
        print "Blender Commands: ", jobStrings

    rsync_threads = []
    jobStatus = {}
    for idx,jobString in enumerate(jobStrings):
        # Get the job string at the index of this host and pass to the thread with other info
        hostname = hosts[idx]
        frame = frames[idx]
        job_args =  {
            'projectName': projectName,
            'projectPath': projectPath,
            'projectFullPath': projectFullPath,
            'hostname': hostname,
            'username': username,
            'verbose': args.verbose,
            'projectOutuptFile' : projectOutuptFile,
            'jobString' : jobString,
            'jobStatus' : jobStatus,
            'startFrame': frame[0],
            'endFrame' : frame[1]
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
