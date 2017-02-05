#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import getpass
import sys
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

parser = argparse.ArgumentParser()

parser.add_argument("-l", "--frame_range", action="store", default="[]")
# Takes a string dictionary of hosts
# If neither of these arguments are provided, then use the default hosts file to load hosts
parser.add_argument("-d", "--hosts", action="store", default=None, help="Pass a dictionary or list of hosts. Should be valid json.")
parser.add_argument("-H", "--hosts_online", action="store_true", default=None, help="Telnets to ports to find out if a host is availible to ssh into, skips everything else.")
parser.add_argument("-i", "--hosts_file", action="store", default="remoteServers.txt", help="Pass a filename from which to load hosts. Should be valid json format.")
parser.add_argument("-m", "--max_server_load", action="store", default=None, help="Max render processes to run on each server at a time.")
parser.add_argument("-a", "--average_results", action="store_true", default=None, help="Average frames when finished.")
# NOTE: this parameter is currently required
parser.add_argument("-n", "--project_name", action="store", default=False) # just project name. default path will be in /tmp/blenderProjects
# TODO: test this for directories other than toRemote
parser.add_argument("-s", "--local_sync", action="store", default="./toRemote", help="Pass a full path or relative path to sync to the project directory on remote.")
# NOTE: remote_sync will sync the directory at results
parser.add_argument("-r", "--remote_sync", action="store", default="results", help="Pass a path to the directory that should be synced back.")
# NOTE: passing the contents flag will sync back the contents from the directory given in remote_sync
parser.add_argument("-c", "--contents", action="store_true", default=False, help="Pass a path to the directory that should be synced back.")
parser.add_argument("-C", "--command", action="store", help="Run the command on the remote host.")
parser.add_argument("-v", "--verbose", action=verbose_action, nargs="?", default=0)
parser.add_argument("-p", "--progress", action="store_true", help="Prints the progress to stdout as a json object.")
parser.add_argument("-R", "--project_root", action="store", help="Root path for storing project files on host server.")
parser.add_argument("-o", "--output_file_path", action="store", default=False, help="Local file to rsync files back into when done")
parser.add_argument("-O", "--name_output_files", action="store", default=False, help="Name to use for output files in results directory.")

# the following two functions are exclusively for use with parallel process
def hostsStatus(hosts_file=None, hosts=None, hosts_online=False, verbose=False):
    global HOSTS # Using the global HOSTS variable
    if hosts:
        HOSTS = json.loads(args.hosts)
    elif hosts_file:
        HOSTS = setServersDict(hosts_file)
    jobs = []
    tmp_hosts = get_hosts()
    hosts = []
    unreachable = [] # jobList is a list of lists containing start and end values
    for host in tmp_hosts:
        try:
            tn = telnetlib.Telnet(host, 22, .5)
            hosts.append(host.encode("utf-8"))
        except:
            unreachable.append(host.encode("utf-8"))
    numHosts = len(hosts)
    if not hosts_online:
        print("")
        print("Could not reach the following hosts: ")
        print(unreachable)
        print("Using the following %d hosts: " % (numHosts))
        print(hosts)
        print("")
        sys.stdout.flush()
    else:
        print(hosts)
        print(unreachable)
    return hosts

def get_hosts(groupName=None, hosts=None):
    global HOSTS
    if groupName:
        return HOSTS[groupName]
    elif hosts:
        return [i for k in HOSTS.keys() for i in hosts[k]]
    else:
        return [i for k in HOSTS.keys() for i in HOSTS[k]]

