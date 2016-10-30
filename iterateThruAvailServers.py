#!/usr/bin/python

import subprocess
import sys
import telnetlib
import ast

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
        
def sendSpecificFrames(hosts, unreachable):
    print "iterating through servers..."
    print ""
    firstTime = True
    for host in hosts:
        uIn = "empty"
        if not firstTime:
            while uIn != "exit" and uIn != "":
                uIn = raw_input("continue to server " + host + "? ('exit' to quit)")
            if uIn == "exit":
                sys.exit()
        else:
            firstTime = False
        subprocess.call("clear",shell=True)
        subprocess.call("ssh cgearhar@" + host + ".cse.taylor.edu",shell=True)

def main():
    CSE_HOSTS = importCSE_HOSTS()
    hostDict = getAvailableHosts(CSE_HOSTS)
    sendSpecificFrames(hostDict['hosts'], hostDict['unreachable'])

main()
