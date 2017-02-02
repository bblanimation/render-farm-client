#!/usr/bin/python

import threading
import telnetlib
import subprocess
import time

from supporting_methods import *

class JobHost(threading.Thread):
    def __init__(self,hostname,persist_thread=True,jobs_list=None,thread_func=None,kwargs=None,callback=None,verbose=0,error_callback=None):
        super(JobHost,self).__init__()

        self.verbose = verbose

        # The name of the host this object represents
        self.hostname = hostname
        # This is the name of the thread.
        self.name = 'Thread-' + hostname

        # Set until it is verified that we can reach the host.
        self.reachable = False
        # In case the status of the host changes after we have checked it once
        self.reachable_change = False
        self.is_telnetable() # Will set up the self.reachable var

        # Starts out not running a job
        self.running_job = False

        # Thread will persist by default
        self.persist_thread=persist_thread

        # List of job strings. This is how jobs are initially handed over to the thread
        self.jobs_list = jobs_list
        self.task_count = 0
        if(jobs_list): self.task_count = len(jobs_list) # Keeps track of number of threads currently running
        self.jobs = dict() # Stores info about a job. Indexed by job string

        if(not(kwargs)): kwargs = dict()
        self.kwargs = kwargs # Arguments to be handed over to the thread_func

        if(not(thread_func)): thread_func = lambda x: x # Defaults to identity function
        self.thread_func = thread_func # The main function that should be run by JobHost

        if(not(callback)): callback = lambda x: x
        self.callback = callback # Set up callback
        self.error_callback = error_callback # If an error comes up while running
        self.started = False
        self._stop = threading.Event()

    def __str__(self):
        aString = threading.Thread.__str__(self)
        return aString

    def set_kwargs(self,kwargs):
        self.kwargs = kwargs

    def set_callback(self,callback):
        self.callback = callback

    def set_error_callback(self,error_callback):
        self.error_callback = error_callback

    def is_running_job(self):
        return self.running_job

    def is_complete_without_error(self):
        for job in self.jobs:
            if(not(job['exit_status']==0)):
                return False
        return True

    def get_jobs_status(self):
        return self.jobs

    def get_task_count(self):
        return self.task_count

    def get_hostname(self):
        return self.hostname

    def is_reachable(self):
        return self.reachable

    def start(self):
        self.started = True
        super(JobHost,self).start()

    def is_started(self):
        return self.started

    def print_job_status(self,state,job=None):
        if(self.verbose >= 1):
            print "Job " + state + " on host", self.get_hostname(),
            if(self.verbose >= 2):
                print ":", job
            else:
                print

    def run(self):
        # Should thread terminate once jobs are finished, or stay alive?
        while( self.task_count > 0  or self.persist_thread ):
            if( len(self.jobs_list) > 0 ):
                self.running_job = True
                job = self.jobs_list.pop()
                self.jobs[job] = { 'exit_status' : -1 , 'get_callback' : self.get_callback, 'error_callback' : self.get_error_callback }
                self.kwargs['jobString'] = job
                self.kwargs['hostname'] = self.get_hostname()
                self.print_job_status('started',job)
                r_value = self.thread_func(**self.kwargs)
                # Cleanup after job is finished and call callback
                self.jobs[job]['exit_status'] = r_value
                self.job_complete(job=job)
            else:
                self.running_job = False
            if( self._stop.isSet() ):
                break
        self.thread_stop()

    def thread_stop(self):
        # This terminates the thread. There is no restarting a thread once it has been terminated.
        self.running_job = False
        self._stop.set()

    def thread_stopped(self):
        return self._stop.isSet()

    def get_callback(self):
        return self.callback

    def get_error_callback(self):
        return self.error_callback

    def job_complete(self,job=None,exit_status=0):
        self.task_count -= 1

        if(self.task_count == 0):
            self.running_job = False
        # Call the callback
        if( self.jobs[job]['exit_status'] == 0 ):

            self.print_job_status('finished',job)

            # Skip callback if there is not one set.
            if( self.jobs[job]['get_callback'] != None ):
                callback = self.jobs[job]['get_callback']()
                if( not(callback == None) ):
                    callback(self.hostname,job)
                elif(self.verbose >=2):
                    print("No callback specified.")
        else:
            if( self.jobs[job]['error_callback'] != None ):
                callback = self.jobs[job]['error_callback']()
                if( not(callback == None) ):
                    callback(self.hostname,job)
                elif(self.verbose >=2):
                    print("No error callback specified.")

    def is_telnetable(self):
        try:
            tn = telnetlib.Telnet(self.hostname,22,.25)
            self.reachable = True
            return True
        except:
            if( self.reachable ):
                self.reachable_change = True
            self.reachable = False
            return False

    def add_jobs(self,jobs):
        for job in jobs:
            self.add_job(job)

    def add_job(self,job):
        self.task_count += 1
        self.running_job = True
        if( not(self.jobs_list) ): self.jobs_list = list()
        self.jobs_list.append(job)

    def print_job_list(self):
        print(self.jobs_list)

