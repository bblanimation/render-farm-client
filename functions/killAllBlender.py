#!/usr/bin/python

import subprocess, telnetlib, sys, argparse, json

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--username", help="Username to use for logging in to remote servers", action="store")
parser.add_argument("-s", "--servers_to_kill", help="Dictionary of remote servers to kill blender processes on", action="store")
parser.add_argument("-e", "--extension", help="Extension to append to every remote server", action="store")
args = parser.parse_args()

def killBlenderOnAvailServers(username, hosts, extension):
    print("running killBlenderOnServer.py...\n")

    for host in hosts:
        print "running 'killall blender' on " + host + " => ",
        sys.stdout.flush()
        subprocess.call("ssh " + username + "@" + host + extension + " 'killall blender'", shell=True)

def main():
    username = args.username
    hosts = json.loads(args.servers_to_kill)
    extension = args.extension
    killBlenderOnAvailServers(username, hosts, extension)

main()
