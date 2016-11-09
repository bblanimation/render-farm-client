#!/usr/bin/python

import subprocess
import telnetlib
import sys
import ast

def importCSE_HOSTS():
    try:
        f = open("HOSTS.txt", "r")
    except:
        print "Whoops! File could not be opened. Make sure 'CSE_HOSTS.txt' is in the same directory as this script file."
        return ""

    CSE_HOSTS = ast.literal_eval(f.readline())

    f.close()

    return CSE_HOSTS
        

def getAvailableHosts(CSE_HOSTS):
    hosts       = []
    unreachable = []
    for hostGroupName in CSE_HOSTS:
        for host in CSE_HOSTS[hostGroupName]:
            try:
                tn = telnetlib.Telnet(host + ".cse.taylor.edu",22,.5)
                hosts.append(host)
            except:
                unreachable.append(host)
    print hosts, unreachable
    return hosts

def killBlenderOnAvailServers(hosts):
    print "running killBlenderOnServer.py...\n"

    print "Are you sure you want to kill blender on the following servers?"
    print ""
    for host in hosts:
        print host + ".cse.taylor.edu"
    print ""
    uInput = ""
    while uInput != "yes" and uInput != "no":
        try:
            uInput = raw_input("[yes/no] => ")
        except:
            print "Whoops! There was an error. Try again."

    if uInput == "yes":
        for host in hosts:
            print "running 'killall blender' on " + host + " => ",
            sys.stdout.flush()
            subprocess.call("ssh cgearhar@" + host + ".cse.taylor.edu 'killall blender'", shell=True)
    else:
        print "\nprocess cancelled.\n"

def main():
    CSE_HOSTS = importCSE_HOSTS()
    if CSE_HOSTS == "":
        sys.exit()
    hosts = getAvailableHosts(CSE_HOSTS)
    killBlenderOnAvailServers(hosts)

main()
