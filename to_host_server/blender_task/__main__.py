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
import json

from JobHost import *
from JobHostManager import *
from VerboseAction import verbose_action

status_regex = r"Fra:(\d+)\s.*Time:(\d{2}:\d{2}\.\d{2}).*Remaining:(\d{2}:\d+\.\d+)\s.*"

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

parser = argparse.ArgumentParser()

parser.add_argument('-l','--frame_range',action='store',default="[]")
# Takes a string dictionary of hosts
# If neither of these arguments are provided, then use the default hosts file to load hosts
parser.add_argument('-d','--hosts',action='store',default=None,help='Pass a dictionary or list of hosts. Should be valid json.')
parser.add_argument('-H','--hosts_online',action='store_true',default=None,help='Telnets to ports to find out if a host is availible to ssh into, skips everything else.')
parser.add_argument('-i','--hosts_file',action='store',default='remoteServers.txt',help='Pass a filename from which to load hosts. Should be valid json format.')
parser.add_argument('-m','--max_server_load',action='store',default=None,help='Max render processes to run on each server at a time.')
parser.add_argument('-a','--average_results',action='store_true',default=None,help='Average frames when finished.')

# NOTE: this parameter is currently required
parser.add_argument('-n','--project_name',action='store',default=False) # just project name. default path will be in /tmp/blenderProjects
# TODO: test this for directories other than toRemote
parser.add_argument('-s','--local_sync',action='store',default='./toRemote',help='Pass a full path or relative path to sync to the project directory on remote.')
# NOTE: remote_sync will sync the directory at results
parser.add_argument('-r','--remote_sync',action='store',default='results',help='Pass a path to the directory that should be synced back.')
# NOTE: passing the contents flag will sync back the contents from the directory given in remote_sync
parser.add_argument('-c','--contents',action='store_true',default=False,help='Pass a path to the directory that should be synced back.')
parser.add_argument('-C','--command',action='store',help='Run the command on the remote host.')
parser.add_argument('-v','--verbose',action=verbose_action,nargs='?',default=0)
parser.add_argument('-p','--progress',action='store_true',help='Prints the progress to stdout as a json object.')
parser.add_argument('-R','--project_root',action='store',help='Root path for storing project files on host server.')
parser.add_argument('-o','--output_file_path',action='store',default=False,help='Local file to rsync files back into when done')
parser.add_argument('-O','--name_output_files',action='store',default=False,help='Name to use for output files in results directory.')