break_loop = False

def callback_func(host,job):
    global break_loop
    break_loop = True

def error_callback_func(host,job):
    pass

if( __name__ == '__main__' ):
    print("TESTING JobHost Class")
    verbose = 0
    # self,hostname,thread_func=None,kwargs=None,callback=None,persist_thread=True,verbose=False,error_callback=None

    testDict1 = {'username': 'nwhite', 'remoteProjectPath': '/tmp/nwhite/test', 'verbose': verbose, 'projectPath': '/tmp/nwhite/test', 'remoteSyncBack': '/tmp/nwhite/test/results', 'projectName': 'test', 'projectSyncPath': '/tmp/nwhite/test/toRemote/', 'projectOutuptFile': '/tmp/nwhite/test/'}
    jobsList = [ 'blender -b /tmp/nwhite/test/test.blend -x 1 -o //results/test_####.png -s 2 -e 2 -P  /tmp/nwhite/test/blender_p.py -a' ]
    h1 = JobHost(hostname='cse10318',thread_func=start_tasks,kwargs=testDict1,verbose=verbose,callback=callback_func,jobs_list=jobsList)
    print( "Reachable:", h1.is_reachable() )
    print( "Running:", h1.is_running_job() )
    h1.start()
    h1.add_job('blender -b /tmp/nwhite/test/test.blend -x 1 -o //results/test_####.png -s 4 -e 4 -P  /tmp/nwhite/test/blender_p.py -a')
    # print(h1.get_jobs_status())
    while( h1.is_running_job() ):
        print "Remaining jobs1: ", h1.get_task_count(), "remaining"
        time.sleep(2)

    h1.add_job('blender -b /tmp/nwhite/test/test.blend -x 1 -o //results/test_####.png -s 5 -e 5 -P  /tmp/nwhite/test/blender_p.py -a')
    while( h1.is_running_job() ):
        print "Remaining jobs2: ", h1.get_task_count(), "remaining"
        time.sleep(2)

    h1.thread_stop()
    print(h1.get_jobs_status())

    # testDict2 = {'username': 'nwhite', 'remoteProjectPath': '/tmp/nwhite/test', 'verbose': 2, 'projectPath': '/tmp/nwhite/test', 'remoteSyncBack': '/tmp/nwhite/test/results', 'projectName': 'test', 'projectSyncPath': '/tmp/nwhite/test/toRemote/', 'projectOutuptFile': '/tmp/nwhite/test/'}
    # h2 = JobHost(hostname='cse10319',thread_func=start_tasks,kwargs=testDict2)
    # h2.add_job('blender -b /tmp/nwhite/test/test.blend -x 1 -o //results/test_####.png -s 3 -e 3 -P  /tmp/nwhite/test/blender_p.py -a')
    # h2.print_job_list()
    # print( "Reachable:", h2.is_reachable() )
    # print( "Running:", h2.is_running_job() )
    # h2.start()
    # while( h2.is_running_job() ):
    #     pass
