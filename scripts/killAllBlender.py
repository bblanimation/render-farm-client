#!/usr/bin/python

import subprocess, telnetlib, sys, argparse

args = None

def ParseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="Username to use for logging in to remote servers", action="store_true")
    parser.add_argument("-s", "--servers_to_kill", help="Dictionary of remote servers to kill blender processes on", action="store_true")
    parser.add_argument("-e", "--extension", help="Extension to append to every remote server", action="store_true")
    args = parser.parse_args()

def killBlenderOnAvailServers(username, hosts, extension):
    print("running killBlenderOnServer.py...\n")

    for host in hosts:
        print("running 'killall blender' on " + host + " => ",end="")
        sys.stdout.flush()
        subprocess.call("ssh " + username + "@" + host + extension + " 'killall blender'", shell=True)

def main():
    parseArgs()
    username  = args.username
    hosts     = args.servers_to_kill
    extension = args.extension
    killBlenderOnAvailServers(username, hosts, extension)

main()
