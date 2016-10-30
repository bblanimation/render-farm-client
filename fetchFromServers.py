#!/usr/bin/python

import subprocess
import sys
import telnetlib
import ast



projectName = "rise_of_miniland_logo"



def importCSE_HOSTS():
    try:
        f = open("CSE_HOSTS.txt", "r")
    except:
        print "Whoops! File could not be opened. Make sure 'CSE_HOSTS.txt' is in the same directory as this script file."

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
    return { 'hosts':hosts, 'unreachable':unreachable }

def fetchFromServers(hosts, unreachable):
    print "Unreachable hosts => " + str(unreachable)
    print "Hosts in queue    => " + str(hosts) + "\n"
    for host in hosts:
        print "fetching all rendered frames from server " + host
        subprocess.call("rsync -v --exclude='*.blend' -ae 'ssh -o StrictHostKeyChecking=no' --ignore-existing 'cgearhar@" + host + ".cse.taylor.edu:/tmp/cgearhar/' '/Users/cgear13/filmmaking/files_for_render_farm/renderedFrames/directFetchesFromServers/'",shell=True)
        print""

def main():
    CSE_HOSTS = importCSE_HOSTS()
    hostsDict = getAvailableHosts(CSE_HOSTS)
    fetchFromServers(hostsDict['hosts'], hostsDict['unreachable'])

main()
