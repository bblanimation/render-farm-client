#!/usr/bin/python

import subprocess
import telnetlib
import sys
import ast

CSE_HOSTS = {'cse21801group':  ['cse21801','cse21802','cse21803','cse21804','cse21805','cse21806','cse21807',
                                'cse21808','cse21809','cse21810','cse21811','cse21812','cse21701','cse21702',
                                'cse21703','cse21704','cse21705','cse21706','cse21707','cse21708','cse21709',
                                'cse21710','cse21711','cse21712','cse21713','cse21714','cse21715','cse21716',
                                'cse10301','cse10302','cse10303','cse10304','cse10305','cse10306','cse10307',
                                'cse10309','cse10310','cse10311','cse10312','cse10315','cse10316','cse10317',
                                'cse10318','cse10319','cse103podium',
                                'cse20101','cse20102','cse20103','cse20104','cse20105','cse20106','cse20107',
                                'cse20108','cse20109','cse20110','cse20111','cse20112','cse20113','cse20114',
                                'cse20116','cse20117','cse20118','cse20119','cse20120','cse20121','cse20122',
                                'cse20123','cse20124','cse20125','cse20126','cse20127','cse20128','cse20129',
                                'cse20130','cse20131','cse20132','cse20133','cse20134','cse20135','cse20136'
                                ]} 

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

    for host in hosts:
        print "running 'killall blender' on " + host + " => ",
        sys.stdout.flush()
        subprocess.call("ssh cgearhar@" + host + ".cse.taylor.edu 'killall blender'", shell=True)

def main():
    global CSE_HOSTS
    hosts = getAvailableHosts(CSE_HOSTS)
    killBlenderOnAvailServers(hosts)

main()