def main():
    startTime=time.time()
    args    = parser.parse_args()
    verbose = args.verbose
    # Getting hosts from some source
    hosts   = listHosts( HOSTS )
    if( args.hosts_file ):
        hosts = listHosts( setServersDict(args.hosts_file) )
    elif( args.hosts ):
        hosts = listHosts( args.hosts )

    host_objects = dict()

    hosts_online    = list()
    hosts_offline   = list()
    for host in hosts:
        jh = JobHost( hostname=host,thread_func=start_tasks,verbose=verbose )
        if( jh.is_reachable() ):
            hosts_online.append(str(host))
        else:
            hosts_offline.append(str(host))
        host_objects[host] = jh

    # Printing the start message
    if(not( args.hosts_online )):
        if(verbose >= 1):
            print ("Starting distribute task...")
            sys.stdout.flush()
    else:
        if( verbose >= 1 ): print( "Hosts Online : " )
        print(hosts_online)
        if( verbose >= 1 ): print( "Hosts Offline: " )
        print(hosts_offline)
        sys.exit(0)

    username    = getpass.getuser()
    if ( not(args.project_root) ):
        projectRoot = "/tmp/%s" % (username)
    else:
        if args.project_root[-1] == "/":
            args.project_root = args.project_root[:-1]
        projectRoot = args.project_root

    if(args.project_name):

        if(not(args.name_output_files)):
            args.name_output_files =  args.project_name

        projectName         = args.project_name
        projectPath         = '{projectRoot}/{projectName}'.format(projectRoot=projectRoot,projectName=projectName)
        # Make the <projectRoot>/<projectname> directory
        if(not (os.path.exists(projectPath))):
            os.mkdir(projectPath)

        if( not(args.local_sync) or args.local_sync == './toRemote' ):
            workingDir      = os.path.dirname(os.path.abspath(__file__))
            # Defaults to ./toRemote directory in working directory
            if(os.path.exists(os.path.join(workingDir,'toRemote'))):
                projectSyncPath = '{workingDir}/toRemote/'.format(workingDir=workingDir)
            # Otherwise, tries to find toRemote in <projectRoot>/<projectname>/toRemote
            else:
                tmpDir = os.path.join(projectPath,'toRemote')
                # If this is the case, we literally have nothing to sync :(
                if(not(os.path.exists(tmpDir))):
                    os.mkdir(tmpDir)
                projectSyncPath = '{tmpDir}/'.format(tmpDir=tmpDir)
        else:
            projectSyncPath = args.local_sync

        remoteProjectPath       = '{projectRoot}/{projectName}'.format(projectRoot=projectRoot,projectName=projectName)
        if(args.remote_sync == 'results'):
            remoteSyncBack      = '{remoteProjectPath}/results'.format(remoteProjectPath=remoteProjectPath)
        else:
            remoteSyncBack      = args.remote_sync
        if(args.contents):
            remoteSyncBack      = remoteSyncBack + "/*"
    else:
        print("sorry, please give your project a name using the -n or --project_name flags.")
        sys.exit(0)

    if(not(args.output_file_path)):
        projectOutuptFile = "{projectPath}/".format(projectPath=projectPath)
        for file in os.listdir(projectOutuptFile):
            if( fnmatch.fnmatch(file,'*_seed-*') or fnmatch.fnmatch(file,'*.tga') ):
                if( verbose > 1 ):
                    print('Removing %s from project dir.' % (projectOutuptFile + file))
                os.remove(projectOutuptFile + file)
    else:
         projectOutuptFile = args.output_file_path

    # What is the abstraction for this
    frame_range = json.loads(args.frame_range)
    numHosts = len(hosts)

    frames      = expandFrames(frame_range)
    jobStrings  = buildJobStrings(frames,projectName,projectPath,args.name_output_files,numHosts)

    # Copy blender_p.py to project folder
    subprocess.call("rsync -e 'ssh -oStrictHostKeyChecking=no' -a '" + os.path.join(projectRoot, "blender_p.py") + "' '" + os.path.join(projectPath, "toRemote", "blender_p.py") + "'", shell=True)

    job_args =  {
        'projectName':      projectName,
        'projectPath':      projectPath,
        'projectSyncPath':  projectSyncPath,
        'remoteProjectPath':   remoteProjectPath,
        'username':         username,
        'verbose':          verbose,
        'projectOutuptFile' :projectOutuptFile,
        'remoteSyncBack':   remoteSyncBack,
    }

    # Sets up kwargs, and callbacks on the hosts
    jhm = JobHostManager(jobs=jobStrings,hosts=host_objects,function_args=job_args,verbose=verbose,max_on_hosts=2)
    jhm.start()
    status = jhm.get_cumulative_status()

    if args.average_results:
        averageFrames(remoteSyncBack, projectName, verbose)

    endTime = time.time()
    timer = stopWatch(endTime-startTime)
    if( verbose >= 1 ):
        print("")
        print("Elapsed time: " + timer)
        ##TODO: Add the functionality on the following 6 lines back in
        # if(status==0):
        #     print("Render completed successfully!")
        #     sys.stdout.flush()
        # else:
        #     sys.stderr.write("Render failed for %d jobs" % (failed) + "\n")
        #     sys.stderr.flush()

    if( verbose >= 3 ):
        print("\nJob exit statuses:")
        jhm.print_jobs_status()

if __name__ == '__main__':
    main()