def main():
    """ Main function runs when blender_task is called """

    startTime = time.time()
    args = parser.parse_args()
    verbose = args.verbose

    # Getting hosts from some source
    if args.hosts_file:
        hosts = listHosts(setServersDict(args.hosts_file))
    elif args.hosts:
        hosts = listHosts(args.hosts)
    else:
        hosts = listHosts(HOSTS)

    host_objects = dict()
    hosts_online = list()
    hosts_offline = list()
    for host in hosts:
        jh = JobHost(hostname=host, thread_func=start_split_tasks, verbose=verbose)
        if jh.is_reachable():
            hosts_online.append(str(host))
        else:
            hosts_offline.append(str(host))
        host_objects[host] = jh
    numHosts = len(hosts_online)

    # Printing the start message
    if not args.hosts_online:
        if verbose >= 1:
            print("Starting distribute task...")
            sys.stdout.flush()
        if len(hosts_online) == 0:
            sys.stderr.write("No hosts available.")
            sys.exit(58)
    else:
        if verbose >= 1: print("Hosts Online : ")
        print(hosts_online)
        if verbose >= 1: print("Hosts Offline: ")
        print(hosts_offline)
        sys.exit(0)

    username = getpass.getuser()
    if not args.project_root:
        projectRoot = "/tmp/%s" % (username)
    else:
        if args.project_root[-1] == "/":
            args.project_root = args.project_root[:-1]
        projectRoot = args.project_root

    if args.project_name:

        if not args.name_output_files:
            args.name_output_files = args.project_name

        projectName = args.project_name
        projectPath = "{projectRoot}/{projectName}".format(projectRoot=projectRoot, projectName=projectName)
        # Make the <projectRoot>/<projectname> directory
        if not os.path.exists(projectPath):
            os.mkdir(projectPath)

        if not args.local_sync or args.local_sync == "./toRemote":
            workingDir = os.path.dirname(os.path.abspath(__file__))
            # Defaults to ./toRemote directory in working directory
            if os.path.exists(os.path.join(workingDir, "toRemote")):
                projectSyncPath = "{workingDir}/toRemote/".format(workingDir=workingDir)
            # Otherwise, tries to find toRemote in <projectRoot>/<projectname>/toRemote
            else:
                tmpDir = os.path.join(projectPath, "toRemote")
                # If this is the case, we literally have nothing to sync :(
                if not os.path.exists(tmpDir):
                    os.mkdir(tmpDir)
                projectSyncPath = "{tmpDir}/".format(tmpDir=tmpDir)
        else:
            projectSyncPath = args.local_sync

        remoteProjectPath = "{projectRoot}/{projectName}".format(projectRoot=projectRoot, projectName=projectName)
        if args.remote_sync == "results":
            remoteSyncBack = "{remoteProjectPath}/results".format(remoteProjectPath=remoteProjectPath)
        else:
            remoteSyncBack = args.remote_sync
        if args.contents:
            remoteSyncBack = remoteSyncBack + "/*"
    else:
        print("sorry, please give your project a name using the -n or --project_name flags.")
        sys.exit(0)

    if not args.output_file_path:
        for file in os.listdir(projectPath):
            if fnmatch.fnmatch(file, "*_seed-*") or fnmatch.fnmatch(file, "*.tga"):
                projectOutputFile = os.path.join(projectPath, file)
                if verbose > 1:
                    print("Removing {projectOutputFile} from project dir.".format(projectOutputFile=projectOutputFile))
                os.remove(projectOutuptFile)
    else:
        projectOutuptFile = args.output_file_path

    # Copy blender_p.py to project folder
    subprocess.call("rsync -e 'ssh -oStrictHostKeyChecking=no' -a '" + os.path.join(projectRoot, "blender_p.py") + "' '" + os.path.join(projectPath, "toRemote", "blender_p.py") + "'", shell=True)

    if verbose >= 1:
        print("Rendering frames {frameRange} in {projectName}".format(frameRange=args.frame_range, projectName=projectName))
        sys.stdout.flush()

    frame_range = json.loads(args.frame_range)

    frames = expandFrames(frame_range)
    jobStrings = buildJobStrings(frames, projectName, projectPath, args.name_output_files, numHosts)

    # for split processing
    if int(args.max_server_load) > 0:
        job_args = {
            "projectName":       projectName,
            "projectPath":       projectPath,
            "projectSyncPath":   projectSyncPath,
            "remoteProjectPath": remoteProjectPath,
            "username":          username,
            "verbose":           verbose,
            "projectOutuptFile": projectOutuptFile,
            "remoteSyncBack":    remoteSyncBack
        }

        # Sets up kwargs, and callbacks on the hosts
        jhm = JobHostManager(jobs=jobStrings, hosts=host_objects, function_args=job_args, verbose=verbose, max_on_hosts=2)
        jhm.start()
        status = jhm.get_cumulative_status()

        if args.average_results:
            averageFrames(remoteSyncBack, projectName, verbose)

    # for parallel processing
    else:
        if args.verbose >= 2:
            print("Frames: ", frames)
            print("Blender Commands: ", jobStrings)
        rsync_threads = {}
        jobStatus = {}

        for idx, jobString in enumerate(jobStrings):
            # Get the job string at the index of this host and pass to the thread with other info
            hostname = hosts_online[idx % (numHosts)]

            if len(frames) == 1:
                frame = frames[0]
            else:
                frame = frames[idx]

            job_args = {
                "projectName":      projectName,
                "projectPath":      projectPath,
                "projectSyncPath":  projectSyncPath,
                "remoteProjectPath":remoteProjectPath,
                "hostname":         hostname,
                "username":         username,
                "verbose":          args.verbose,
                "projectOutuptFile":projectOutuptFile,
                "jobString":        jobString,
                "jobStatus":        jobStatus,
                "progress":         args.progress,
                "frame":            frame,
                "remoteSyncBack":   remoteSyncBack
            }

            thread = threading.Thread(target=start_parallel_tasks, kwargs=job_args)
            rsync_threads[hostname] = thread
            thread.start()

        # Blocks `til all threads are done
        for hostname in rsync_threads.keys():
            rsync_threads[hostname].join()

        failed = 0
        for job in jobStrings:
            if job not in jobStatus:
                sys.stderr.write("Render task did not complete. Command: %s" % (job) + "\n")
                sys.stdout.flush()
                failed += 1

    endTime = time.time()
    timer = stopWatch(endTime-startTime)
    if verbose >= 1:
        print("")
        print("Elapsed time: " + timer)
        if int(args.max_server_load) > 0:
            pass
            # TODO: Show status of render if using split processing
            # if(status==0):
            #     print("Render completed successfully!")
            #     sys.stdout.flush()
            # else:
            #     sys.stderr.write("Render failed for %d jobs" % (failed) + "\n")
            #     sys.stderr.flush()
        else:
            if failed == 0:
                print("Render completed successfully!")
                sys.stdout.flush()
                sys.exit(0)
            else:
                sys.stderr.write("Render failed for %d jobs" % (failed) + "\n")
                sys.stdout.flush()
                sys.exit(1)

    if verbose >= 3:
        print("\nJob exit statuses:")
        jhm.print_jobs_status()

if __name__ == "__main__":
    main()
